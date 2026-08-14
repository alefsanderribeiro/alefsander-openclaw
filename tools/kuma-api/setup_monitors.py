#!/usr/bin/env python3
"""
Configura todos os monitores no Uptime Kuma via Socket.IO.
Lê credenciais de ~/.openclaw/secrets/kuma-credentials
"""
import os, sys, json, time

# Carrega credenciais do arquivo local
secrets = {}
cred_path = os.path.expanduser("~/.openclaw/secrets/kuma-credentials")
with open(cred_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

url = secrets.get("KUMA_URL", "http://uptime-kuma:3001")
user = secrets.get("KUMA_USER")
password = secrets.get("KUMA_PASSWORD")

from uptime_kuma_api import UptimeKumaApi, MonitorType

api = UptimeKumaApi(url)
print(f"Conectando em {url}...")
api.login(user, password)
print("✅ Login OK")

# --- Definição dos monitores ---
# Monitor Docker: verifica se o container está rodando e healthy
docker_containers = [
    "uptime-kuma",
    "ms-dashboard-app",
    "ms-dashboard-redis",
    "ms-dashboard-postgres",
    "ms-automatizar-mongodb",
    "ms-automatizar-redis",
    "ms-automatizar-whatsapp",
    "vaultwarden",
    "stirling-pdf",
    "caddy-proxy",
    "openclaw-gateway-1",
    "searxng",
]

# Monitor HTTP: verifica se o site responde (e retorna HTTP 200)
http_monitors = [
    ("OpenClaw Gateway (HTTP)", "https://openclaw.SEU_DOMINIO.com"),
    ("Vaultwarden (interno)", "http://vaultwarden:80"),
    ("Stirling-PDF (interno)", "http://stirling-pdf:8080"),
    ("Uptime Kuma (interno)", "http://uptime-kuma:3001"),
    ("Netdata (interno)", "http://netdata:19999"),
    ("SearXNG (interno)", "http://searxng:8080"),
]

# Monitor SSL/TLS: avisa antes do certificado expirar
ssl_monitors = [
    ("SSL - openclaw.SEU_DOMINIO.com", "openclaw.SEU_DOMINIO.com"),
    ("SSL - vault.SEU_DOMINIO.com", "vault.SEU_DOMINIO.com"),
    ("SSL - pdf.SEU_DOMINIO.com", "pdf.SEU_DOMINIO.com"),
    ("SSL - health.SEU_DOMINIO.com", "health.SEU_DOMINIO.com"),
]

# Monitor TCP: portas internas importantes
tcp_monitors = [
    ("TCP - Dashboard (3000)", "host.docker.internal", 3000) if False else None,  # placeholder
]

results = []

def add_docker(name, container):
    try:
        api.add_monitor(
            type=MonitorType.DOCKER,
            name=name,
            docker_container=container,
            interval=60,
        )
        results.append(f"✅ Docker: {name} ({container})")
    except Exception as e:
        results.append(f"❌ Docker: {name} -> {e}")

def add_http(name, url):
    try:
        api.add_monitor(
            type=MonitorType.HTTP,
            name=name,
            url=url,
            interval=60,
            accepted_statuscodes=["200-299", "300-399"],
        )
        results.append(f"✅ HTTP: {name}")
    except Exception as e:
        results.append(f"❌ HTTP: {name} -> {e}")

def add_ssl(name, hostname):
    try:
        api.add_monitor(
            type=MonitorType.HTTP,
            name=name,
            url=f"https://{hostname}",
            interval=86400,
            # Cert expiry monitor: Kuma verifica SSL automaticamente
        )
        results.append(f"✅ SSL: {name}")
    except Exception as e:
        results.append(f"❌ SSL: {name} -> {e}")

print("\n=== Criando monitores Docker ===")
for c in docker_containers:
    add_docker(f"Docker - {c}", c)

print("\n=== Criando monitores HTTP ===")
for name, u in http_monitors:
    add_http(name, u)

print("\n=== Criando monitores SSL ===")
for name, host in ssl_monitors:
    add_ssl(name, host)

print("\n=== RESUMO ===")
for r in results:
    print(r)

api.disconnect()
print("\n✅ Todos os monitores configurados!")
