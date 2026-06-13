#!/usr/bin/env bash
# ============================================================
# OpenClaw Custom — Script de Setup
# ============================================================
# O que este script faz:
#   1. Verifica dependências (docker, docker compose)
#   2. Cria diretórios de configuração e workspace
#   3. Gera um token de gateway seguro (se não existir)
#   4. Configura mounts extras (OPENCLAW_EXTRA_MOUNTS)
#   5. Salva todas as variáveis no arquivo .env
#   6. Roda o onboarding interativo dentro do container
#   7. Inicia o gateway via Docker Compose
#
# Uso:
#   ./docker-setup.sh
#
# Variáveis opcionais (defina antes de rodar ou no .env):
#   OPENCLAW_IMAGE         → Imagem Docker (padrão: ghcr.io/alefsanderribeiro/alefsander-openclaw:latest)
#   OPENCLAW_EXTRA_MOUNTS  → Mounts extras do host
#   OPENCLAW_HOME_VOLUME   → Volume nomeado para /home/node
#   OPENCLAW_DOCKER_APT_PACKAGES → Pacotes apt extras no build
#   OPENCLAW_SANDBOX       → Habilitar sandbox (1/true/yes/on)
#   OPENCLAW_SKIP_ONBOARDING   → Pular onboarding (1/true/yes/on)
# ============================================================

# Sai imediatamente se qualquer comando falhar
set -euo pipefail

# ============================================================
# 1. DETERMINA O DIRETÓRIO RAIZ DO PROJETO
# ============================================================
# BASH_SOURCE[0] é o caminho deste script.
# dirname extrai o diretório pai.
# cd + pwd resolve para o caminho absoluto.
# ============================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
EXTRA_COMPOSE_FILE="$ROOT_DIR/docker-compose.extra.yml"

# Define qual imagem usar (variável de ambiente ou padrão)
IMAGE_NAME="${OPENCLAW_IMAGE:-ghcr.io/alefsanderribeiro/alefsander-openclaw:latest}"

# Lê mounts extras e volume home das variáveis de ambiente
EXTRA_MOUNTS="${OPENCLAW_EXTRA_MOUNTS:-}"
HOME_VOLUME_NAME="${OPENCLAW_HOME_VOLUME:-}"

# ============================================================
# 2. VERIFICA DEPENDÊNCIAS
# ============================================================
# require_cmd verifica se um comando está disponível no PATH.
# Se não estiver, imprime erro e sai com código 1.
# ============================================================
require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ Dependência faltando: $1" >&2
    echo "   Instale o $1 e tente novamente." >&2
    exit 1
  fi
}

# Verifica Docker (engine principal)
require_cmd docker

# Verifica Docker Compose (plugin v2, não docker-compose legado)
if ! docker compose version >/dev/null 2>&1; then
  echo "❌ Docker Compose não disponível" >&2
  echo "   Instale o Docker Compose v2: https://docs.docker.com/compose/install/" >&2
  exit 1
fi

echo "✅ Docker: $(docker --version)"
echo "✅ Docker Compose: $(docker compose version --short)"

# ============================================================
# 3. CONFIGURA DIRETÓRIOS DE CONFIGURAÇÃO E WORKSPACE
# ============================================================
# OPENCLAW_CONFIG_DIR: onde fica openclaw.json, skills, memória
# OPENCLAW_WORKSPACE_DIR: área de trabalho do agente
# Se não definidos, usa ~/.openclaw como padrão.
# ============================================================
OPENCLAW_CONFIG_DIR="${OPENCLAW_CONFIG_DIR:-$HOME/.openclaw}"
OPENCLAW_WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-$HOME/.openclaw/workspace}"

# Cria os diretórios se não existirem (-p = cria pais também)
mkdir -p "$OPENCLAW_CONFIG_DIR"
mkdir -p "$OPENCLAW_WORKSPACE_DIR"

