"""Stream a subprocess to the terminal and a log, with elapsed-time updates."""
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time


def live_run(command, log_path, label, cwd=None, timeout=1200, heartbeat=15, min_free_bytes=0):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    print(f"\n>>> {label}\nJournal : {log_path}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(repr([str(x) for x in command]) + "\n")
        log.flush()
        process = subprocess.Popen([str(x) for x in command], cwd=cwd,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        lines = queue.Queue()
        def read_lines():
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)
        reader = threading.Thread(target=read_lines, daemon=True)
        reader.start()
        next_update = started + heartbeat
        try:
            while True:
                now = time.monotonic()
                if now - started > timeout:
                    raise TimeoutError(f"{label}: limite de {timeout}s atteinte; voir {log_path}")
                try:
                    line = lines.get(timeout=0.5)
                except queue.Empty:
                    line = ""
                if line is None:
                    break
                if line:
                    print(line, end="", flush=True)
                    log.write(line)
                    log.flush()
                if now >= next_update:
                    if min_free_bytes and shutil.disk_usage(log_path.parent).free < min_free_bytes:
                        raise OSError("Espace disque trop faible : arret pour conserver la reserve configuree")
                    elapsed = int(now - started)
                    print(f"[{elapsed // 60:02d}:{elapsed % 60:02d}] {label} : toujours en cours", flush=True)
                    next_update = now + heartbeat
            status = process.wait(timeout=10)
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            raise
        finally:
            process.stdout.close()
    elapsed = int(time.monotonic() - started)
    if status:
        raise RuntimeError(f"{label}: echec (code {status}). Journal : {log_path}")
    print(f"<<< Termine en {elapsed // 60:02d}:{elapsed % 60:02d}\n", flush=True)
