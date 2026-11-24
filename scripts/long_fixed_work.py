"""Windows launcher: original True Skate initialization, longer optimization."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys

from live_process import live_run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args()
    if os.name!="nt":raise ValueError("Lancer depuis PowerShell Windows")
    root=Path(__file__).resolve().parents[1]
    source=root/"data/processed/true-skate-fixed-pilot-v2"
    baseline=root/"outputs/true-skate-fixed-pilot"
    original=root/"configs/experiments/true-skate-fixed-pilot.py"
    config=root/"configs/experiments/true-skate-fixed-duration.py"
    report=json.loads((baseline/"report.json").read_text())
    manifest=json.loads((source/"manifest.json").read_text())
    if manifest["initialization_points"]!=1115 or "resampling" in manifest:
        raise ValueError("Le test de duree exige l'initialisation originale de 1115 points")
    if hashlib.sha256(original.read_bytes()).hexdigest()!=report["config_sha256"]:
        raise ValueError("La configuration initiale a change depuis le premier essai")
    overrides={k:v for k,v in runpy.run_path(str(config)).items() if not k.startswith("__")}
    if overrides!={"_base_":"./true-skate-fixed-pilot.py","OptimizationParams":{"iterations":10000}}:
        raise ValueError("Seule la duree fine doit changer dans cette experience")
    validation=json.loads((root/"docs/evidence/next-initialization-validation.json").read_text())["preparation"]
    for path,key in [(source/"manifest.json","source_manifest_sha256"),(source/"points3D_multipleview.ply","source_cloud_sha256")]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=validation[key]:
            raise ValueError(f"Entree initiale modifiee : {path}")
    for record in manifest["frames"]:
        if not (source/record["image_path"]).is_file():raise FileNotFoundError(record["image_path"])
    if shutil.disk_usage(root).free<6*2**30:raise OSError("Il faut 6 Gio libres avant le lancement")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    destination=root/"outputs"/(("fixed-duration-check-" if args.check_only else "fixed-duration-")+stamp)
    destination.mkdir(parents=True)
    state=dict(status="checking",source=str(source),original_points=1115,coarse_steps=200,
        fine_steps=10000,checkpoints=[2000,5000,10000],
        original_config_sha256=report["config_sha256"],
        duration_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        source_manifest_sha256=validation["source_manifest_sha256"],source_cloud_sha256=validation["source_cloud_sha256"])
    (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
    print("\nTRUE SKATE - TEST DE DUREE D'ENTRAINEMENT",flush=True)
    print("Dossier :",destination,flush=True)
    print("Initialisation originale : 1115 points; memes images, cameras et temps.",flush=True)
    print("200 etapes coarse puis 10000 fine. Sauvegardes/evaluations : 2000, 5000, 10000.",flush=True)
    print("La densification conserve ses echeances initiales (fin a 1300); on teste davantage d'optimisation.",flush=True)
    print("Estimation indicative : 10-20 min. Pourcentages/perte/PSNR et rappels toutes les 15 s.",flush=True)
    print("Les rendus comparatifs complets seront generes apres l'entrainement. Aucune installation de paquets.",flush=True)
    gpu="import torch,diff_gaussian_rasterization,simple_knn._C; assert torch.cuda.is_available(); print('GPU:',torch.cuda.get_device_name(0)); print('CUDA existant : OK')"
    live_run(["wsl","-d","Ubuntu-22.04","-u","root","--exec","/opt/skate4d/venv/bin/python","-c",gpu],
        destination/"logs/preflight.log","1/3 Verification du GPU et des entrees",cwd=root,timeout=300)
    if args.check_only:
        state["status"]="checks_passed_no_training"
        (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
        print("\nVERIFICATIONS TERMINEES. Aucun entrainement lance.",flush=True)
        return
    live_run([sys.executable,"-u",root/"scripts/run_fixed_pilot.py","--source",source,
        "--output",destination/"run","--long"],destination/"logs/execution.log",
        "2/3 Copie WSL, entrainement jusqu'a 10000 etapes, rendus des trois checkpoints",cwd=root,
        timeout=5400,min_free_bytes=5*2**30)
    live_run([sys.executable,"-u",root/"scripts/compare_fixed_duration.py","--run",destination/"run",
        "--output",destination/"comparison"],destination/"logs/comparison.log",
        "3/3 Comparaison 2000 / 5000 / 10000 sur les memes images",cwd=root,timeout=300)
    state["status"]="completed_pending_visual_review"
    (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
    print("\nTERMINE. Le calcul GPU est termine.",flush=True)
    print("Video / 2000 / 5000 / 10000 :",destination/"comparison/test-cam13-comparison.jpg",flush=True)
    print("Courbes :",destination/"comparison/progression.png",flush=True)
    print("Mesures :",destination/"comparison/progression.json",flush=True)
    print("Journal complet :",destination/"logs/execution.log",flush=True)


if __name__=="__main__":
    try:main()
    except KeyboardInterrupt:
        print("\nInterruption demandee. Fichiers deja ecrits conserves.",flush=True)
        raise SystemExit(130)
    except Exception as error:
        print(f"\nARRET : {error}\nConsulter le dernier journal affiche.",file=sys.stderr,flush=True)
        raise SystemExit(1)
