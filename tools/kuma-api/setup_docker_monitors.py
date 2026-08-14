#!/usr/bin/env python3
"""
Registra o Docker Host local no Uptime Kuma e cria os monitores Docker.
Lê credenciais de ~/.openclaw/secrets/kuma-credentials
"""
import os, time

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

from uptime_kuma_api import UptimeKumaApi, MonitorType, DockerType

api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

# 1. Registrar Docker Host local (socket)
docker_host_id = None
hosts = api.get_docker_hosts()
print(f"Docker hosts existentes: {len(hosts)}")
if hosts:
    docker_host_id = hosts[0]["id"]
    print(f"Usando host existente: id={docker_host_id}")
else:
    print("Registrando Docker Host via socket local...")
    result = api.add_docker_host(
        name="servidor-ubuntu-home (socket local)",
        dockerType=DockerType.SOCKET,
        dockerDaemon="/var/run/docker.sock",
    )
    print("add_docker_host result:", result)
    # Re-busca para pegar o ID
    hosts = api.get_docker_hosts()
    if hosts:
        docker_host_id = hosts[0]["id"]
    time.sleep(1)

if not docker_host_id:
    print("❌ Não consegui obter o docker_host_id")
    api.disconnect()
    exit(1)

print(f"✅ docker_host_id = {docker_host_id}")

# 2. Criar monitores Docker para cada container
docker_containers = [
    "uptime-kuma",
    "ms-dashboard-app",
    "ms-dashboard-redis",
    "ms-dashboard-postgres",
    "ms-automatizar-mongodb",
    "ms-automatizar-redis",
    "ms-automatizar-whatsapp",
    "vaultwarden_server",
    "stirling-pdf",
    "caddy-proxy-tailscale",
    "alefsander-openclaw-gateway-1",
    "searxng",
]

print("\n=== Criando monitores Docker ===")
for c in docker_containers:
    try:
        api.add_monitor(
            type=MonitorType.DOCKER,
            name=f"Docker - {c}",
            docker_container=c,
            docker_host=docker_host_id,
            interval=60,
        )
        print(f"✅ Docker - {c}")
    except Exception as e:
        print(f"❌ Docker - {c} -> {e}")

api.disconnect()
print("\n✅ Monitores Docker configurados!")
