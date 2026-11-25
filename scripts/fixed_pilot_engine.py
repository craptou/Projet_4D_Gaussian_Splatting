"""Linux GPU entry point for the runtime True Skate loader and bounded pilot."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT/"third_party/4DGaussians"
sys.path.insert(0, str(UPSTREAM))
from fixed_dataset_adapter import install
from fixed_training_schedule import training_arguments
install()


def load(source, output, config, iteration=None):
    import mmcv
    from arguments import ModelParams, ModelHiddenParams, PipelineParams
    from utils.params_utils import merge_hparams
    from scene import Scene, GaussianModel
    parser = argparse.ArgumentParser()
    mp = ModelParams(parser)
    hp = ModelHiddenParams(parser)
    pp = PipelineParams(parser)
    args = parser.parse_args(["-s",str(source),"-m",str(output/"model")])
    args = merge_hparams(args, mmcv.Config.fromfile(str(config)))
    parameters = mp.extract(args)
    gaussians = GaussianModel(parameters.sh_degree, hp.extract(args))
    scene = Scene(parameters, gaussians, load_iteration=iteration, shuffle=False)
    return scene,gaussians,pp.extract(args),parameters


def probe(source, output, config):
    import numpy as np
    import torch
    scene,gaussians,_,_ = load(source,output,config)
    manifest = json.loads((source/"manifest.json").read_text())
    train,test = scene.getTrainCameras(),scene.getTestCameras()
    train_records=[r for r in manifest["frames"] if r["split"]=="train"]
    test_records=[r for r in manifest["frames"] if r["split"]=="test"]
    assert len(train)==len(train_records) and len(test)==len(test_records)
    assert {r["camera_id"] for r in train_records}.isdisjoint({manifest["heldout_camera"]})
    max_error = 0
    points = gaussians.get_xyz.detach().cpu().numpy()
    seen=set()
    for i,record in enumerate(train_records):
        if record["camera_id"] in seen:continue
        seen.add(record["camera_id"])
        camera = train[i]
        pose = np.array(record["world_to_camera"])
        cp = points@pose[:,:3].T+pose[:,3]
        valid = cp[:,2]>.1
        xyz = np.c_[points[valid],np.ones(valid.sum())]
        clip = xyz@camera.full_proj_transform.numpy()
        ndc = clip[:,:2]/clip[:,3,None]
        viewport = (ndc+1)*np.array(manifest["image_resolution"])/2
        focal,cx,cy = manifest["intrinsics"]
        expected = cp[valid,:2]/cp[valid,2,None]*focal+np.array([cx,cy])
        inside = np.all((expected>0)&(expected<np.array(manifest["image_resolution"])),axis=1)
        assert inside.sum()>=10
        max_error = max(max_error,float(np.max(np.abs(viewport[inside]-expected[inside]))))
    assert max_error<.001
    width,height=manifest["image_resolution"]
    assert train[0].original_image.shape == (3,height,width)
    assert [camera.time for camera in test]==[r['time'] for r in test_records]
    expected_points=manifest["initialization_points"]
    assert gaussians.get_xyz.shape[0]==expected_points
    board_visibility=None
    if manifest.get('static_scene') or manifest.get('temporal_scene'):
        from static_world_scale import require_board_visibility
        preparation=json.loads((source/'preparation.json').read_text())
        start=preparation['background_points']
        board_visibility=require_board_visibility(points[start:start+preparation['board_seed_points']],manifest['frames'])
    result=dict(training_samples=len(train),test_samples=len(test),initial_points=expected_points,
        image_resolution=manifest["image_resolution"],last_normalized_time=test[len(test)-1].time,
        renderer_projection_max_error_pixels=max_error,gpu=torch.cuda.get_device_name(),
        static_board_visibility=board_visibility,
        status="Actual runtime loader and renderer projection checks passed")
    (output/"loader.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)


def render(source, output, config, iteration):
    import numpy as np
    from PIL import Image, ImageDraw
    import torch
    from gaussian_renderer import render as render_image
    from utils.loss_utils import ssim
    scene,gaussians,pipeline,parameters = load(source,output,config,iteration)
    gaussians.active_sh_degree = min(gaussians.max_sh_degree,iteration//1000)
    manifest=json.loads((source/"manifest.json").read_text())
    train_records=[r for r in manifest["frames"] if r["split"]=="train"]
    train=scene.getTrainCameras()
    training_view=manifest.get("evaluation_training_camera","cam08")
    groups={"test-"+manifest["heldout_camera"]:list(scene.getTestCameras()),
        "train-"+training_view:[train[i] for i,r in enumerate(train_records) if r["camera_id"]==training_view]}
    static=bool(manifest.get('static_scene'))
    if static:
        groups.update({'train-'+name:[train[i] for i,r in enumerate(train_records) if r['camera_id']==name]
            for name in manifest['training_cameras']})
    render_options={'stage':'coarse'} if static else {}
    background=torch.tensor([0,0,0],dtype=torch.float32,device="cuda")
    result={}
    with torch.no_grad():
        for name,cameras in groups.items():
            folder=output/f"renders-{iteration}"/name
            for sub in ["gt","renders","frozen-time"]: (folder/sub).mkdir(parents=True,exist_ok=True)
            targets=[];renders=[];frozen=[]
            for j,camera in enumerate(cameras):
                image=render_image(camera,gaussians,pipeline,background,cam_type=scene.dataset_type,**render_options)["render"].clamp(0,1)
                original=camera.time
                camera.time=manifest.get('frozen_control_time',.5)
                fixed=render_image(camera,gaussians,pipeline,background,cam_type=scene.dataset_type,**render_options)["render"].clamp(0,1)
                camera.time=original
                gt=camera.original_image.cuda()
                targets.append(gt.cpu());renders.append(image.cpu());frozen.append(fixed.cpu())
                for sub,value in [("gt",gt),("renders",image),("frozen-time",fixed)]:
                    array=(value.permute(1,2,0).cpu().numpy()*255).round().astype(np.uint8)
                    Image.fromarray(array).save(folder/sub/f"{j:03d}.png")
            target=torch.stack(targets);pred=torch.stack(renders);fixed=torch.stack(frozen)
            # A temporal-change region is diagnostic, not a board segmentation.
            change=(target.max(0).values-target.min(0).values).max(0).values>45/255
            region_key='temporal_change_region'
            if static:
                record=next(r for r in manifest['frames'] if r['camera_id']==name.split('-',1)[1])
                with Image.open(source/record['evaluation_mask_path']) as image:change=torch.from_numpy(np.array(image.convert('L'))>0)
                region_key='candidate_foreground_region'
            if not static:assert int(change.sum())>20
            Image.fromarray((change.numpy()*255).astype(np.uint8)).save(folder/("candidate-foreground-mask.png" if static else "temporal-change-mask.png"))
            def metrics(value):
                mse=((value-target)**2).mean((1,2,3))
                from masked_evaluation import region_metrics
                region=region_metrics(value,target,change)
                return dict(mean_psnr_db=float((-10*torch.log10(mse)).mean()),
                    mean_ssim=float(np.mean([ssim(a.unsqueeze(0),b.unsqueeze(0)).item() for a,b in zip(value,target)])),
                    **{region_key+'_mean_psnr_db':region['mean_psnr_db'],
                    region_key+'_mae':region['mae'],region_key+'_available':region['available']})
            result[name]=dict(render=metrics(pred),frozen_time_baseline=metrics(fixed),
                **{region_key+'_pixels':int(change.sum())},total_pixels=int(change.numel()),
                target_interframe_mae=None if static else float((target[1:]-target[:-1]).abs().mean()),
                render_interframe_mae=None if static else float((pred[1:]-pred[:-1]).abs().mean()))
            width,height=manifest["image_resolution"]
            preview_height=round(height*400/width)
            examples=[0] if static else [0,len(cameras)//2,len(cameras)-1]
            sheet=Image.new("RGB",(800,(preview_height+25)*len(examples)),"white");draw=ImageDraw.Draw(sheet)
            for row,index in enumerate(examples):
                for col,sub in enumerate(["gt","renders"]):
                    with Image.open(folder/sub/f"{index:03d}.png") as image: sheet.paste(image.resize((400,preview_height)),(col*400,row*(preview_height+25)+25))
                    draw.text((col*400+5,row*(preview_height+25)+5),f"{name} / frame {index} / {sub}",fill="black")
            sheet.save(folder/"comparison.jpg",quality=92)
    report=dict(iteration=iteration,active_sh_degree=gaussians.active_sh_degree,
        static_scene=static,
        temporal_scene=bool(manifest.get('temporal_scene')),frozen_control_time=manifest.get('frozen_control_time',.5),
        gaussian_count=int(gaussians.get_xyz.shape[0]),metrics=result,
        caution="Bounded pilot, no convergence claim. Temporal-change mask comes from target pixel variation, not board ground truth. Reserved camera excluded from optimization; viewpoint independence must be assessed separately.")
    if static:report['caution']='Static undeformed renderer, one instant, restricted 14-view training subset. Candidate foreground masks are approximate; training masks guide optimization. Reserved view excluded from initialization and optimization. No motion or full-dataset reconstruction demonstrated.'
    (output/f"evaluation-{iteration}.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["probe","train","render"])
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--configs",type=Path,required=True)
    parser.add_argument("--iteration",type=int,default=2000)
    parser.add_argument("--save-iterations",type=int,nargs="+",default=[500,2000])
    parser.add_argument("--test-iterations",type=int,nargs="+",default=[2000])
    args=parser.parse_args()
    if args.phase=="probe": probe(args.source,args.output,args.configs)
    elif args.phase=="render": render(args.source,args.output,args.configs,args.iteration)
    else:
        sys.argv=training_arguments(UPSTREAM,args.source,args.output,args.configs,args.save_iterations,args.test_iterations)
        manifest=json.loads((args.source/"manifest.json").read_text())
        if manifest.get("foreground_loss") or manifest.get('static_scene'):
            from fixed_foreground_loss import foreground_l1,instrument_training
            training_path=UPSTREAM/"train.py"
            weight=manifest.get('foreground_loss',{}).get('weight',0.)
            text=training_path.read_text()
            if manifest.get('foreground_loss'):
                print("Foreground L1 enabled:",json.dumps(manifest["foreground_loss"]),flush=True)
                text=instrument_training(text)
            if manifest.get('static_scene'):
                from fixed_static_scene import instrument_static_render
                text=instrument_static_render(text)
                print('Static scene: undeformed renderer in all training/evaluation calls',flush=True)
            namespace=dict(__name__="__main__",__file__=str(training_path),foreground_l1=foreground_l1,foreground_weight=weight)
            exec(compile(text,str(training_path),"exec"),namespace)
        else:
            runpy.run_path(str(UPSTREAM/"train.py"),run_name="__main__")
