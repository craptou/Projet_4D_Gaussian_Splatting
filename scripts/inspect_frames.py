import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import _bootstrap
from skate4d.validation import validate

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Create synchronized timestamp contact sheet")
    p.add_argument("dataset", type=Path)
    p.add_argument("--output", type=Path, default=Path("outputs/contact-sheet.jpg"))
    args = p.parse_args()
    info = validate(args.dataset)
    cams = sorted(d for d in args.dataset.glob("cam*") if d.is_dir())
    indices = sorted(set([1, (info["frames_per_camera"]+1)//2, info["frames_per_camera"]]))
    sheet = Image.new("RGB", (320*len(cams), 210*len(indices)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        for col, cam in enumerate(cams):
            with Image.open(cam / f"frame_{index:05d}.jpg") as im:
                im.thumbnail((320, 180))
                sheet.paste(im, (col*320, row*210+25))
            draw.text((col*320+5, row*210+5), f"{cam.name} / extracted index {index}", fill="black")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        p.error("Output already exists; choose a new filename")
    sheet.save(args.output)
    print(args.output)
