"""Recover menu-hidden replay passages from the inspected 24 November capture.

HUD absence defines passages, not replay synchronization. Editor overlays are
screened separately; sampled feature checks flag moving cameras and repeats.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw
import pycolmap


def editor_fraction(image):
    array=np.asarray(image.convert("RGB"),dtype=np.int16)
    scale=image.width/1126
    roi=array[round(2080*scale):round(2170*scale)]
    red=(roi[:,:,0]>90)&(roi[:,:,0]>roi[:,:,1]+45)&(roi[:,:,0]>roi[:,:,2]+45)
    return float(red.mean())


def sample(source,time,path):
    subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",f"{time:.6f}","-i",str(source),
        "-frames:v","1","-vf","scale=480:-1","-q:v","3","-y",str(path)],check=True)
    with Image.open(path) as image:return editor_fraction(image)


def recover(source,inspection,output,export):
    with source.open("rb") as handle:fingerprint=hashlib.file_digest(handle,"sha256").hexdigest()
    trace=json.loads((inspection/"ui-trace.json").read_text())
    if fingerprint!=trace["source_sha256"]:raise ValueError("Source differs from UI inspection")
    if (output/"cuts.json").exists():raise ValueError("Output already has a manifest; choose a fresh output")
    records=trace["records"]
    rate=trace["analysis_fps"]
    intervals=[];start=0
    for i in range(1,len(records)+1):
        if i==len(records) or records[i]["replay"]!=records[start]["replay"]:
            if not records[start]["replay"] and (i-start)/rate>=3:
                intervals.append((start/rate,i/rate))
            start=i
    previews=inspection/"hidden-samples";previews.mkdir(exist_ok=True)
    jobs=[]
    for index,(a,b) in enumerate(intervals):
        for j,time in enumerate([a+.5,(a+b)/2,b-.5]):
            jobs.append((index,j,time,previews/f"interval{index:02d}-{j}.jpg"))
    def worker(job):
        i,j,time,path=job
        return i,j,dict(time_seconds=time,path=str(path),editor_red_fraction=sample(source,time,path))
    sampled=list(ThreadPoolExecutor(max_workers=4).map(worker,jobs))
    candidates=[];rejected=[]
    for index,(a,b) in enumerate(intervals):
        samples=[r for i,_,r in sampled if i==index]
        clean=[r["editor_red_fraction"]<.20 for r in samples]
        if not any(clean):
            rejected.append(dict(interval_seconds=[a,b],reason="Editor toolbar present in all three samples",samples=samples))
            continue
        # Mixed intervals need local scanning to separate editor/capture transitions.
        runs=[(a,b)]
        if not all(clean):
            raw=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str(a),"-i",str(source),
                "-t",str(b-a),"-vf","fps=10,scale=240:-1","-an","-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
            height=round(2436*240/1126)
            frames=np.frombuffer(raw,np.uint8).reshape(-1,height,240,3)
            mask=[editor_fraction(Image.fromarray(frame))<.20 for frame in frames]
            runs=[];first=0
            for i in range(1,len(mask)+1):
                if i==len(mask) or mask[i]!=mask[first]:
                    if mask[first] and (i-first)/10>=3:runs.append((a+first/10,a+i/10))
                    first=i
        for first,last in runs:
            first+=.35;last-=.35
            frames=int(np.floor((last-first)*60))
            if frames<120:continue
            name=f"view{len(candidates)+1:02d}"
            observations=[]
            for j,fraction in enumerate([.05,.5,.95]):
                time=first+fraction*(last-first)
                path=previews/f"{name}-{j}.jpg"
                value=sample(source,time,path)
                observations.append(dict(time_seconds=time,path=str(path),editor_red_fraction=value))
            if any(r["editor_red_fraction"]>=.20 for r in observations):
                rejected.append(dict(interval_seconds=[first,last],reason="Editor remains in refined samples"))
                continue
            context=previews/f"{name}-context.jpg"
            sample(source,max(0,a-.5),context)
            candidates.append(dict(id=name,source_start_seconds=first,source_end_seconds=first+frames/60,
                original_hud_absence_interval=[a,b],frames=frames,duration_seconds=frames/60,
                samples=observations,context_preview=str(context)))
    extraction=pycolmap.FeatureExtractionOptions(num_threads=2,max_image_size=1100)
    extraction.sift.max_num_features=2048
    extractor=pycolmap.FeatureExtractor.create(extraction,pycolmap.Device.cpu)
    matcher=pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=2),pycolmap.Device.cpu)
    features={}
    for candidate in candidates:
        values=[]
        for observation in candidate["samples"]:
            with Image.open(observation["path"]) as image:gray=np.array(image.convert("L"))[:950]
            keypoints,descriptors=extractor.extract_from_uint8_array(gray)
            values.append((np.array([[p.x,p.y] for p in keypoints]),descriptors))
        features[candidate["id"]]=values
    def compare(a,b):
        matches=np.asarray(matcher.match(pycolmap.FeatureKeypoints(),a[1],pycolmap.FeatureKeypoints(),b[1]))
        if len(matches)<80:return dict(matches=len(matches),median=None,p90=None,consistent=False)
        displacement=np.linalg.norm(a[0][matches[:,0]]-b[0][matches[:,1]],axis=1)
        med=float(np.median(displacement));p90=float(np.percentile(displacement,90))
        return dict(matches=len(matches),median=med,p90=p90,consistent=med<=.75 and p90<=2.5)
    representatives=[]
    for candidate in candidates:
        current=features[candidate["id"]]
        checks=[compare(current[0],current[1]),compare(current[0],current[2])]
        stable=all(check["consistent"] for check in checks)
        duplicate=None
        if stable:
            for representative in representatives:
                if compare(current[1],features[representative][1])["consistent"]:
                    duplicate=representative;break
            if duplicate is None:representatives.append(candidate["id"])
        candidate.update(sampled_fixed_consistency=stable,stability_checks=checks,duplicate_of=duplicate)
        print(candidate["id"],round(candidate["source_start_seconds"],2),round(candidate["duration_seconds"],2),"fixed",stable,"repeat",duplicate,flush=True)
    if not candidates:raise ValueError("No clean replay passages detected")
    output.mkdir(parents=True,exist_ok=True)
    report=dict(source=source.name,source_sha256=fingerprint,source_resolution=[1126,2436],
        export_fps=60,boundary_method="Replay-menu disappearance at 10 analysis samples/sec; editor-toolbar screening; 0.35-second margins",
        candidates=candidates,rejected_intervals=rejected,distinct_sampled_fixed_views=representatives,
        caution="Variable-duration passages, not synchronized training clips. Three-frame stability/dedup checks only; no camera calibration. Lower-menu absence does not guarantee absence of score overlays or editor objects.",exported=False)
    (output/"cuts.json").write_text(json.dumps(report,indent=2)+"\n")
    if export:
        for candidate in candidates:
            subprocess.run(["ffmpeg","-nostdin","-v","error","-hwaccel","cuda","-ss",str(candidate["source_start_seconds"]),
                "-i",str(source),"-map","0:v:0","-an","-vf","fps=60","-frames:v",str(candidate["frames"]),
                "-c:v","libx264","-preset","fast","-crf","18","-threads","2","-movflags","+faststart",
                "-n",str(output/(candidate["id"]+".mp4"))],check=True)
            print("Exported",candidate["id"],flush=True)
        report["exported"]=True
        (output/"cuts.json").write_text(json.dumps(report,indent=2)+"\n")
    sheet=Image.new("RGB",(6*240,550*((len(candidates)+5)//6)),"white");draw=ImageDraw.Draw(sheet)
    modes=Image.new("RGB",(4*480,200*((len(candidates)+3)//4)),"white");mode_draw=ImageDraw.Draw(modes)
    for i,candidate in enumerate(candidates):
        with Image.open(candidate["samples"][1]["path"]) as image:sheet.paste(image.resize((240,519)),((i%6)*240,(i//6)*550+30))
        draw.text(((i%6)*240+5,(i//6)*550+5),f"{candidate['id']} | {candidate['source_start_seconds']:.1f}s | fixed={candidate['sampled_fixed_consistency']}",fill="black")
        with Image.open(candidate["context_preview"]) as image:modes.paste(image.crop((0,740,480,910)),((i%4)*480,(i//4)*200+30))
        mode_draw.text(((i%4)*480+5,(i//4)*200+5),candidate["id"]+" / preceding menu",fill="black")
    sheet.save(inspection/"recovered-hidden-views.jpg",quality=92)
    modes.save(inspection/"preceding-camera-modes.jpg",quality=92)
    print("Recovered passages:",len(candidates),"distinct sampled-fixed views:",len(representatives),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("--inspection",type=Path,default=Path("outputs/fixed-clean-review"))
    parser.add_argument("--output",type=Path,default=Path("data/raw/true-skate-clean-2026-11-24"))
    parser.add_argument("--export",action="store_true")
    args=parser.parse_args()
    recover(args.source,args.inspection,args.output,args.export)
