#!/usr/bin/env python3
"""Verifica/configura notificação Telegram no Kuma."""
import os

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

from uptime_kuma_api import UptimeKumaApi, NotificationType

api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

# Ver se NotificationType tem TELEGRAM
print("Has TELEGRAM type:", hasattr(NotificationType, "TELEGRAM"))

# Ver notificações existentes
notifs = api.get_notifications()
print(f"Notificações existentes: {len(notifs)}")
for n in notifs:
    print("  ", n.get("id"), n.get("name"), "| type:", n.get("type"), "| default:", n.get("isDefault"))

api.disconnect()
