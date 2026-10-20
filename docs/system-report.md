# System report

Audit date: 2026-10-19 (America/Bogota). Re-run to refresh; reports describe the invoking Python environment.

Platform: Windows-10-10.0.26200-SP0. Python: 3.11.9.

## Interpretation
Windows 11 host; WSL has no distribution. RTX 4050 Laptop: 6141 MiB VRAM; about 23.7 GiB usable RAM. CUDA UMD 13.4 is the driver's API capability, not an installed toolkit. Training is blocked by absent nvcc, compiler environment, Conda, and PyTorch. COLMAP CUDA capability is unknown because COLMAP is absent. Prefer WSL2 Ubuntu 22.04 for upstream Bash/CUDA tooling. No system driver or WSL changes were made. Portable GitHub CLI is confined to ignored .tools; helper dependencies to .venv. See environment/README.md for Ada compatibility and installation strategy.

## GPU / VRAM / driver
Command: `nvidia-smi`

```text
exit=0
Mon Oct 19 22:55:04 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 616.56                 KMD Version: 616.56        CUDA UMD Version: 13.4     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 4050 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   65C    P3             12W /   49W |       0MiB /   6141MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

## CUDA toolkit
Command: `nvcc --version`

```text
NOT FOUND
```

## Python
Command: `C:\Users\Raphaël Landry\Desktop\Computer_vision\projet\.venv\Scripts\python.exe --version`

```text
exit=0
Python 3.11.9
```

## Python installations
Command: `py --list`

```text
exit=0
-V:3.13 *        Python 3.13 (64-bit)
 -V:3.11          Python 3.11 (64-bit)
```

## Conda
Command: `conda --version`

```text
NOT FOUND
```

## Mamba
Command: `mamba --version`

```text
NOT FOUND
```

## Micromamba
Command: `micromamba --version`

```text
NOT FOUND
```

## Git
Command: `git --version`

```text
exit=0
git version 2.48.1.windows.1
```

## GitHub CLI
Command: `C:\Users\Raphaël Landry\Desktop\Computer_vision\projet\.tools\gh\bin\gh.exe --version`

```text
exit=0
gh version 2.102.0 (2026-09-30)
https://github.com/cli/cli/releases/tag/v2.102.0
```

## GitHub authentication
Command: `C:\Users\Raphaël Landry\Desktop\Computer_vision\projet\.tools\gh\bin\gh.exe auth status`

```text
exit=1
You are not logged into any GitHub hosts. To log in, run: gh auth login
```

## CMake
Command: `cmake --version`

```text
exit=0
cmake version 3.31.4

CMake suite maintained and supported by Kitware (kitware.com/cmake).
```

## MSVC
Command: `cl`

```text
NOT FOUND
```

## GCC
Command: `gcc --version`

```text
NOT FOUND
```

## COLMAP
Command: `colmap -h`

```text
NOT FOUND
```

## FFmpeg
Command: `ffmpeg -version`

```text
exit=0
ffmpeg version 9.0-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers
built with gcc 16.1.0 (Rev2, Built by MSYS2 project)
configuration: --enable-gpl --enable-version3 --enable-static --disable-w32threads --disable-autodetect --enable-cairo --enable-fontconfig --enable-iconv --enable-gnutls --enable-lcms2 --enable-libxml2 --enable-gmp --enable-bzlib --enable-lzma --enable-libsnappy --enable-zlib --enable-librist --enable-libsrt --enable-libssh --enable-libzmq --enable-avisynth --enable-libbluray --enable-libcaca --enable-libdvdnav --enable-libdvdread --enable-sdl2 --enable-libaribb24 --enable-libaribcaption --enable-libdav1d --enable-libdavs2 --enable-libopenjpeg --enable-libquirc --enable-libuavs3d --enable-libxevd --enable-libzvbi --enable-liboapv --enable-libqrencode --enable-librav1e --enable-libsvtav1 --enable-libvvenc --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxavs2 --enable-libxeve --enable-libxvid --enable-libaom --enable-libjxl --enable-libsvtjpegxs --enable-libvpx --enable-mediafoundation --enable-libass --enable-frei0r --enable-libfreetype --enable-libfribidi --enable-libharfbuzz --enable-liblensfun --enable-libvidstab --enable-libvmaf --enable-libzimg --enable-amf --enable-cuda-llvm --enable-cuvid --enable-dxva2 --enable-d3d11va --enable-d3d12va --enable-ffnvcodec --enable-libvpl --enable-nvdec --enable-nvenc --enable-vaapi --enable-vulkan --enable-libplacebo --enable-opencl --enable-libcdio --enable-openal --enable-libgme --enable-libmodplug --enable-libopenmpt --enable-libopencore-amrwb --enable-libmp3lame --enable-libshine --enable-libtheora --enable-libtwolame --enable-libvo-amrwbenc --enable-libcodec2 --enable-libilbc --enable-libgsm --enable-liblc3 --enable-libopencore-amrnb --enable-libopus --enable-libspeex --enable-libvorbis --enable-ladspa --enable-libbs2b --enable-libflite --enable-libmysofa --enable-librubberband --enable-libsoxr --enable-chromaprint --enable-whisper
libavutil      61.  1.100 / 61.  1.100
libavcodec     63.  1.100 / 63.  1.100
libavformat    63.  1.100 / 63.  1.100
libavdevice    63.  1.100 / 63.  1.100
libavfilter    12.  1.100 / 12.  1.100
libswscale     10.  1.100 / 10.  1.100
libswresample   7.  1.100 /  7.  1.100

