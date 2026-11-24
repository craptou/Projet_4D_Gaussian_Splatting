"""Compare the fixed pilot with a new initialization using identical targets."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw


def compare(baseline,candidate,output):
    output.mkdir(parents=True,exist_ok=True)
    before=json.loads((baseline/"evaluation-2000.json").read_text())
    after=json.loads((candidate/"evaluation-2000.json").read_text())
    summary={"baseline":str(baseline),"candidate":str(candidate),"cameras":{}}
    for group in ["test-cam13","train-cam08"]:
        old=baseline/"renders-2000"/group
        new=candidate/"renders-2000"/group
        for index in range(13):
            with Image.open(old/"gt"/f"{index:03d}.png") as a,Image.open(new/"gt"/f"{index:03d}.png") as b:
                if not np.array_equal(np.asarray(a),np.asarray(b)):
                    raise ValueError("Comparison targets differ; metrics are not comparable")
        first=before["metrics"][group]["render"]
        second=after["metrics"][group]["render"]
        delta={key:second[key]-first[key] for key in first}
        summary["cameras"][group]=dict(baseline=first,candidate=second,delta=delta,
            candidate_frozen_time=after["metrics"][group]["frozen_time_baseline"])
        print(f"\n{group}: PSNR {first['mean_psnr_db']:.2f} -> {second['mean_psnr_db']:.2f} dB ({delta['mean_psnr_db']:+.2f})",flush=True)
        print(f"SSIM {first['mean_ssim']:.3f} -> {second['mean_ssim']:.3f}; region changeante : {first['temporal_change_region_mean_psnr_db']:.2f} -> {second['temporal_change_region_mean_psnr_db']:.2f} dB",flush=True)
        sheet=Image.new("RGB",(384*3,300*3),"white");draw=ImageDraw.Draw(sheet)
        for row,index in enumerate([0,6,12]):
            columns=[("Video",new/"gt"),("Essai precedent",old/"renders"),("Initialisation reechantillonnee",new/"renders")]
            for col,(label,folder) in enumerate(columns):
                with Image.open(folder/f"{index:03d}.png") as image:sheet.paste(image.resize((384,273)),(col*384,row*300+27))
                draw.text((col*384+5,row*300+8),f"{group} / f{index} / {label}",fill="black")
        sheet.save(output/(group+"-comparison.jpg"),quality=92)
    summary["interpretation"]="Changes in full-image metrics do not validate the board. Inspect the board in the comparisons and compare the dynamic result with its frozen-time control. Temporal-change regions are not board segmentation."
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("\nUne hausse des metriques globales ne prouve pas que la planche est reconstruite. Examiner les images.",flush=True)
    print("Comparaison de la vue reservee :",output/"test-cam13-comparison.jpg",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    compare(args.baseline,args.candidate,args.output)
