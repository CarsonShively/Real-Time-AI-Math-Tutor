import subprocess

subprocess.run(["pkill", "-f", "uvicorn"], check=False)
subprocess.run(["pkill", "-f", "cloudflared"], check=False)

print("Server and tunnel stopped.")