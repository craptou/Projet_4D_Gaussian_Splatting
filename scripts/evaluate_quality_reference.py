"""Compare fixed held-out RGB PNGs across the smoke and bounded quality pilot."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage.metrics import structural_similarity


def evaluate(output, source, iterations):
    root = source.parents[2]
    baseline = root / "outputs/dynerf-local-20261120-234731Z/model/test/ours_10"
    candidates = [("smoke-12-steps", baseline)] if baseline.exists() else []
    candidates += [(f"fine-{i}", output / f"model/test/ours_{i}") for i in iterations]
    reference = candidates[-1][1] / "gt"
    names = [f"{i:05d}.png" for i in range(30)]
    metrics = {}
    for label, folder in candidates:
        records = []
        for i, name in enumerate(names):
            with Image.open(reference / name) as im:
                target = np.array(im.convert("RGB"))
            with Image.open(folder / "gt" / name) as im:
                if not np.array_equal(target, np.asarray(im.convert("RGB"))):
                    raise ValueError("Target pixels differ between experiments")
            with Image.open(folder / "renders" / name) as im:
                rendered = np.array(im.convert("RGB"))
            if rendered.shape != target.shape or rendered.shape != (1014, 1352, 3):
                raise ValueError("Mismatched render/target dimensions")
            a, b = target.astype(np.float32)/255, rendered.astype(np.float32)/255
            mse = float(np.mean((a-b)**2))
            psnr = float(-10*np.log10(mse)) if mse > 0 else None
            ssim = float(structural_similarity(a, b, data_range=1, channel_axis=2,
                gaussian_weights=True, sigma=1.5, use_sample_covariance=False))
            records.append(dict(source_frame=i, psnr_db=psnr, ssim=ssim))
        metrics[label] = dict(frames=records,
            mean_psnr_db=float(np.mean([r["psnr_db"] for r in records if r["psnr_db"] is not None])),
            mean_ssim=float(np.mean([r["ssim"] for r in records])))
        print(label, "PSNR", metrics[label]["mean_psnr_db"], "SSIM", metrics[label]["mean_ssim"], flush=True)
    sheet = Image.new("RGB", (400*(len(candidates)+1), 3*326), "white")
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate([0, 14, 29]):
        columns = [("cam00 original", reference)] + [(label, folder/"renders") for label, folder in candidates]
        for column, (label, folder) in enumerate(columns):
            with Image.open(folder / f"{index:05d}.png") as im:
                sheet.paste(im.resize((400, 300)), (column*400, row*326+26))
            draw.text((column*400+5, row*326+6), f"{label} | frame {index}", fill="black")
    sheet.save(output / "progression.jpg", quality=90)
    result = dict(camera="cam00", usage="Held out from optimization; monitored validation camera, not a fresh independent final test",
        protocol="30 full-frame RGB PNGs, 1352x1014, normalized stored RGB, no masks or linearization",
        psnr="Mean of per-frame PSNR from RGB MSE; a perfect-match frame has null PSNR (infinite)",
        ssim="scikit-image, Gaussian window sigma=1.5, channel_axis=2, data_range=1, sample covariance disabled",
        lpips="Not measured; no pretrained network download", results=metrics)
    (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return {label: {k:v for k,v in values.items() if k != "frames"} for label,values in metrics.items()}