# Exporta para que o docker-compose.yml possa usar
export OPENCLAW_CONFIG_DIR
export OPENCLAW_WORKSPACE_DIR
export OPENCLAW_GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
export OPENCLAW_BRIDGE_PORT="${OPENCLAW_BRIDGE_PORT:-18790}"
export OPENCLAW_GATEWAY_BIND="${OPENCLAW_GATEWAY_BIND:-lan}"
export OPENCLAW_IMAGE="$IMAGE_NAME"
export OPENCLAW_DOCKER_APT_PACKAGES="${OPENCLAW_DOCKER_APT_PACKAGES:-}"
export OPENCLAW_EXTRA_MOUNTS="$EXTRA_MOUNTS"
export OPENCLAW_HOME_VOLUME="$HOME_VOLUME_NAME"

# ============================================================
# 4. GERA TOKEN DO GATEWAY
# ============================================================
# O token é a senha de acesso ao Gateway.
# Se já existe OPENCLAW_GATEWAY_TOKEN no ambiente, usa ele.
# Se não, gera um token aleatório de 64 caracteres hex.
# ============================================================
if [[ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
  echo "🔑 Gerando token de gateway..."

  # Tenta usar openssl (mais comum)
  if command -v openssl >/dev/null 2>&1; then
    OPENCLAW_GATEWAY_TOKEN="$(openssl rand -hex 32)"
  else
    # Fallback para Python3 se openssl não estiver disponível
    OPENCLAW_GATEWAY_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  fi

  echo "   Token gerado: ${OPENCLAW_GATEWAY_TOKEN:0:8}..."
  echo "   (token completo salvo no .env)"
fi

export OPENCLAW_GATEWAY_TOKEN

# ============================================================
# 5. CONFIGURA MOUNTS EXTRAS (docker-compose.extra.yml)
# ============================================================
# Se OPENCLAW_EXTRA_MOUNTS ou OPENCLAW_HOME_VOLUME estão definidos,
# gera um arquivo docker-compose.extra.yml com os volumes extras.
# Este arquivo é incluído automaticamente pelo docker compose.
# ============================================================
write_extra_compose() {
  local home_volume="$1"
  shift
  local mount

  # Cabeçalho do arquivo YAML
  cat >"$EXTRA_COMPOSE_FILE" <<'YAML'
# ============================================================
# Docker Compose Extra — Gerado automaticamente pelo docker-setup.sh
# ============================================================
# NÃO EDITE ESTE ARQUIVO MANUALMENTE.
# Ele é regenerado toda vez que o script de setup é executado.
# Para alterar mounts, edite OPENCLAW_EXTRA_MOUNTS no .env
# e rode ./docker-setup.sh novamente.
# ============================================================

services:
  gateway:
    volumes:
YAML

  # Se há volume nomeado para /home/node, adiciona
  if [[ -n "$home_volume" ]]; then
    printf '      - %s:/home/node\n' "$home_volume" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.openclaw\n' "$OPENCLAW_CONFIG_DIR" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.openclaw/workspace\n' "$OPENCLAW_WORKSPACE_DIR" >>"$EXTRA_COMPOSE_FILE"
  fi

  # Adiciona cada mount extra
  for mount in "$@"; do
    printf '      - %s\n' "$mount" >>"$EXTRA_COMPOSE_FILE"
  done

  # Mesma coisa para o serviço CLI
  cat >>"$EXTRA_COMPOSE_FILE" <<'YAML'
  cli:
    volumes:
YAML

  if [[ -n "$home_volume" ]]; then
    printf '      - %s:/home/node\n' "$home_volume" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.openclaw\n' "$OPENCLAW_CONFIG_DIR" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.openclaw/workspace\n' "$OPENCLAW_WORKSPACE_DIR" >>"$EXTRA_COMPOSE_FILE"
  fi

  for mount in "$@"; do
    printf '      - %s\n' "$mount" >>"$EXTRA_COMPOSE_FILE"
  done

  # Se o volume nomeado não é um path (ex: "openclaw_home"),
  # declara como volume Docker gerenciado
  if [[ -n "$home_volume" && "$home_volume" != *"/"* ]]; then
    cat >>"$EXTRA_COMPOSE_FILE" <<YAML
volumes:
  ${home_volume}:
YAML
  fi
}

# Parse dos mounts extras (separados por vírgula)
VALID_MOUNTS=()
if [[ -n "$EXTRA_MOUNTS" ]]; then
  # Separa por vírgula e trim de espaços
  IFS=',' read -r -a mounts <<<"$EXTRA_MOUNTS"
  for mount in "${mounts[@]}"; do
    # Remove espaços no início e fim
    mount="${mount#"${mount%%[![:space:]]*}"}"
    mount="${mount%"${mount##*[![:space:]]}"}"
    if [[ -n "$mount" ]]; then
      VALID_MOUNTS+=("$mount")
    fi
  done
fi

# Se há mounts extras ou volume home, gera o arquivo extra
if [[ -n "$HOME_VOLUME_NAME" || ${#VALID_MOUNTS[@]} -gt 0 ]]; then
  echo "📁 Configurando mounts extras..."

  # Compatibilidade com Bash 3.2 (macOS padrão)
  if [[ ${#VALID_MOUNTS[@]} -gt 0 ]]; then
    write_extra_compose "$HOME_VOLUME_NAME" "${VALID_MOUNTS[@]}"
  else
    write_extra_compose "$HOME_VOLUME_NAME"
  fi

  echo "   ${#VALID_MOUNTS[@]} mount(s) configurado(s)"
fi

# Monta a lista de arquivos compose para usar
COMPOSE_FILES=("$COMPOSE_FILE")
COMPOSE_ARGS=()
if [[ -f "$EXTRA_COMPOSE_FILE" ]]; then
  COMPOSE_FILES+=("$EXTRA_COMPOSE_FILE")
fi
for compose_file in "${COMPOSE_FILES[@]}"; do
  COMPOSE_ARGS+=("-f" "$compose_file")
done

# Comando hint para mostrar ao usuário
COMPOSE_HINT="docker compose"
for compose_file in "${COMPOSE_FILES[@]}"; do
  COMPOSE_HINT+=" -f ${compose_file}"
done

# ============================================================
# 6. SALVA VARIÁVEIS NO ARQUIVO .ENV
# ============================================================
# upsert_env atualiza ou adiciona variáveis no arquivo .env.
# Se a variável já existe, atualiza o valor.
# Se não existe, adiciona no final.
# Preserva variáveis existentes que não estão na lista.
# ============================================================
ENV_FILE="$ROOT_DIR/.env"

upsert_env() {
  local file="$1"
  shift
  local -a keys=("$@")
  local tmp
  tmp="$(mktemp)"
  # Lista de variáveis já processadas (evita duplicatas)
  local seen=" "

  # Se o arquivo já existe, lê linha por linha
  if [[ -f "$file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      local key="${line%%=*}"
      local replaced=false
      for k in "${keys[@]}"; do
        if [[ "$key" == "$k" ]]; then
          # Atualiza com o novo valor
          printf '%s=%s\n' "$k" "${!k-}" >>"$tmp"
          seen="$seen$k "
          replaced=true
          break
        fi
      done
      if [[ "$replaced" == false ]]; then
        # Mantém variáveis que não estamos atualizando
        printf '%s\n' "$line" >>"$tmp"
      fi
    done <"$file"
  fi

  # Adiciona variáveis novas que não estavam no arquivo
  for k in "${keys[@]}"; do
    if [[ "$seen" != *" $k "* ]]; then
      printf '%s=%s\n' "$k" "${!k-}" >>"$tmp"
    fi
  done

  # Substitui o arquivo original
  mv "$tmp" "$file"
}

# Salva todas as variáveis relevantes no .env
upsert_env "$ENV_FILE" \
  OPENCLAW_CONFIG_DIR \
  OPENCLAW_WORKSPACE_DIR \
  OPENCLAW_GATEWAY_PORT \
  OPENCLAW_BRIDGE_PORT \
  OPENCLAW_GATEWAY_BIND \
  OPENCLAW_GATEWAY_TOKEN \
  OPENCLAW_IMAGE \
  OPENCLAW_EXTRA_MOUNTS \
  OPENCLAW_HOME_VOLUME \
  OPENCLAW_DOCKER_APT_PACKAGES

echo "✅ Configurações salvas em $ENV_FILE"

# ============================================================
# 7. BUILD DA IMAGEM (se usando imagem local)
# ============================================================
# Se a imagem é ghcr.io/alefsanderribeiro/alefsander-openclaw:latest, faz build local.
# Se é uma imagem remota (alpine/openclaw, ghcr.io), faz pull.
# ============================================================
if [[ "$IMAGE_NAME" == "ghcr.io/alefsanderribeiro/alefsander-openclaw:latest" ]]; then
  echo ""
  echo "🔨 Build da imagem customizada: $IMAGE_NAME"
  docker compose "${COMPOSE_ARGS[@]}" build
else
  echo ""
  echo "📥 Pull da imagem: $IMAGE_NAME"
  docker compose "${COMPOSE_ARGS[@]}" pull || true
fi

# ============================================================
# 8. ONBOARDING INTERATIVO
# ============================================================
# Roda o wizard de configuração dentro do container.
# O wizard pede:
#   - Provider de IA (OpenAI, Anthropic, etc.)
#   - API key
#   - Modelo principal
#   - Canais de mensagem (Telegram, Discord, etc.)
#
# Pule com OPENCLAW_SKIP_ONBOARDING=1
# ============================================================
if [[ "${OPENCLAW_SKIP_ONBOARDING:-}" != "1" && \
      "${OPENCLAW_SKIP_ONBOARDING:-}" != "true" && \
      "${OPENCLAW_SKIP_ONBOARDING:-}" != "yes" && \
      "${OPENCLAW_SKIP_ONBOARDING:-}" != "on" ]]; then

  echo ""
  echo "🚀 Onboarding interativo"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Quando solicitado:"
  echo "  - Gateway bind: lan"
  echo "  - Gateway auth: token"
  echo "  - Gateway token: ${OPENCLAW_GATEWAY_TOKEN:0:8}..."
  echo "  - Tailscale exposure: Off"
  echo "  - Install Gateway daemon: No"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  docker compose "${COMPOSE_ARGS[@]}" run --rm cli onboard --no-install-daemon
fi

# ============================================================
# 9. CONFIGURA CANAIS DE MENSAGEM (opcional)
# ============================================================
# Mostra os comandos para configurar canais de mensagem.
# O usuário pode rodar depois, não é automático.
# ============================================================
echo ""
echo "📱 Configuração de canais (opcional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "WhatsApp (QR code):"
echo "  ${COMPOSE_HINT} run --rm cli channels login"
echo ""
echo "Telegram (bot token):"
echo "  ${COMPOSE_HINT} run --rm cli channels add --channel telegram --token <token>"
echo ""
echo "Discord (bot token):"
echo "  ${COMPOSE_HINT} run --rm cli channels add --channel discord --token <token>"
echo ""
echo "Documentação: https://docs.openclaw.ai/channels"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ============================================================
# 10. INICIA O GATEWAY
# ============================================================
# Sobe o container do gateway em background (-d = detached).
# O gateway começa a ouvir na porta configurada.
# ============================================================
echo ""
echo "🚀 Iniciando gateway..."
docker compose "${COMPOSE_ARGS[@]}" up -d gateway

# ============================================================
# 11. RESUMO FINAL
# ============================================================
# Mostra informações úteis para o usuário:
#   - Onde acessar o Gateway
#   - Onde estão as configurações
#   - Como ver logs
#   - Como verificar saúde do serviço
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ OpenClaw Gateway está rodando!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Control UI: http://127.0.0.1:${OPENCLAW_GATEWAY_PORT:-18789}/"
echo "📁 Config:     $OPENCLAW_CONFIG_DIR"
echo "📂 Workspace:  $OPENCLAW_WORKSPACE_DIR"
echo "🔑 Token:      ${OPENCLAW_GATEWAY_TOKEN:0:8}... (completo em $ENV_FILE)"
echo ""
echo "📋 Comandos úteis:"
echo "  Ver logs:         ${COMPOSE_HINT} logs -f gateway"
echo "  Ver saúde:        ${COMPOSE_HINT} exec gateway node dist/index.js health --token \"$OPENCLAW_GATEWAY_TOKEN\""
echo "  Dashboard URL:    ${COMPOSE_HINT} run --rm cli dashboard --no-open"
echo "  Parar:            ${COMPOSE_HINT} down"
echo "  Reiniciar:        ${COMPOSE_HINT} down && ${COMPOSE_HINT} up -d"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
