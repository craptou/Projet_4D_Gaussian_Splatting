"""Windows terminal launcher for the next controlled True Skate experiment."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from live_process import live_run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only",action="store_true",help="Check files, disk, WSL and CUDA without training")
    parser.add_argument("--factor",type=int,choices=range(2,17),default=8)
    args=parser.parse_args()
    if os.name!="nt":raise ValueError("Lancer depuis le terminal PowerShell Windows")
    root=Path(__file__).resolve().parents[1]
    source=root/"data/processed/true-skate-fixed-pilot-v2"
    baseline=root/"outputs/true-skate-fixed-pilot"
    for path in [source/"manifest.json",source/"points3D_multipleview.ply",baseline/"report.json",baseline/"evaluation-2000.json"]:
        if not path.is_file():raise FileNotFoundError(f"Fichier requis absent : {path}")
    report=json.loads((baseline/"report.json").read_text())
    config=root/"configs/experiments/true-skate-fixed-pilot.py"
    if hashlib.sha256(config.read_bytes()).hexdigest()!=report["config_sha256"]:
        raise ValueError("Configuration modifiee depuis l'essai de reference : comparaison non controlee")
    if shutil.disk_usage(root).free<6*2**30:raise OSError("Il faut 6 Gio libres avant de lancer ce test")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    destination=root/"outputs"/(("fixed-next-check-" if args.check_only else "fixed-next-")+stamp)
    destination.mkdir(parents=True)
    print("\nSUITE TRUE SKATE - TEST DE L'INITIALISATION",flush=True)
    print("Dossier de cette execution :",destination,flush=True)
    print("Reference : essai deja termine; il ne sera pas reentraine.",flush=True)
    print(f"Modification testee : nuage initial reechantillonne x{args.factor}. Images/cameras/temps inchanges.",flush=True)
    print("Pas d'installation de paquets. Duree indicative : 5-15 min, dont environ 2-10 min de calcul GPU.",flush=True)
    print("Chaque phase affiche sa progression; un rappel de temps ecoule apparait toutes les 15 secondes.",flush=True)
    state=dict(source=str(source),baseline=str(baseline),factor=args.factor,config_sha256=report["config_sha256"],
        source_manifest_sha256=hashlib.sha256((source/"manifest.json").read_bytes()).hexdigest(),status="checking")
    (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
    gpu_check="import torch,diff_gaussian_rasterization,simple_knn._C; assert torch.cuda.is_available(); print('GPU:',torch.cuda.get_device_name(0)); print('Environnement CUDA existant : OK')"
    live_run(["wsl","-d","Ubuntu-22.04","-u","root","--exec","/opt/skate4d/venv/bin/python","-c",gpu_check],
        destination/"logs/preflight.log","1/4 Verification WSL et GPU (un demarrage a froid peut prendre plus longtemps)",cwd=root,timeout=300)
    if args.check_only:
        state["status"]="checks_passed_no_training"
        (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
        print("\nVERIFICATIONS TERMINEES. Aucun entrainement lance.",flush=True)
        return
    live_run([sys.executable,"-u",root/"scripts/prepare_dense_fixed_init.py","--source",source,
        "--output",destination/"input","--factor",str(args.factor)],destination/"logs/preparation.log",
        "2/4 Preparation du nuage initial et verification des images",cwd=root,timeout=300)
    live_run([sys.executable,"-u",root/"scripts/run_fixed_pilot.py","--source",destination/"input",
        "--output",destination/"run"],destination/"logs/execution.log",
        "3/4 Copie WSL, controle du chargeur, entrainement 200 + 2000 etapes et rendus",cwd=root,timeout=2400,min_free_bytes=5*2**30)
    live_run([sys.executable,"-u",root/"scripts/compare_fixed_runs.py","--baseline",baseline,
        "--candidate",destination/"run","--output",destination/"comparison"],destination/"logs/comparison.log",
        "4/4 Comparaison avec l'essai precedent sur les memes images",cwd=root,timeout=300)
    state["status"]="completed_pending_visual_review"
    (destination/"experiment.json").write_text(json.dumps(state,indent=2)+"\n")
    print("\nTERMINE. Le calcul GPU est termine.",flush=True)
    print("Video / ancien essai / nouvel essai :",destination/"comparison/test-cam13-comparison.jpg",flush=True)
    print("Metriques et differences :",destination/"comparison/summary.json",flush=True)
    print("Journal complet :",destination/"logs/execution.log",flush=True)
    print("Ce test concerne l'initialisation; le traitement specifique de la planche reste une experience separee.",flush=True)


if __name__=="__main__":
    try:main()
    except KeyboardInterrupt:
        print("\nInterruption demandee. Les journaux et resultats deja ecrits sont conserves.",flush=True)
        raise SystemExit(130)
    except Exception as error:
        print(f"\nARRET : {error}\nConsulter le dernier chemin de journal affiche.",file=sys.stderr,flush=True)
        raise SystemExit(1)
