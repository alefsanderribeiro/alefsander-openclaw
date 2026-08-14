#!/usr/bin/env python3
"""
Corrige os monitores HTTP + remove os monitores 'SSL -' redundantes.
O SSL/certificado no Kuma é coberto por expiryNotification=True dentro do monitor HTTP,
NÃO por um monitor separado.
"""
import os

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

from uptime_kuma_api import UptimeKumaApi
api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

monitors = {m["id"]: m for m in api.get_monitors()}

def fix_http(mid, statuscodes, follow_redirect=True):
    m = monitors[mid]
    try:
        api.edit_monitor(
            mid,
            type=m["type"],
            name=m["name"],
            url=m["url"],
            interval=m.get("interval", 60),
            accepted_statuscodes=statuscodes,
            follow_redirect=follow_redirect,
            expiryNotification=True,   # ativa monitoramento de certificado SSL
        )
        print(f"  ✅ editado id={mid} {m['name']}")
    except Exception as e:
        print(f"  ❌ id={mid} {m['name']}: {e}")

def delete_monitor(mid):
    try:
        api.delete_monitor(mid)
        print(f"  🗑️ apagado id={mid} {monitors[mid]['name']}")
    except Exception as e:
        print(f"  ❌ deletar id={mid}: {e}")

print("\n=== Corrigindo monitores HTTP principais (follow_redirect + SSL expiry) ===")
# id 1: openclaw (200 ok)
fix_http(1, ["200-299", "300-399"])
# id 2: vaultwarden (200)
fix_http(2, ["200-299", "300-399"])
# id 3: stirling-pdf (401 = login, aceitar)
fix_http(3, ["200-299", "300-399", "400-499"])
# id 4: uptime kuma (302 redirect -> login)
fix_http(4, ["200-299", "300-399"])

print("\n=== Sites externos: corrigir HTTP + SSL ===")
# id 20: alefsander.dev (200)
fix_http(20, ["200-299", "300-399"])
# id 22: msservicos.com (200)
fix_http(22, ["200-299", "300-399"])

print("\n=== Removendo monitores 'SSL -' redundantes ===")
for mid in [5, 6, 7, 8, 21, 23]:  # SSL separados (agora cobertos por expiryNotification)
    delete_monitor(mid)

api.disconnect()
print("\n✅ Correção concluída!")
