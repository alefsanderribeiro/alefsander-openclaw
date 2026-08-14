# TOOLS.md — Notas de Ferramentas

## Acesso ao Host

**⚠️ Você roda dentro de um container Docker.** Os projetos do Alef estão no sistema **host**.

Use `exec` (sem `host:`) para comandos — o OpenClaw roteia automaticamente pro host.

**Caminhos importantes:**
- Projetos: `~/Documentos/Mega/Drive/Projetos/...` (resolvido no host como `/home/alefsander/...`)
- Node/Python/Docker: disponíveis no host normalmente
- OpenClaw workspace: `/home/node/.openclaw/workspace/` (dentro do container)

```bash
# Exemplo: rodar comando no host
exec(command="cd ~/Documentos/Mega/Drive/Projetos/Sistema/ms-dashboard-next && npm test")
```

### Paths dos projetos:

```bash
# Projetos
~/Documentos/Mega/Drive/Projetos/Sistema/ms-dashboard-next/
~/Documentos/Mega/Drive/Projetos/Trabalho/MS-Site/
~/Documentos/Mega/Drive/Projetos/Trabalho/MS-Agentes/
~/Documentos/Mega/Drive/Projetos/Trabalho/MS-Automatizar/
~/Documentos/Mega/Drive/Projetos/Trabalho/MS-WhatsApp/
~/Documentos/Mega/Drive/Projetos/Site/alefsander.dev-site-next/
~/Documentos/Mega/Drive/Projetos/Site/ms-site-next-public/
```

## Testes

```bash
# ms-dashboard-next (no host)
cd ~/Documentos/Mega/Drive/Projetos/Sistema/ms-dashboard-next

# Unitários — 1800+ testes
npm test

# Type check — factories contra schema Prisma
npx tsc --noEmit

# Integração (Docker isolado porta 5435)
./tests/scripts/run-integration.sh

# Grupos específicos
npx vitest run src/__tests__/actions/
npx vitest run src/__tests__/schemas/
npx vitest run src/__tests__/components/
npx vitest run src/__tests__/api/
```

## Busca Turbo

```bash
# ripgrep estático (disponível no workspace da Aura)
/home/node/.openclaw/workspace/rg "termo" /caminho --type ts -l
/home/node/.openclaw/workspace/rg "termo" /caminho --type py -l

# Indexador de arquivos (MEGA Drive)
cd /home/node/.openclaw/workspace
python3 Scripts/indexador.py --stats
python3 Scripts/indexador.py --busca "termo"
```

### Indexador (.catalogo.db)

Script Python que indexa `~/Documentos/Mega/Drive/` em um SQLite.

**Local:** `Scripts/indexador.py` (movido para pasta Scripts/)
**Banco:** `~/.openclaw/workspace/.catalogo.db` (~125 MB)

| Modo | Comando | O que faz |
|------|---------|-----------|
| Estrutura | `python3 Scripts/indexador.py` | Metadados (~1s) |
| Completo | `python3 Scripts/indexador.py --completo` | + Conteúdo (~2min) |
| Busca | `python3 Scripts/indexador.py --busca "termo"` | Full-text search |
| Stats | `python3 Scripts/indexador.py --stats` | Estatísticas |

**7.040 arquivos** indexados, **5.480 com conteúdo extraído**.

## Scripts do Workspace

Todos os scripts ficam em `Scripts/`:

| Script | Caminho | Função |
|--------|---------|--------|
| indexador.py | `Scripts/indexador.py` | Indexador MEGA Drive |
| extrator_ml.py | `Scripts/extrator_ml.py` | Extrator ML (Playwright) |
| db_produtos.py | `Scripts/db_produtos.py` | SQLite produtos |
| consulta_produto.py | `Scripts/consulta_produto.py` | Consulta produtos |

### Produtos ML — Banco de Dados

- **Banco:** `.produtos.db` (SQLite, na raiz do workspace)
- **Imagens:** `img_produtos_mercado_livre/`
- **Uso:**
  ```bash
  cd /home/node/.openclaw/workspace
  python3 Scripts/extrator_ml.py CODIGO [LINK]
  python3 Scripts/consulta_produto.py --codigo CODIGO
  python3 Scripts/consulta_produto.py --ultimos 10
  python3 Scripts/consulta_produto.py --stats
  ```

## Docker

Docker disponível no host. Use para testar integrações:

```bash
# Subir PostgreSQL isolado (porta 5435 — não conflita com dev/produção)
docker run --rm -d -p 5435:5432 -e POSTGRES_DB=test -e POSTGRES_PASSWORD=test postgres:17
```

## Cache npm

O container OpenClaw tem `/home/node/.npm` como tmpfs (256MB). Se `npm install` falhar com ENOSPC:

```bash
npm install --cache /home/node/.openclaw/.npm-cache --legacy-peer-deps
```

## Dica: exec vs ferramentas nativas

- Prefira `exec` para comandos shell (curl, git, npm, python, docker)
- Use `read`/`write`/`edit` para arquivos dentro do workspace ou projetos
- Use `web_fetch`/`web_search` para consultas web rápidas
- Se um comando shell parece lento, aumente `yieldMs` ou use `background`

## 🔐 Vaultwarden — Credenciais Compartilhadas (padrão desde 09/08/2026)

> **Regra:** NUNCA salvar senhas em texto puro. Sempre buscar do Vaultwarden (organização `openclaw-agents`) no momento do uso. Cada agente vê **só o que foi compartilhado com ele** — a busca é feita com o usuário do próprio agente.

### Acesso (proxy TLS local — obrigatório)

O bw CLI 2026.6.0 bloqueia HTTP e o domínio público não resolve no container. Usar o proxy TLS local:

```bash
# 1. Garantir proxy rodando (se não estiver)
pgrep -f bwproxy/proxy.py || python3 ~/.openclaw/workspace/.bwproxy/proxy.py &

# 2. Sempre exportar
export NODE_TLS_REJECT_UNAUTHORIZED=0
export BW_AGENT=dev   # <-- trocar pelo nome do agente (dev, orion, aura)
export BW_PASSWORD="SENHA_DO_COFRE_DO_AGENTE"

# 3. Desbloquear e sincronizar
export BW_SESSION=$(BW_AGENT=$BW_AGENT ~/.openclaw/workspace/bw unlock --passwordenv BW_PASSWORD --raw)
BW_AGENT=$BW_AGENT ~/.openclaw/workspace/bw sync --session "$BW_SESSION"

# 4. Buscar credencial na organização compartilhada
BW_AGENT=$BW_AGENT ~/.openclaw/workspace/bw get item "NOME_DO_ITEM" --session "$BW_SESSION"
```

### ⚠️ Lições (09/08/2026)

- **Email com case exato importa:** o email é o salt do hash — `+Aura` ≠ `+aura`. Usar SEMPRE o email exato da conta.
- **Rate limit:** 5+ tentativas falhas → IP bloqueado ~10 min → TUDO retorna "incorrect" (mesmo com senha certa). Se falhar várias vezes, PARAR e esperar.
- **Proxy:** config do bw aponta pra `https://localhost:8443` (nunca pra URL pública).
- **Extração de senha:** preferir variável de ambiente, nunca grep/sed de arquivos (erros de parsing).
