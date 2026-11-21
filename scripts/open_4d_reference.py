"""Start the trained 4D model viewer from Windows, without installing packages."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    url = f"http://127.0.0.1:{args.port}"
    try:
        with urllib.request.urlopen(url+"/meta", timeout=2) as response:
            existing = json.load(response)
        if existing.get("application") != "skate4d-live-reference":
            raise RuntimeError("Le port est utilise par une autre application")
    except urllib.error.URLError:
        existing = None
    if existing:
        print("Visualiseur deja disponible :", url, flush=True)
        raise SystemExit(0)
    candidates = sorted(root.glob("outputs/dynerf-quality-*"), reverse=True)
    run = next((p for p in candidates if (p/"report.json").exists()
                and (p/"model/point_cloud/iteration_3000/deformation.pth").exists()), None)
    if run is None:
        raise RuntimeError("Aucun modele qualite termine a l'etape 3000")
    base = ["wsl", "-d", "Ubuntu-22.04", "-u", "root", "--exec"]
    def wsl_path(path):
        return subprocess.check_output(base+["wslpath", "-a", "-u", str(path)], encoding="utf-8").strip()
    subprocess.run(base+["mkdir", "-p", "/root/skate4d/project/viewer"], check=True)
    for relative in ["scripts/view_4d_reference.py", "viewer/reference4d.html"]:
        subprocess.run(base+["cp", wsl_path(root/relative), "/root/skate4d/project/"+relative], check=True)
    output = root/"outputs/4d-viewer"
    output.mkdir(exist_ok=True)
    command = base+["/opt/skate4d/venv/bin/python", "-u", "/root/skate4d/project/scripts/view_4d_reference.py",
                   "--model", wsl_path(run/"model"), "--port", str(args.port)]
    with (output/"server.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            ready = False
            for attempt in range(120):
                if process.poll() is not None:
                    raise RuntimeError("Le visualiseur s'est arrete : voir outputs/4d-viewer/server.log")
                try:
                    with urllib.request.urlopen(url+"/meta", timeout=1) as response:
                        ready = json.load(response).get("application") == "skate4d-live-reference"
                    if ready:
                        break
                except urllib.error.URLError:
                    pass
                if attempt % 15 == 0:
                    print("Chargement du modele 4D sur la RTX 4050...", flush=True)
                time.sleep(1)
            if not ready:
                raise TimeoutError("Le visualiseur n'est pas encore accessible")
            (output/"session.json").write_text(json.dumps(dict(url=url, run=run.name, launcher_pid=process.pid), indent=2))
            print("Visualiseur pret :", url, flush=True)
            print("Utiliser le bouton Arreter le visualiseur pour liberer le GPU.", flush=True)
            process.wait()
        except BaseException:
            process.terminate()
            raise
