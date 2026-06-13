# ============================================================
# OpenClaw Custom Docker Image
# Base: Node.js 24 on Debian Bookworm Slim
# ============================================================
# Por que Debian e não Alpine?
# - O projeto oficial do OpenClaw usa Debian porque musl (Alpine)
#   causa problemas de compatibilidade com bibliotecas nativas
#   do Node.js e Python (ex: Whisper, OCR, etc.)
# - bookworm-slim é leve (~200MB base) e tem apt completo
# ============================================================

FROM node:24-bookworm-slim

# ============================================================
# Metadados da imagem
# ============================================================
LABEL maintainer="alefsander"
LABEL description="OpenClaw custom image with local tools (Whisper, PDF/OCR, Browser, ffmpeg, NVIDIA GPU)"
LABEL version="1.0.0"

# ============================================================
# Instala ferramentas do sistema
# ============================================================
# nano, vim         → Editores de texto para uso dentro do container
# git               → Controle de versão (skills, workspace)
# curl, wget        → Downloads e testes de conexão
# jq                → Parse JSON no terminal
# htop, tmux        → Monitoramento e sessões persistentes
# tree              → Visualizar estrutura de diretórios
# sudo              → Permitir installs em runtime (com senha desabilitada)
# ca-certificates   → Certificados SSL para downloads seguros
# gnupg2            → Assinar repositórios (NVIDIA)
#
# python3 + pip + venv → Necessário para Whisper e skills Python
# build-essential      → Compilar dependências nativas (npm, pip)
#
# poppler-utils   → pdftotext para leitura de PDFs
# tesseract-ocr   → OCR para PDFs escaneados e imagens
# ffmpeg          → Processamento de áudio/vídeo (Whisper, media)
# sox             → Manipulação de áudio
# chromium        → Browser para automação web (Playwright)
#
# NVIDIA CUDA     → Runtime libs para GPU acceleration (Whisper, PyTorch)
#                   O driver NVIDIA roda no HOST; o container só precisa
#                   das libs CUDA para comunicar com a GPU via nvidia-container-toolkit
# ============================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Editores e utilitários de terminal
    nano vim git curl wget jq htop tmux tree sudo \
    # Certificados e GPG (necessário para repositório NVIDIA)
    ca-certificates gnupg2 \
    # Python para skills (Whisper, etc.)
    python3 python3-pip python3-venv \
    # Compilação de deps nativas
    build-essential \
    # PDF e OCR
    poppler-utils tesseract-ocr tesseract-ocr-por tesseract-ocr-eng \
    # Áudio e vídeo
    ffmpeg sox \
    # Browser automation
    chromium \
    # Cleanup para reduzir tamanho da imagem
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# ============================================================
# Permite que o usuário 'node' use sudo sem senha
# ============================================================
# Isso é intencional: o agente pode precisar instalar skills,
# pacotes Python, ou ferramentas extras em runtime.
# O container é isolado, então não há risco para o host.
# ============================================================
RUN echo "node ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/node \
    && chmod 0440 /etc/sudoers.d/node

# ============================================================
# Instala o OpenClaw globalmente via npm
# ============================================================
# Usa --ignore-scripts para evitar builds desnecessários
# O OpenClaw é instalado como usuário root aqui, mas roda
# como 'node' no container (definido no docker-compose)
# ============================================================
RUN npm install -g openclaw@latest

# ============================================================
# Instala PyTorch com suporte a CUDA + Whisper
# ============================================================
# PyTorch é a dependência principal do Whisper.
# Instalamos a versão com CUDA 12.x para GPU acceleration.
# Se não houver GPU, PyTorch usa CPU automaticamente.
#
# --break-system-packages é necessário no Debian 12 (PEP 668)
# pois o Python é gerenciado pelo sistema.
#
# openai-whisper é a versão open-source que roda LOCALMENTE
# — sem custos de API, sem enviar áudio para fora
# ============================================================
# Instala PyTorch com CUDA (index-url separado para PyTorch)
RUN pip3 install --no-cache-dir --break-system-packages \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124 \
    --extra-index-url https://pypi.org/simple && \
    pip3 install --no-cache-dir --break-system-packages \
    openai-whisper

# ============================================================
# Configura diretório de trabalho
# ============================================================
WORKDIR /app

# ============================================================
# Cria diretórios que o OpenClaw espera
# ============================================================
RUN mkdir -p /home/node/.openclaw/workspace \
             /home/node/.openclaw/skills \
             /home/node/.openclaw/memory \
             /home/node/.openclaw/plugins \
             /home/node/.openclaw/agents \
             /home/node/.cache \
    && chown -R node:node /home/node

# ============================================================
# Variáveis de ambiente padrão
# ============================================================
ENV HOME=/home/node \
    TERM=xterm-256color \
    PATH=/home/node/.openclaw/npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PLAYWRIGHT_CHROMIUM_PATH=/usr/lib/chromium/chromium \
    WHISPER_MODEL=base \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# ============================================================
# Expõe portas do OpenClaw
# ============================================================
# 18789 → Gateway principal (WebSocket + HTTP)
# 18790 → Bridge para canais de mensagem
# ============================================================
EXPOSE 18789 18790

# ============================================================
# Health check integrado
# ============================================================
# Verifica se o gateway está respondendo
# Intervalo: 30s | Timeout: 10s | Retries: 3 | Start: 60s
# ============================================================
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -fsS http://127.0.0.1:18789/healthz || exit 1

# ============================================================
# Usuário padrão (segurança: não roda como root)
# ============================================================
# O container roda como 'node' (uid 1000) por padrão.
# Se precisar de root, use 'sudo' dentro do container.
# ============================================================
USER node

# ============================================================
# Comando padrão: inicia o OpenClaw CLI
# ============================================================
# O docker-compose sobrescreve este comando para rodar o gateway.
# Este entrypoint serve para o container CLI interativo.
# ============================================================
ENTRYPOINT ["node", "dist/index.js"]
CMD ["--help"]