Exiting with exit code 0
```

## FFprobe
Command: `ffprobe -version`

```text
exit=0
ffprobe version 9.0-full_build-www.gyan.dev Copyright (c) 2007-2026 the FFmpeg developers
built with gcc 16.1.0 (Rev2, Built by MSYS2 project)
configuration: --enable-gpl --enable-version3 --enable-static --disable-w32threads --disable-autodetect --enable-cairo --enable-fontconfig --enable-iconv --enable-gnutls --enable-lcms2 --enable-libxml2 --enable-gmp --enable-bzlib --enable-lzma --enable-libsnappy --enable-zlib --enable-librist --enable-libsrt --enable-libssh --enable-libzmq --enable-avisynth --enable-libbluray --enable-libcaca --enable-libdvdnav --enable-libdvdread --enable-sdl2 --enable-libaribb24 --enable-libaribcaption --enable-libdav1d --enable-libdavs2 --enable-libopenjpeg --enable-libquirc --enable-libuavs3d --enable-libxevd --enable-libzvbi --enable-liboapv --enable-libqrencode --enable-librav1e --enable-libsvtav1 --enable-libvvenc --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxavs2 --enable-libxeve --enable-libxvid --enable-libaom --enable-libjxl --enable-libsvtjpegxs --enable-libvpx --enable-mediafoundation --enable-libass --enable-frei0r --enable-libfreetype --enable-libfribidi --enable-libharfbuzz --enable-liblensfun --enable-libvidstab --enable-libvmaf --enable-libzimg --enable-amf --enable-cuda-llvm --enable-cuvid --enable-dxva2 --enable-d3d11va --enable-d3d12va --enable-ffnvcodec --enable-libvpl --enable-nvdec --enable-nvenc --enable-vaapi --enable-vulkan --enable-libplacebo --enable-opencl --enable-libcdio --enable-openal --enable-libgme --enable-libmodplug --enable-libopenmpt --enable-libopencore-amrwb --enable-libmp3lame --enable-libshine --enable-libtheora --enable-libtwolame --enable-libvo-amrwbenc --enable-libcodec2 --enable-libilbc --enable-libgsm --enable-liblc3 --enable-libopencore-amrnb --enable-libopus --enable-libspeex --enable-libvorbis --enable-ladspa --enable-libbs2b --enable-libflite --enable-libmysofa --enable-librubberband --enable-libsoxr --enable-chromaprint --enable-whisper
libavutil      61.  1.100 / 61.  1.100
libavcodec     63.  1.100 / 63.  1.100
libavformat    63.  1.100 / 63.  1.100
libavdevice    63.  1.100 / 63.  1.100
libavfilter    12.  1.100 / 12.  1.100
libswscale     10.  1.100 / 10.  1.100
libswresample   7.  1.100 /  7.  1.100
```

## CPU / RAM / OS
Command: `powershell -NoProfile -Command Get-CimInstance Win32_Processor | Select-Object Name; Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,TotalVisibleMemorySize`

```text
exit=0
Name                                 
----                                 
12th Gen Intel(R) Core(TM) i5-12450HX
```

## WSL distributions
Command: `wsl --list --verbose`

```text
exit=4294967295
Sous-syst�me Windows pour Linux n a aucune distribution install�e.
Vous pouvez r�soudre ce probl�me en installant une distribution avec les instructions ci-dessous :

Utiliser wsl.exe --list --online' pour r�pertorier les distributions disponibles
et 'wsl.exe --install <Distro>' � installer.
```

## PyTorch
Command: `C:\Users\Raphaël Landry\Desktop\Computer_vision\projet\.venv\Scripts\python.exe -c import torch; print(torch.__version__, torch.version.cuda); print('GPU available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU'); print(torch.cuda.get_arch_list())`

```text
exit=1
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'torch'
```
