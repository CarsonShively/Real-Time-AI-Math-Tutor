import platform
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import requests


REPO = Path(__file__).resolve().parent
PYTHON = REPO / ".venv/bin/python"
LOCAL_URL = "http://127.0.0.1:8000"


def get_cloudflared():
    existing = shutil.which("cloudflared")

    if existing:
        return existing

    if platform.machine() not in {"x86_64", "AMD64"}:
        raise RuntimeError(
            f"Unsupported architecture: {platform.machine()}"
        )

    install_path = Path("/usr/local/bin/cloudflared")
    download_url = (
        "https://github.com/cloudflare/cloudflared/"
        "releases/latest/download/cloudflared-linux-amd64"
    )

    print("Installing cloudflared...")

    urllib.request.urlretrieve(
        download_url,
        install_path,
    )

    install_path.chmod(0o755)

    return str(install_path)


cloudflared = get_cloudflared()

server_process = subprocess.Popen(
    [
        str(PYTHON),
        "-m",
        "uvicorn",
        "demo.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ],
    cwd=REPO,
)

print("Waiting for server...")

for attempt in range(180):
    if server_process.poll() is not None:
        raise RuntimeError(
            f"Uvicorn exited with code "
            f"{server_process.returncode}"
        )

    try:
        response = requests.get(
            f"{LOCAL_URL}/docs",
            timeout=2,
        )

        if response.ok:
            break
    except requests.RequestException:
        pass

    if attempt % 12 == 0:
        print(f"Still loading... {attempt * 5}s")

    time.sleep(5)
else:
    server_process.terminate()
    raise RuntimeError("Server startup timed out.")

print("Server ready.")

tunnel_process = subprocess.Popen(
    [
        cloudflared,
        "tunnel",
        "--url",
        LOCAL_URL,
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

try:
    for line in tunnel_process.stdout:
        print(line, end="")

        match = re.search(
            r"https://[-a-z0-9]+\.trycloudflare\.com",
            line,
        )

        if match:
            print("\nPublic URL:", match.group(0))

except KeyboardInterrupt:
    print("\nStopping server and tunnel...")

finally:
    for process in (tunnel_process, server_process):
        if process.poll() is None:
            process.terminate()