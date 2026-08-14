#!/usr/bin/env python3
"""Testa a notificação Telegram configurada."""
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
# testar a notificacao id=1
try:
    r = api.test_notification(1)
    print("test_notification resultado:", r)
except TypeError as e:
    # tenta diferente: passar kwargs
    try:
        r = api.test_notification(id=1)
        print("teste (kwargs):", r)
    except Exception as e2:
        print("erro2:", e2)
except Exception as e:
    print("erro:", e)
api.disconnect()
