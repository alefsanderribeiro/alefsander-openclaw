# TOOLS.md — Referência de Ferramentas

## Ferramentas Disponíveis

| Ferramenta | Uso |
|-----------|-----|
| `web_fetch` | Scraper principal |
| `web_search` | Fallback de preço/imagem |
| `exec` | Curl, download, verificação |
| `read` / `write` / `edit` | Ler/escrever memória e arquivos |
| `memory_search` / `memory_get` | Buscar na memória |
| `image` | Analisar imagem (formato, dimensões) |

## ⚠️ NUNCA usar message()

**Você NÃO envia mensagem no grupo.** Quem posta é a Aura (main).

Seu trabalho é **só extrair e retornar JSON**. Não tente usar message() tool, wacli ou qualquer outro método de envio.
|-----------|-----|
| `web_fetch` | Scraper principal |
| `web_search` | Fallback de preço/imagem |
| `exec` | Curl, download, verificação |
| `read` / `write` / `edit` | Ler/escrever memória e arquivos |
| `memory_search` / `memory_get` | Buscar na memória |
| `image` | Analisar imagem (formato, dimensões) |
| `message` | Enviar resposta no grupo (OBRIGATÓRIO para imagens) |

## message() — Como usar (OBRIGATÓRIO)

**Sempre que tiver uma imagem baixada, você DEVE usar message() tool com action="send".**
O auto-route NÃO envia imagens — só texto. Sem message(), a imagem nunca chega no grupo.

**Exemplo CORRETO (funciona sempre):**

```
message(action="send", channel="whatsapp", target="COLOQUE_O_JID_DO_GRUPO", media="/tmp/produto.jpg", caption="Texto com link_original")
```

- `action` = "send" (OBRIGATÓRIO — não esqueça!)
- `channel` = "whatsapp"
- `target` = "COLOQUE_O_JID_DO_GRUPO" (JID do grupo — placeholder, preencher no setup local)
- `media` = caminho completo da imagem baixada (ex: /tmp/produto.jpg)
- `caption` = texto que aparece com a imagem (deve conter o link_original)

**Quando NÃO tiver imagem (só texto):**

Não precisa de message() — o auto-route entrega o texto automaticamente.

## Curl — Comandos úteis para scraping

**Amazon (web_fetch bloqueia):**
```
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0" URL
```
Extrair preço: `grep -oP '"priceAmount":\{"value":\K[\d.]+'`
Extrair imagem: `grep -oP '"hiRes":"\Khttps://[^"]+'`

**Mercado Livre (web_fetch funciona):**
Seguir redirect: `curl -sL -o /dev/null -w '%{url_effective}' "https://meli.la/..."`

**Shopee (hostil, fallback rápido):**
Usar web_search em vez de curl. Meta tags: `og:title`, `og:image`.

## Verificação de imagem

Magic bytes conhecidos:
- `JFIF` ou `ÿØÿà` → JPEG
- `PNG` → PNG
- `RIFF....WEBP` → WebP
- `GIF` → GIF

Usar: `od -A x -t x1z -v -N 20 /caminho/imagem.jpg`

## 🔐 Vaultwarden — Credenciais Compartilhadas (padrão desde 09/08/2026)

> **Regra:** NUNCA salvar senhas em texto puro. Sempre buscar do Vaultwarden (organização `openclaw-agents`) no momento do uso. Cada agente vê **só o que foi compartilhado com ele** — a busca é feita com o usuário do próprio agente.

### Acesso (proxy TLS local — obrigatório)

O bw CLI 2026.6.0 bloqueia HTTP e o domínio público não resolve no container. Usar o proxy TLS local:

```bash
# 1. Garantir proxy rodando (se não estiver)
pgrep -f bwproxy/proxy.py || python3 ~/.openclaw/workspace/.bwproxy/proxy.py &

# 2. Sempre exportar
export NODE_TLS_REJECT_UNAUTHORIZED=0
export BW_AGENT=extrator   # <-- trocar pelo nome do agente
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
