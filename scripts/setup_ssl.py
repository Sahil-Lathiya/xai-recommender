#!/usr/bin/env python3
"""
One-shot SSL + domain setup for xairecommender.me.

Run AFTER DNS has propagated:
  py -3.11 scripts/setup_ssl.py

What this does:
  1. Installs certbot on the Droplet
  2. Obtains Let's Encrypt certs for api.xairecommender.me
  3. Rewrites Nginx with domain-aware server blocks + HTTPS
  4. Reloads Nginx

Prerequisites (do these first):
  A) In Namecheap Advanced DNS:
       A     @    <Vercel IP shown in Vercel dashboard>   Automatic
       CNAME www  cname.vercel-dns.com.                   Automatic
       A     api  178.128.168.101                         Automatic
  B) In Vercel dashboard → Domains → add xairecommender.me + www
  C) Wait ~5-30 min for DNS to propagate, then run this script
"""
import sys
import time
from pathlib import Path

DROPLET_IP   = "178.128.168.101"
SSH_USER     = "root"
SSH_PASSWORD = ""   # set via: export SSH_PASSWORD=<your-root-password>
APP_DIR      = "/opt/xai-recommender"
DOMAIN       = "api.xairecommender.me"
EMAIL        = "thakkarnishit007@gmail.com"

NGINX_SSL_CONF = f"""\
# HTTP → HTTPS redirect
server {{
    listen 80;
    server_name {DOMAIN};
    return 301 https://$host$request_uri;
}}

# HTTPS API server
server {{
    listen 443 ssl;
    server_name {DOMAIN};

    ssl_certificate     /etc/letsencrypt/live/{DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    # Proxy all traffic to FastAPI
    location / {{
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }}
}}

# HTTP fallback (IP direct access — for health checks / deploy script)
server {{
    listen 80 default_server;
    server_name _;

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

    location = /api/health {{
        proxy_pass http://127.0.0.1:8000/health;
    }}

    location /docs {{
        proxy_pass http://127.0.0.1:8000/docs;
    }}

    location /openapi.json {{
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }}

    location / {{
        root       {APP_DIR}/frontend/dist;
        try_files  $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, must-revalidate";
    }}

    location /assets/ {{
        root       {APP_DIR}/frontend/dist;
        expires    1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""


def run(ssh, cmd, timeout=300, check=True):
    print(f"\n  $ {cmd}")
    chan = ssh.get_transport().open_session()
    chan.exec_command(cmd)
    out, err = b"", b""
    while True:
        if chan.recv_ready():
            out += chan.recv(4096)
        if chan.recv_stderr_ready():
            chunk = chan.recv_stderr(4096)
            err += chunk
            sys.stdout.write(chunk.decode(errors="replace"))
            sys.stdout.flush()
        if chan.exit_status_ready():
            while chan.recv_ready():
                out += chan.recv(4096)
            while chan.recv_stderr_ready():
                err += chan.recv_stderr(4096)
            break
        time.sleep(0.1)
    rc = chan.recv_exit_status()
    text = out.decode(errors="replace").strip()
    if text:
        print(f"    {text}")
    if rc != 0 and check:
        raise RuntimeError(f"Command failed (rc={rc}): {cmd}")
    return rc, out.decode(errors="replace"), err.decode(errors="replace")


def main():
    import os
    import paramiko

    password = os.environ.get("SSH_PASSWORD") or SSH_PASSWORD
    if not password:
        print("ERROR: set SSH_PASSWORD env var before running this script.")
        sys.exit(1)

    print("=" * 60)
    print("  XAI Recommender — SSL Setup")
    print(f"  Domain: {DOMAIN}")
    print(f"  Target: {SSH_USER}@{DROPLET_IP}")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(DROPLET_IP, username=SSH_USER, password=password,
                timeout=30, banner_timeout=30)
    print("\n  Connected!")

    sftp = ssh.open_sftp()

    # 1. Verify DNS resolves to this droplet
    print("\n[1/4] Checking DNS resolution...")
    rc, out, _ = run(ssh, f"getent hosts {DOMAIN} || host {DOMAIN}", check=False)
    if DROPLET_IP not in out:
        print(f"\n  ERROR: {DOMAIN} does not resolve to {DROPLET_IP}")
        print(f"  Resolved to: {out.strip()}")
        print("  Wait for DNS propagation and try again.")
        ssh.close()
        sys.exit(1)
    print(f"  DNS OK — {DOMAIN} -> {DROPLET_IP}")

    # 2. Install certbot
    print("\n[2/4] Installing certbot...")
    run(ssh, "apt-get update -qq", timeout=120)
    run(ssh, (
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
        "certbot python3-certbot-nginx"
    ), timeout=300)
    print("  Certbot installed.")

    # 3. Obtain certificate (standalone mode — stop nginx briefly)
    print(f"\n[3/4] Obtaining Let's Encrypt certificate for {DOMAIN}...")
    run(ssh, "systemctl stop nginx")
    try:
        run(ssh, (
            f"certbot certonly --standalone --non-interactive --agree-tos "
            f"--email {EMAIL} -d {DOMAIN}"
        ), timeout=120)
        print("  Certificate obtained!")
    finally:
        run(ssh, "systemctl start nginx", check=False)

    # 4. Write new Nginx config + reload
    print("\n[4/4] Updating Nginx with SSL config...")
    with sftp.open("/etc/nginx/sites-available/xai", "w") as f:
        f.write(NGINX_SSL_CONF)

    run(ssh, "nginx -t")
    run(ssh, "systemctl reload nginx")

    # Set up auto-renewal
    run(ssh, (
        "bash -c 'echo \"0 3 * * * root certbot renew --quiet --post-hook "
        "\\\"systemctl reload nginx\\\"\" > /etc/cron.d/certbot-renew'"
    ), check=False)

    sftp.close()
    ssh.close()

    print("\n" + "=" * 60)
    print("  SSL Setup complete!")
    print(f"  API:     https://{DOMAIN}")
    print(f"  Health:  https://{DOMAIN}/health")
    print(f"  Swagger: https://{DOMAIN}/docs")
    print()
    print("  NEXT STEP: Update Vercel env var:")
    print(f"    VITE_API_BASE_URL = https://{DOMAIN}")
    print("  Then redeploy frontend from Vercel dashboard or:")
    print("    npm run build  (in frontend/) then re-run remote_deploy.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
