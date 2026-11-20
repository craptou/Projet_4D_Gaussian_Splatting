# Local GPU execution — 20 November 2026

[Español](local-gpu.es.md)

Colab did not work for the owner (the error was not supplied). The owner selected the local RTX 4050 instead. Initially WSL existed without a Linux distribution. Ubuntu 22.04 was installed in WSL2; the Windows NVIDIA driver was retained. CUDA 12.1 compiler/header packages and Python 3.10 were installed inside Linux. A native CUDA kernel compiled for sm_89 returned the expected checksum (285), and PyTorch 2.1.2-cu121 detected the RTX 4050.

**No 4DGaussians training has started.** Remaining Python dependencies, CUDA extension compilation, training and rendering are delegated to the foreground terminal launcher below so progress remains visible. A temporary NumPy 2 incompatibility during setup is addressed by the setup script's NumPy 1.26.4 pin. This is a compatibility port, not the original upstream environment.

From a PowerShell terminal in the repository:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-LocalGPU.ps1
```

This changes execution policy only for that child PowerShell process. The launcher resumes setup, reuses an installed PyTorch or completed installer where available, builds extensions, verifies the actual loader, and runs 2 coarse + 10 fine steps followed by 30 held-out renders. It streams logs and displays elapsed time every 15 seconds, with approximate duration ranges rather than a promised completion time. It prevents two launcher instances. On failure it stops and names the log. `-CheckOnly` verifies WSL, compiler/GPU access and launcher paths without starting setup/training; this check passed locally.

The reduced input already exists: cam01, cam05, cam12 and cam20 train; cam00 is held out; source frames 0–29 at 1352 × 1014, preserving original time `index / 300`. The initialization uses the previous 3,390-point training-only sparse map. Original videos are hard-linked, avoiding duplicate storage. Source stays under `/root/skate4d/project` for compilation; data and results remain in the Windows repository.

Each launch writes a new `outputs/dynerf-local-<UTC timestamp>/` directory. `setup.log` and `execution.log` capture installation/execution. A successful run will additionally produce `report.json`, `comparison.jpg` and detailed stage logs. These artifacts do not exist until those stages succeed. Twelve steps test execution, not convergence or useful reconstruction quality.

Helper syntax, live-output streaming, nonzero-exit handling, timeout handling and the check-only launcher were verified. The full GPU sequence remains unexecuted at this checkpoint. The script intentionally runs in the user's terminal rather than leaving a long installation dependent on an assistant tool session.
