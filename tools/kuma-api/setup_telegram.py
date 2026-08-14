#!/usr/bin/env python3
"""Configura notificação Telegram no Kuma e liga em todos os monitores."""
import os, time

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

bot_token = secrets["KUMA_TELEGRAM_BOT_TOKEN"]
chat_id = secrets.get("KUMA_TELEGRAM_CHAT_ID", "")  # preencher no kuma-credentials

from uptime_kuma_api import UptimeKumaApi, NotificationType

api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

# 1. Verificar se já existe notificação Telegram
notifs = api.get_notifications()
existing = [n for n in notifs if str(n.get("type")) == "telegram" or "telegram" in str(n.get("type")).lower()]

if existing:
    notif_id = existing[0]["id"]
    print(f"ℹ️ Notificação Telegram já existe (id={notif_id}), atualizando...")
    try:
        api.edit_notification(
            notif_id,
            name="Telegram Alertas",
            type=NotificationType.TELEGRAM,
            telegramBotToken=bot_token,
            telegramChatID=chat_id,
        )
        print("✅ Atualizado")
    except Exception as e:
        print(f"❌ Erro ao editar: {e}")
else:
    print("Criando notificação Telegram...")
    try:
        result = api.add_notification(
            name="Telegram Alertas",
            type=NotificationType.TELEGRAM,
            telegramBotToken=bot_token,
            telegramChatID=chat_id,
            isDefault=True,
        )
        print("✅ Resultado:", result)
        # re-busca para pegar o id
        time.sleep(1)
        notifs = api.get_notifications()
        notif_id = notifs[-1]["id"] if notifs else None
    except Exception as e:
        print(f"❌ Erro ao criar: {e}")
        api.disconnect()
        exit(1)

# Testa a notificação
print("Testando notificação (deve chegar msg no Telegram)...")
try:
    api.test_notification(notif_id)
    print("✅ Teste enviado!")
except Exception as e:
    print(f"⚠️ Erro no teste (pode ser pq o teste usa config): {e}")

api.disconnect()
print("\n✅ Configuração do Telegram concluída!")
