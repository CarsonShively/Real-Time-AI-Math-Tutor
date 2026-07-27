import re
import subprocess
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent
PYTHON = REPO / ".venv/bin/python"
LOCAL_URL = "http://127.0.0.1:8000"

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
            f"Uvicorn exited with code {server_process.returncode}"
        )

    try:
        if requests.get(f"{LOCAL_URL}/docs", timeout=2).ok:
            break
    except requests.RequestException:
        pass

    if attempt % 12 == 0:
        print(f"Still loading... {attempt * 5}s")

    time.sleep(5)
else:
    raise RuntimeError("Server timed out.")

print("Server ready.")

tunnel_process = subprocess.Popen(
    [
        "cloudflared",
        "tunnel",
        "--url",
        LOCAL_URL,
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

public_url = None

for line in tunnel_process.stdout:
    print(line, end="")

    match = re.search(
        r"https://[-a-z0-9]+\.trycloudflare\.com",
        line,
    )

    if match and public_url is None:
        public_url = match.group(0)
        print("\nPublic URL:", public_url)

    if tunnel_process.poll() is not None:
        break