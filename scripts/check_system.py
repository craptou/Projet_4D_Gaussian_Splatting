"""Write a repeatable host audit without printing environment secrets."""
import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def command(args):
    if not shutil.which(args[0]) and not Path(args[0]).exists():
        return "NOT FOUND"
    try:
        p = subprocess.run(args, capture_output=True, timeout=30)
        def decode(raw):
            return raw.decode("utf-16-le" if b"\x00" in raw else "utf-8", errors="replace")
        output = decode(p.stdout) + decode(p.stderr)
        output = "\n".join(line.rstrip() for line in output.splitlines())
        return f"exit={p.returncode}\n{output.strip()}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=root / "docs/system-report.md")
    args = p.parse_args()
    gh = root / ".tools/gh/bin/gh.exe"
    cmds = {"GPU / VRAM / driver": ["nvidia-smi"], "CUDA toolkit": ["nvcc", "--version"],
            "Python": [sys.executable, "--version"], "Python installations": ["py", "--list"],
            "Conda": ["conda", "--version"], "Mamba": ["mamba", "--version"],
            "Micromamba": ["micromamba", "--version"], "Git": ["git", "--version"],
            "GitHub CLI": [str(gh) if gh.exists() else "gh", "--version"],
            "GitHub authentication": [str(gh) if gh.exists() else "gh", "auth", "status"],
            "CMake": ["cmake", "--version"], "MSVC": ["cl"], "GCC": ["gcc", "--version"],
            "COLMAP": ["colmap", "-h"], "FFmpeg": ["ffmpeg", "-version"],
            "FFprobe": ["ffprobe", "-version"]}
    if platform.system() == "Windows":
        cmds["CPU / RAM / OS"] = ["powershell", "-NoProfile", "-Command",
             "@{CPU=(Get-CimInstance Win32_Processor).Name; OS=(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,TotalVisibleMemorySize)} | ConvertTo-Json -Depth 3"]
        cmds["WSL distributions"] = ["wsl", "--list", "--verbose"]
    cmds["PyTorch"] = [sys.executable, "-c", "import torch; print(torch.__version__, torch.version.cuda); print('GPU available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU'); print(torch.cuda.get_arch_list())"]
    sections = ["# System report", "Audit date: 2026-10-19 (America/Bogota). Re-run to refresh; reports describe the invoking Python environment.",
                f"Platform: {platform.platform()}. Python: {sys.version.split()[0]}.",
                "## Interpretation\nWindows 11 host; WSL has no distribution. RTX 4050 Laptop: 6141 MiB VRAM; about 23.7 GiB usable RAM. CUDA UMD 13.4 is the driver's API capability, not an installed toolkit. Training is blocked by absent nvcc, compiler environment, Conda, and PyTorch. COLMAP CUDA capability is unknown because COLMAP is absent. Prefer WSL2 Ubuntu 22.04 for upstream Bash/CUDA tooling. No system driver or WSL changes were made. Portable GitHub CLI is confined to ignored .tools; helper dependencies to .venv. See environment/README.md for Ada compatibility and installation strategy."]
    for label, cmd in cmds.items():
        sections.append(f"## {label}\nCommand: `{ ' '.join(cmd) }`\n\n```text\n{command(cmd)}\n```")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n\n".join(sections)+"\n")
    print(args.output)
