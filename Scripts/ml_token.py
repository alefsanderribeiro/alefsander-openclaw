#!/usr/bin/env python3
"""
ml_token.py — Gerencia o access token da API do Mercado Livre (OAuth2)

- Renova automaticamente com refresh_token quando o access token expira
- Salva os tokens em ~/.openclaw/secrets/ml-tokens.json (permissão 600)
- Uso como CLI:
    python3 ml_token.py              # imprime o access token (renova se precisar)
    python3 ml_token.py --status     # mostra status sem imprimir o token
    python3 ml_token.py --force-refresh  # renova mesmo sem ter expirado
    python3 ml_token.py --file       # imprime o access token em --file <caminho>

Credenciais: ~/.openclaw/secrets/ml-api-credentials (ML_CLIENT_ID, ML_SECRET_KEY)
Tokens:      ~/.openclaw/secrets/ml-tokens.json
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SECRETS_DIR = Path(os.path.expanduser("~/.openclaw/secrets"))
CRED_FILE = SECRETS_DIR / "ml-api-credentials"
TOKEN_FILE = SECRETS_DIR / "ml-tokens.json"
OAUTH_URL = "https://api.mercadolibre.com/oauth/token"
MARGIN_SECONDS = 300  # renova 5 min antes de expirar


def load_creds():
    if not CRED_FILE.exists():
        sys.exit(f"❌ Credenciais não encontradas: {CRED_FILE}")
    creds = {}
    for line in CRED_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            creds[k] = v
    client_id = creds.get("ML_CLIENT_ID") or creds.get("ML_APP_ID")
    secret = creds.get("ML_SECRET_KEY")
    if not client_id or not secret:
        sys.exit("❌ ML_CLIENT_ID/ML_SECRET_KEY ausentes nas credenciais")
    return client_id, secret


def load_tokens():
    if not TOKEN_FILE.exists():
        sys.exit(f"❌ Tokens não encontrados: {TOKEN_FILE}")
    return json.loads(TOKEN_FILE.read_text())


def save_tokens(tokens):
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2, ensure_ascii=False))
    os.chmod(TOKEN_FILE, 0o600)


def is_expired(tokens, now=None):
    now = now or time.time()
    expires_at = tokens.get("expires_at")
    if not expires_at:
        return True
    return now >= (expires_at - MARGIN_SECONDS)


def refresh(client_id, secret, refresh_token):
    """Troca refresh_token por um novo access_token."""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": secret,
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(
        OAUTH_URL, data=data,
        headers={"accept": "application/json",
                 "content-type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        sys.exit(f"❌ Falha no refresh ({e.code}): {body}")


def get_access_token(force=False, verbose=False):
    client_id, secret = load_creds()
    tokens = load_tokens()
    now = time.time()

    if force or is_expired(tokens, now):
        if verbose:
            print("↻ Renovando access token...", file=sys.stderr)
        new = refresh(client_id, secret, tokens["refresh_token"])
        if "access_token" not in new:
            sys.exit(f"❌ Resposta inválida do refresh: {json.dumps(new)[:300]}")
        # O ML pode rotacionar o refresh_token — sempre salva o novo
        tokens["access_token"] = new["access_token"]
        tokens["refresh_token"] = new.get("refresh_token", tokens["refresh_token"])
        tokens["expires_in"] = new.get("expires_in", tokens.get("expires_in", 21600))
        tokens["expires_at"] = now + int(tokens["expires_in"])
        tokens["user_id"] = new.get("user_id", tokens.get("user_id"))
        tokens["ultimo_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        save_tokens(tokens)
        if verbose:
            print(f"✅ Token renovado! Válido por {tokens['expires_in']}s", file=sys.stderr)
    else:
        if verbose:
            restante = int(tokens["expires_at"] - now)
            print(f"✅ Token ainda válido (expira em {restante // 60} min)", file=sys.stderr)

    return tokens["access_token"], tokens


def main():
    parser = argparse.ArgumentParser(description="Gerencia o access token do Mercado Livre")
    parser.add_argument("--status", action="store_true", help="mostra status sem imprimir o token")
    parser.add_argument("--force-refresh", action="store_true", help="renova o token agora")
    parser.add_argument("--verbose", "-v", action="store_true", help="mensagens de progresso no stderr")
    args = parser.parse_args()

    token, tokens = get_access_token(force=args.force_refresh, verbose=args.verbose or args.status)

    if args.status:
        exp = tokens.get("expires_at")
        print(f"user_id:      {tokens.get('user_id')}")
        print(f"access_token: {'***' + token[-8:]}")
        print(f"expira em:    {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(exp))} "
              f"({int(tokens['expires_at'] - time.time()) // 60} min restantes)")
        print(f"refresh ok:   {'***' + tokens['refresh_token'][-8:]}")
    else:
        # Modo script: imprime só o token (usável em pipes: TOKEN=$(python3 ml_token.py))
        print(token)


if __name__ == "__main__":
    main()
