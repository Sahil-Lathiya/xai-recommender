#!/usr/bin/env python3
"""Deploy XAI Recommender to DigitalOcean Droplet via SSH/SFTP."""

import io
import os
import sys
import tarfile
import time
from pathlib import Path

DROPLET_IP   = "178.128.168.101"
SSH_USER     = "root"
SSH_PASSWORD = "XaiSahil2026Rave"
APP_DIR      = "/opt/xai-recommender"
LOCAL_ROOT   = Path(r"c:\Users\abhay\OneDrive\Desktop\xai-recommender")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_print(text: str):
    """Print text, replacing characters that can't be encoded on this console."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def run(ssh, cmd, timeout=300, check=True):
    _safe_print(f"\n  $ {cmd}")
    chan = ssh.get_transport().open_session()
    chan.exec_command(cmd)
    out, err = b"", b""
    while True:
        if chan.recv_ready():
            out += chan.recv(4096)
        if chan.recv_stderr_ready():
            chunk = chan.recv_stderr(4096)
            err += chunk
            try:
                sys.stdout.write(chunk.decode(errors="replace"))
            except UnicodeEncodeError:
                sys.stdout.write(chunk.decode(errors="replace").encode("ascii", errors="replace").decode("ascii"))
            sys.stdout.flush()
        if chan.exit_status_ready():
            while chan.recv_ready():
                out += chan.recv(4096)
            while chan.recv_stderr_ready():
                err += chan.recv_stderr(4096)
            break
        time.sleep(0.1)
    rc = chan.recv_exit_status()
    if out.strip():
        _safe_print(f"    {out.decode(errors='replace').strip()}")
    if rc != 0 and check:
        raise RuntimeError(f"Command failed (rc={rc}): {cmd}")
    return rc, out.decode(errors="replace"), err.decode(errors="replace")


def make_tarball() -> bytes:
    """Bundle backend + frontend/dist into a tar.gz in memory."""
    print("\n[1/7] Creating deployment archive...")
    buf = io.BytesIO()

    # Paths to exclude
    skip_dirs  = {"__pycache__", ".git", "node_modules", ".venv", "venv",
                  ".pytest_cache", ".mypy_cache", "dist_old"}
    skip_exts  = {".pyc", ".pyo"}
    skip_files = {".env.example"}

    def should_skip(path: Path, base: Path) -> bool:
        for part in path.relative_to(base).parts:
            if part in skip_dirs:
                return True
        if path.suffix in skip_exts:
            return True
        if path.name in skip_files:
            return True
        return False

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # backend/ (everything — .env and models/ included)
        backend = LOCAL_ROOT / "backend"
        for p in sorted(backend.rglob("*")):
            if p.is_file() and not should_skip(p, LOCAL_ROOT):
                arcname = str(p.relative_to(LOCAL_ROOT)).replace("\\", "/")
                tar.add(str(p), arcname=arcname)
                print(f"    + {arcname}")

        # frontend/dist/ only (pre-built)
        dist = LOCAL_ROOT / "frontend" / "dist"
        if dist.exists():
            for p in sorted(dist.rglob("*")):
                if p.is_file():
                    arcname = str(p.relative_to(LOCAL_ROOT)).replace("\\", "/")
                    tar.add(str(p), arcname=arcname)
                    print(f"    + {arcname}")
        else:
            print("  WARNING: frontend/dist not found — frontend won't be deployed")

    buf.seek(0)
    data = buf.read()
    print(f"  Archive size: {len(data) / 1024 / 1024:.1f} MB")
    return data


NGINX_CONF = f"""\
server {{
    listen 80 default_server;
    server_name _;

    # API — backend on localhost:8000
    location /api/ {{
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }}

    location /health {{
        proxy_pass http://127.0.0.1:8000/health;
    }}

    # /api/health alias (convenience)
    location = /api/health {{
        proxy_pass http://127.0.0.1:8000/health;
    }}

    location /docs {{
        proxy_pass http://127.0.0.1:8000/docs;
    }}

    location /openapi.json {{
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }}

    # React SPA — serve from dist, fallback to index.html
    location / {{
        root       {APP_DIR}/frontend/dist;
        try_files  $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, must-revalidate";
    }}

    # Cache hashed static assets
    location /assets/ {{
        root       {APP_DIR}/frontend/dist;
        expires    1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""

SYSTEMD_SERVICE = f"""\
[Unit]
Description=XAI Recommender FastAPI Backend
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}/backend
Environment=PATH={APP_DIR}/backend/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart={APP_DIR}/backend/.venv/bin/uvicorn app.main:app \\
    --host 127.0.0.1 \\
    --port 8000 \\
    --workers 2 \\
    --log-level info \\
    --access-log
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def deploy():
    import paramiko

    print("=" * 60)
    print("  XAI Recommender — Remote Deploy")
    print(f"  Target: {SSH_USER}@{DROPLET_IP}")
    print("=" * 60)

    # ── 1. Build archive locally ──────────────────────────────────
    archive = make_tarball()

    # ── 2. Connect ────────────────────────────────────────────────
    print("\n[2/7] Connecting to Droplet...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(DROPLET_IP, username=SSH_USER, password=SSH_PASSWORD,
                timeout=30, banner_timeout=30)
    print("  Connected!")

    sftp = ssh.open_sftp()

    # ── 3. System packages ────────────────────────────────────────
    print("\n[3/7] Installing system packages...")
    run(ssh, "apt-get update -qq", timeout=120)
    run(ssh, (
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
        "python3 python3-pip python3-venv python3-dev "
        "build-essential nginx curl git"
    ), timeout=300)
    print("  Packages installed.")

    # ── 4. Upload archive ─────────────────────────────────────────
    print("\n[4/7] Uploading application archive...")
    remote_tar = "/tmp/xai-deploy.tar.gz"
    with sftp.open(remote_tar, "wb") as f:
        f.write(archive)
    print(f"  Uploaded {len(archive) / 1024 / 1024:.1f} MB to {remote_tar}")

    run(ssh, f"mkdir -p {APP_DIR}")
    run(ssh, f"tar -xzf {remote_tar} -C {APP_DIR}")
    run(ssh, f"rm {remote_tar}")
    run(ssh, f"ls {APP_DIR}/backend/app/main.py {APP_DIR}/frontend/dist/index.html")
    print("  Files extracted and verified.")

    # ── 5. Python virtualenv + dependencies ───────────────────────
    print("\n[5/7] Creating virtualenv and installing Python dependencies...")
    run(ssh, f"python3 -m venv {APP_DIR}/backend/.venv", timeout=60)
    run(ssh, (
        f"{APP_DIR}/backend/.venv/bin/pip install --upgrade pip --quiet"
    ), timeout=60)
    run(ssh, (
        f"{APP_DIR}/backend/.venv/bin/pip install "
        f"-r {APP_DIR}/backend/requirements.txt "
        f"--quiet --no-deps 2>&1 | tail -5"
    ), timeout=600)
    # Install with deps (needed for transitive reqs)
    run(ssh, (
        f"{APP_DIR}/backend/.venv/bin/pip install "
        f"-r {APP_DIR}/backend/requirements.txt "
        f"--quiet 2>&1 | tail -5"
    ), timeout=600)
    print("  Dependencies installed.")

    # ── 5b. Patch .env for production ─────────────────────────────
    print("\n  Patching CORS origins for production URL...")
    run(ssh, (
        f"sed -i 's|CORS_ORIGINS=.*|CORS_ORIGINS=http://{DROPLET_IP},http://localhost:5173|' "
        f"{APP_DIR}/backend/.env"
    ))
    run(ssh, f"grep CORS_ORIGINS {APP_DIR}/backend/.env")

    # ── 6. Nginx ──────────────────────────────────────────────────
    print("\n[6/7] Configuring Nginx...")
    with sftp.open("/etc/nginx/sites-available/xai", "w") as f:
        f.write(NGINX_CONF)

    run(ssh, "ln -sf /etc/nginx/sites-available/xai /etc/nginx/sites-enabled/xai", check=False)
    run(ssh, "rm -f /etc/nginx/sites-enabled/default", check=False)
    run(ssh, "nginx -t")
    run(ssh, "systemctl enable nginx")
    run(ssh, "systemctl restart nginx")
    print("  Nginx configured and restarted.")

    # ── 7. Systemd service ────────────────────────────────────────
    print("\n[7/7] Setting up systemd service...")
    with sftp.open("/etc/systemd/system/xai-backend.service", "w") as f:
        f.write(SYSTEMD_SERVICE)

    run(ssh, "systemctl daemon-reload")
    run(ssh, "systemctl enable xai-backend")
    run(ssh, "systemctl restart xai-backend")
    print("  Service started.")

    # ── Health check ──────────────────────────────────────────────
    print("\n  Waiting 30s for backend to load models...")
    time.sleep(30)

    for attempt in range(1, 7):
        rc, out, _ = run(ssh, "curl -sf http://127.0.0.1:8000/health", check=False)
        if rc == 0 and "healthy" in out:
            print(f"  Backend healthy after {attempt} attempt(s)!")
            break
        print(f"  Attempt {attempt}/6 — not ready yet, waiting 15s...")
        time.sleep(15)
    else:
        rc2, logs, _ = run(ssh, "journalctl -u xai-backend -n 50 --no-pager", check=False)
        print("  BACKEND LOGS:")
        print(logs)
        print("\n  WARNING: Backend health check failed. Check logs above.")

    # Public health check via nginx
    rc3, out3, _ = run(ssh, f"curl -sf http://127.0.0.1/health", check=False)
    print(f"\n  /health via nginx: {out3.strip() or 'no response'}")
    rc4, out4, _ = run(ssh, f"curl -sf http://127.0.0.1/api/health", check=False)
    print(f"  /api/health via nginx: {out4.strip() or 'no response'}")

    sftp.close()
    ssh.close()

    print("\n" + "=" * 60)
    print("  Deploy complete!")
    print(f"  Frontend:   http://{DROPLET_IP}/")
    print(f"  Health:     http://{DROPLET_IP}/health")
    print(f"  API health: http://{DROPLET_IP}/api/health")
    print(f"  Swagger:    http://{DROPLET_IP}/docs")
    print("=" * 60)


if __name__ == "__main__":
    deploy()
