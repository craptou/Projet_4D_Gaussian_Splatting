"""Recover replay-view candidates from the inspected raw True Skate recording.

UI segmentation and timestamp-aware local cursor fits precede any export.
Three scene samples check fixed-camera consistency; this is not calibration.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw
import pycolmap
import _bootstrap
from skate4d.replays import fit_passage


def sample(source, moment, target, expected_x):
    command = ["ffmpeg", "-nostdin", "-v", "info", "-threads", "1", "-ss", f"{moment:.9f}",
        "-i", str(source), "-filter_complex",
        "[0:v]split[a][b];[a]crop=900:32:100:2165,format=gray,showinfo[ui];[b]scale=480:-1[preview]",
        "-map", "[ui]", "-frames:v", "1", "-fps_mode", "passthrough", "-pix_fmt", "gray",
        "-f", "rawvideo", "pipe:1", "-map", "[preview]", "-frames:v", "1", "-q:v", "3", "-y", str(target)]
    result = subprocess.run(command, capture_output=True, check=True)
    array = np.frombuffer(result.stdout, np.uint8).reshape(32,900)
    score = (array[9:23]>160).sum(axis=0)
    columns = np.flatnonzero(score>=8)
    runs = np.split(columns, np.where(np.diff(columns)>1)[0]+1)
    runs = [run for run in runs if 30<=len(run)<=60]
    if not runs:
        raise ValueError(f"No unambiguous cursor near {moment:.2f}s")
    best = min(runs,key=lambda run: abs((run[0]+run[-1])/2+100-expected_x))
    marker = float((best[0]+best[-1])/2+100)
    if abs(marker-expected_x)>15:
        raise ValueError("Detected cursor differs from the coarse playback fit")
    times = re.findall(r"n:\s*0 .*?pts_time:([\d.\-]+)", result.stderr.decode(errors="replace"))
    if not times:
        raise ValueError("Missing decoded sample timestamp")
    return dict(source_seconds=moment+float(times[0]), marker_source_x=marker, preview=str(target))


def recover(source, inspection, output, export):
    if (output/"cuts.json").exists():
        raise ValueError("Output already has a manifest; use a new directory")
    inspected = json.loads((inspection/"ui-trace.json").read_text())
    if source.name != inspected["source"]:
        raise ValueError("Trace source differs")
    with source.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != inspected["source_sha256"]:
            raise ValueError("Source content differs from the inspected recording")
    rows = inspected["records"]
    trace = [r["marker"] for r in rows]
    boundaries = [0,len(rows)]
    for i in range(1,len(rows)):
        if rows[i]["replay"] != rows[i-1]["replay"]:
            boundaries.append(i)
        if trace[i] is not None and trace[i-1] is not None and trace[i-1]-trace[i]>50:
            boundaries.append(i)
    boundaries = sorted(set(boundaries))
    candidates, rejected = [], []
    for start,end in zip(boundaries,boundaries[1:]):
        if end-start<60:
            continue
        try:
            fit = fit_passage(trace,start,end,25,210,10)
            fit.update(ui_interval_seconds=[start/10,end/10])
            candidates.append(fit)
        except ValueError as error:
            rejected.append(dict(source_interval_seconds=[start/10,end/10],reason=str(error)))
    if not candidates:
        raise ValueError("No coherent replay passages")
    previews = inspection/"view-samples"
    previews.mkdir(exist_ok=True)
    jobs = []
    for i,candidate in enumerate(candidates,1):
        start,end = candidate["first_frame"]/10,candidate["end_frame_exclusive"]/10
        candidate["id"] = f"cam{i:02d}"
        for j,fraction in enumerate([.03,.5,.97]):
            jobs.append((i,j,start+fraction*(end-start),previews/f"cam{i:02d}-{j}.jpg",164+740*fraction))
    def worker(job):
        i,j,t,path,expected = job
        return i,j,sample(source,t,path,expected)
    sampled = list(ThreadPoolExecutor(max_workers=4).map(worker,jobs))
    for i,candidate in enumerate(candidates,1):
        observations = [item for index,_,item in sampled if index==i]
        times = np.array([r["source_seconds"] for r in observations])
        positions = np.array([r["marker_source_x"] for r in observations])
        slope,intercept = np.polyfit(times-times.mean(),positions,1)
        intercept -= slope*times.mean()
        residual = float(np.max(np.abs(positions-(slope*times+intercept))))
        if slope<=0 or residual>3:
            raise ValueError(f"Inconsistent local cursor fit for {candidate['id']}: {residual:.2f}px")
        candidate.update(source_start_seconds=float((164-intercept)/slope),
            source_end_seconds=float((904-intercept)/slope),
            cursor_source_pixels_per_second=float(slope), cursor_max_residual_source_pixels=residual,
            refinement_samples=observations)
    options = pycolmap.FeatureExtractionOptions(num_threads=2,max_image_size=1100)
    options.sift.max_num_features = 2048
    extractor = pycolmap.FeatureExtractor.create(options,pycolmap.Device.cpu)
    matcher = pycolmap.FeatureMatcher.create(pycolmap.FeatureMatchingOptions(num_threads=2),pycolmap.Device.cpu)
    features = {}
    for candidate in candidates:
        samples = []
        for observation in candidate["refinement_samples"]:
            with Image.open(observation["preview"]) as image:
                gray = np.asarray(image.convert("L"))[:720]
            keypoints,descriptors = extractor.extract_from_uint8_array(gray)
            samples.append((np.array([[p.x,p.y] for p in keypoints]),descriptors))
        features[candidate["id"]] = samples
    def compare(a,b):
        matches = np.asarray(matcher.match(pycolmap.FeatureKeypoints(),a[1],pycolmap.FeatureKeypoints(),b[1]))
        if not len(matches):
            return dict(matches=0,median_displacement_pixels=None,p90_displacement_pixels=None)
        displacements = np.linalg.norm(a[0][matches[:,0]]-b[0][matches[:,1]],axis=1)
        return dict(matches=len(matches),median_displacement_pixels=float(np.median(displacements)),
                    p90_displacement_pixels=float(np.percentile(displacements,90)))
    representatives = []
    for candidate in candidates:
        current = features[candidate["id"]]
        checks = [compare(current[0],other) for other in current[1:]]
        stable = all(c["matches"]>=80 and c["median_displacement_pixels"]<=.75 and
                     c["p90_displacement_pixels"]<=2.5 for c in checks)
        candidate["sampled_camera_stability"] = dict(consistent_with_fixed=stable,checks=checks,
            units="pixels in 480px-wide scene samples; 3 sampled instants only")
        duplicate = None
        if stable:
            for representative in representatives:
                match = compare(current[1],features[representative][1])
                if match["matches"]>=80 and match["median_displacement_pixels"]<.75 and match["p90_displacement_pixels"]<2.5:
                    duplicate=representative
                    break
            if duplicate is None:
                representatives.append(candidate["id"])
        candidate["duplicate_of"] = duplicate
        print(candidate['id'],candidate['source_start_seconds'],candidate['source_end_seconds'],
              'fixed',stable,'duplicate',duplicate,flush=True)
    output.mkdir(parents=True,exist_ok=True)
    speed = [c["cursor_source_pixels_per_second"] for c in candidates]
    common_seconds = min(c["source_end_seconds"]-c["source_start_seconds"] for c in candidates)
    frames = int(np.floor(common_seconds*60))
    report = dict(source=source.name,source_sha256=inspected['source_sha256'],
        common_cursor_window_source_x=[164,904],export_fps=60,frames_per_clip=frames,
        duration_seconds=frames/60,cursor_speed_ratio=max(speed)/min(speed),
        candidates=candidates,rejected_intervals=rejected,distinct_sampled_fixed_views=representatives,
        caution="Candidate alignment from UI only, not frame-perfect simulation sync. Sampled fixed-camera checks do not establish calibration or full-sequence stability. Board visibility needs review.",exported=False)
    (output/"cuts.json").write_text(json.dumps(report,indent=2)+"\n")
    if export:
        if report['cursor_speed_ratio']>1.02:
            raise ValueError("Playback speeds differ by more than 2%; refusing common export")
        for candidate in candidates:
            subprocess.run(["ffmpeg","-nostdin","-v","error","-hwaccel","cuda","-ss",f"{candidate['source_start_seconds']:.9f}",
                "-i",str(source),"-map","0:v:0","-an","-vf","fps=60","-frames:v",str(frames),
                "-c:v","libx264","-preset","fast","-crf","18","-threads","2","-movflags","+faststart",
                "-n",str(output/(candidate['id']+'.mp4'))],check=True)
            print('Exported',candidate['id'],flush=True)
        report['exported']=True
        (output/"cuts.json").write_text(json.dumps(report,indent=2)+"\n")
    sheet=Image.new('RGB',(7*240,((len(candidates)+6)//7)*550),'white');draw=ImageDraw.Draw(sheet)
    for i,candidate in enumerate(candidates):
        with Image.open(candidate['refinement_samples'][1]['preview']) as image:
            image=image.resize((240,519));sheet.paste(image,((i%7)*240,(i//7)*550+30))
        draw.text(((i%7)*240+5,(i//7)*550+5),f"{candidate['id']} | {candidate['source_start_seconds']:.1f}s",fill='black')
    sheet.save(inspection/'recovered-views.jpg',quality=90)
    print('Distinct sampled-fixed viewpoints:',len(representatives),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--inspection',type=Path,default=Path('outputs/fixed-capture-review'))
    parser.add_argument('--output',type=Path,default=Path('data/raw/true-skate-fixed-2026-11-23'))
    parser.add_argument('--export',action='store_true')
    args=parser.parse_args()
    recover(args.source,args.inspection,args.output,args.export)
