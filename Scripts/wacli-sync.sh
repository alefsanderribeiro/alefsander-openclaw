#!/bin/bash
# wacli-sync.sh - Sincroniza mensagens do WhatsApp (ambas as contas)
# Chamado pelo CRON openclaw

WACLI=/home/node/.openclaw/workspace/wacli
BASE=/home/node/.openclaw/workspace

cd "$BASE"

echo "=== Sync Aura ==="
timeout 120 "$WACLI" sync --once --store "$BASE/.wacli-store-aura" 2>&1
echo ""

echo "=== Sync Alef ==="
timeout 120 "$WACLI" sync --once --store "$BASE/.wacli-store-alef" 2>&1
echo ""

echo "Ambas contas sincronizadas."
