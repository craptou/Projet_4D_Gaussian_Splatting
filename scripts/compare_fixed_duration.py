"""Compare checkpoints from one trajectory on identical reserved/train targets."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

CHECKPOINTS=[2000,5000,10000]


def compare(run,output):
    reports={i:json.loads((run/f"evaluation-{i}.json").read_text()) for i in CHECKPOINTS}
    output.mkdir(parents=True,exist_ok=True)
    summary=dict(checkpoints=CHECKPOINTS,cameras={},
        caution="Same-run checkpoints; target temporal-change region is not a board segmentation. Inspect the board and frozen-time control alongside image-wide metrics.")
    rows=[]
    for group in ["test-cam13","train-cam08"]:
        for index in range(13):
            with Image.open(run/"renders-2000"/group/"gt"/f"{index:03d}.png") as image:target=np.asarray(image).copy()
            for iteration in CHECKPOINTS[1:]:
                with Image.open(run/f"renders-{iteration}"/group/"gt"/f"{index:03d}.png") as image:
                    if not np.array_equal(target,np.asarray(image)):raise ValueError("Targets differ across checkpoints")
        summary["cameras"][group]={}
        print(f"\n{group} : etapes | PSNR global | SSIM | PSNR zone changeante | PSNR temps fige",flush=True)
        for iteration in CHECKPOINTS:
            metrics=reports[iteration]["metrics"][group]
            summary["cameras"][group][str(iteration)]=metrics
            row=dict(camera=group,iteration=iteration,gaussians=reports[iteration]["gaussian_count"],
                psnr=metrics["render"]["mean_psnr_db"],ssim=metrics["render"]["mean_ssim"],
                changing_region_psnr=metrics["render"]["temporal_change_region_mean_psnr_db"],
                frozen_time_psnr=metrics["frozen_time_baseline"]["mean_psnr_db"])
            rows.append(row)
            print(f"{iteration:5d} | {row['psnr']:.2f} dB | {row['ssim']:.3f} | {row['changing_region_psnr']:.2f} dB | {row['frozen_time_psnr']:.2f} dB",flush=True)
        sheet=Image.new("RGB",(1280,771),"white");draw=ImageDraw.Draw(sheet)
        for row,index in enumerate([0,6,12]):
            sources=[("Recording",run/"renders-2000"/group/"gt")]+[(f"{i} steps",run/f"renders-{i}"/group/"renders") for i in CHECKPOINTS]
            for col,(label,folder) in enumerate(sources):
                with Image.open(folder/f"{index:03d}.png") as image:sheet.paste(image.resize((320,227)),(col*320,row*257+30))
                draw.text((col*320+5,row*257+8),f"{group} / f{index} / {label}",fill="black")
        sheet.save(output/(group+"-comparison.jpg"),quality=92)
    (output/"progression.json").write_text(json.dumps(summary,indent=2)+"\n")
    with (output/"progression.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for group,label in [("test-cam13","Reserved cam13"),("train-cam08","Training cam08")]:
        selected=[r for r in rows if r["camera"]==group]
        axes[0].plot(CHECKPOINTS,[r["psnr"] for r in selected],marker="o",label=label)
        axes[1].plot(CHECKPOINTS,[r["changing_region_psnr"] for r in selected],marker="o",label=label)
    for ax,title in zip(axes,["Full-image PSNR","Target temporal-change region PSNR"]):
        ax.set(title=title,xlabel="Fine training steps",ylabel="PSNR (dB)",xticks=CHECKPOINTS)
        ax.grid(alpha=.25);ax.legend()
    fig.suptitle("Training-duration experiment: identical views, images and initialization")
    fig.tight_layout();fig.savefig(output/"progression.png",dpi=140);plt.close(fig)
    print("\nComparer la planche dans les images : une hausse du score global ne suffit pas.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    compare(args.run,args.output)
