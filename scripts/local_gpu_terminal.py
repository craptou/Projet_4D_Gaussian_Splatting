"""Interactive Windows entry point: resume setup, then run the local GPU gate."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

from live_process import live_run


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    assert os.name == "nt", "Lancer ce script depuis le terminal Windows du projet."
    base = ["wsl", "-d", "Ubuntu-22.04", "-u", "root", "--exec"]
    probe = subprocess.run(base + ["/bin/bash", "-lc", "printf 'Ubuntu disponible\\n'; /usr/local/cuda-12.1/bin/nvcc --version | tail -2; /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"], check=True)
    if args.check_only:
        for name in ["setup_local_gpu.sh", "run_local_reference.py", "prepare_local_reference.py", "live_process.py"]:
            assert (root / "scripts" / name).is_file(), name
        print("Verification du lanceur terminee. Aucun entrainement lance.")
        return
    # Do not race another setup operating on the same Python environment.
    active = subprocess.run(base + ["/bin/bash", "-lc", "pgrep -af '^/opt/skate4d/venv/bin/python -m pip' || true"],
                            capture_output=True, encoding="utf-8")
    if active.stdout.strip():
        raise RuntimeError("Une installation Python est deja active. Attendre sa fin avant de relancer.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = root / "outputs" / ("dynerf-local-" + stamp)
    output.mkdir(parents=True)
    setup = subprocess.check_output(base + ["wslpath", "-a", "-u", str(root / "scripts/setup_local_gpu.sh")], encoding="utf-8").strip()
    print("\nTEST COURT : 4 vues d'entrainement, cam00 reservee, 30 instants.")
    print("Installation/reprise : estimation 5-20 min; un nouveau telechargement peut prendre davantage.")
    print("Compilation initiale : estimation 2-15 min. Entrainement + rendus : estimation 2-10 min.")
    print("Ces durees sont indicatives. Le temps ecoule sera affiche toutes les 15 secondes.")
    print("Les 12 etapes d'optimisation verifient l'execution, pas la qualite finale.\n", flush=True)
    live_run(base + ["/bin/bash", setup], output / "setup.log", "1/2 Installation ou reprise de l'environnement", timeout=7200)
    live_run([sys.executable, "-u", root / "scripts/run_local_reference.py", "--output", output],
             output / "execution.log", "2/2 Compilation, entrainement et rendu", cwd=root, timeout=3600)
    print(f"\nTERMINE. Comparaison : {output / 'comparison.jpg'}")
    print(f"Resultats et durees : {output / 'report.json'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu. Les journaux et fichiers deja produits sont conserves.")
        raise SystemExit(130)
    except Exception as error:
        print(f"\nARRET : {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
