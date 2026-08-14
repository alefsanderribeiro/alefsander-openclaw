#!/usr/bin/env python3
"""Testa o envio real via Telegram Bot API e a config no Kuma."""
import os, json, urllib.request

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

bot_token = secrets["KUMA_TELEGRAM_BOT_TOKEN"]
chat_id = secrets.get("KUMA_TELEGRAM_CHAT_ID", "")  # preencher no kuma-credentials

# 1. Teste direto na API do Telegram (confirma token + chat id)
print("=== Teste 1: enviar mensagem real via Bot API ===")
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
data = json.dumps({"chat_id": int(chat_id), "text": "🔔 Teste do Kuma: alertas configurados!"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print("✅ Mensagem enviada! ok:", resp.get("ok"))
except Exception as e:
    print("❌ Erro ao enviar:", e)

# 2. Verificar config da notificação no Kuma
print("\n=== Teste 2: verificar notificação no Kuma ===")
from uptime_kuma_api import UptimeKumaApi, NotificationType
api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
notifs = api.get_notifications()
print(f"Notificações: {len(notifs)}")
for n in notifs:
    print(f"  id={n.get('id')} name={n.get('name')} type={n.get('type')} isDefault={n.get('isDefault')}")
api.disconnect()
