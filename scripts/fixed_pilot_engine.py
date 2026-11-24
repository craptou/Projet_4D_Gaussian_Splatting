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
    assert len(train)==104 and len(test)==13
    assert {r["camera_id"] for r in manifest["frames"] if r["split"]=="train"}.isdisjoint({"cam13"})
    max_error = 0
    points = gaussians.get_xyz.detach().cpu().numpy()
    for i in range(0,len(train),13):
        camera = train[i]
        record = [r for r in manifest["frames"] if r["split"]=="train"][i]
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
    assert train[0].original_image.shape == (3,400,563)
    assert test[0].time==0 and test[12].time==1
    expected_points=manifest["initialization_points"]
    assert gaussians.get_xyz.shape[0]==expected_points
    result=dict(training_samples=len(train),test_samples=len(test),initial_points=expected_points,
        image_resolution=manifest["image_resolution"],last_normalized_time=test[12].time,
        renderer_projection_max_error_pixels=max_error,gpu=torch.cuda.get_device_name(),
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
    groups={"test-cam13":list(scene.getTestCameras()),
        "train-cam08":[train[i] for i,r in enumerate(train_records) if r["camera_id"]=="cam08"]}
    background=torch.tensor([0,0,0],dtype=torch.float32,device="cuda")
    result={}
    with torch.no_grad():
        for name,cameras in groups.items():
            folder=output/f"renders-{iteration}"/name
            for sub in ["gt","renders","frozen-time"]: (folder/sub).mkdir(parents=True,exist_ok=True)
            targets=[];renders=[];frozen=[]
            for j,camera in enumerate(cameras):
                image=render_image(camera,gaussians,pipeline,background,cam_type=scene.dataset_type)["render"].clamp(0,1)
                original=camera.time
                camera.time=.5
                fixed=render_image(camera,gaussians,pipeline,background,cam_type=scene.dataset_type)["render"].clamp(0,1)
                camera.time=original
                gt=camera.original_image.cuda()
                targets.append(gt.cpu());renders.append(image.cpu());frozen.append(fixed.cpu())
                for sub,value in [("gt",gt),("renders",image),("frozen-time",fixed)]:
                    array=(value.permute(1,2,0).cpu().numpy()*255).round().astype(np.uint8)
                    Image.fromarray(array).save(folder/sub/f"{j:03d}.png")
            target=torch.stack(targets);pred=torch.stack(renders);fixed=torch.stack(frozen)
            # A temporal-change region is diagnostic, not a board segmentation.
            change=(target.max(0).values-target.min(0).values).max(0).values>45/255
            assert int(change.sum())>20
            Image.fromarray((change.numpy()*255).astype(np.uint8)).save(folder/"temporal-change-mask.png")
            def metrics(value):
                mse=((value-target)**2).mean((1,2,3))
                moving=((value-target)**2)[:,:,change].mean((1,2))
                return dict(mean_psnr_db=float((-10*torch.log10(mse)).mean()),
                    mean_ssim=float(np.mean([ssim(a.unsqueeze(0),b.unsqueeze(0)).item() for a,b in zip(value,target)])),
                    temporal_change_region_mean_psnr_db=float((-10*torch.log10(moving)).mean()),
                    temporal_change_region_mae=float((value-target).abs()[:,:,change].mean()))
            result[name]=dict(render=metrics(pred),frozen_time_baseline=metrics(fixed),
                temporal_change_region_pixels=int(change.sum()),total_pixels=int(change.numel()),
                target_interframe_mae=float((target[1:]-target[:-1]).abs().mean()),
                render_interframe_mae=float((pred[1:]-pred[:-1]).abs().mean()))
            sheet=Image.new("RGB",(563*2,425*3),"white");draw=ImageDraw.Draw(sheet)
            for row,index in enumerate([0,6,12]):
                for col,sub in enumerate(["gt","renders"]):
                    with Image.open(folder/sub/f"{index:03d}.png") as image: sheet.paste(image,(col*563,row*425+25))
                    draw.text((col*563+5,row*425+5),f"{name} / frame {index} / {sub}",fill="black")
            sheet.save(folder/"comparison.jpg",quality=92)
    report=dict(iteration=iteration,active_sh_degree=gaussians.active_sh_degree,
        gaussian_count=int(gaussians.get_xyz.shape[0]),metrics=result,
        caution="Short execution/quality pilot, no convergence claim. Temporal-change mask comes from target pixel variation, not board ground truth. cam13 is held out from optimization but closely overlaps cam01.")
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
        runpy.run_path(str(UPSTREAM/"train.py"),run_name="__main__")
