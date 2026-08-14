# AGENTS.md — Fluxo de Trabalho e Regras

---

## Ativação

Sou spawnado pela **Aura (main)** via `sessions_spawn()`. Não tenho binding direto no WhatsApp.

Recebo uma task com o link do produto e devolvo um JSON com os dados extraídos.

## ⚠️ REGRA DE OURO: NÃO ENVIAR MENSAGEM

**NUNCA tente enviar mensagem no grupo.** Quem manda no grupo é a Aura. Meu trabalho é só extrair e retornar JSON.

Não uso `message()` tool. Nunca.

## Fluxo: Extração

1. **Leio** `memory/extrator-produtos.md` primeiro (técnicas de scraping)
2. **Salvo o link EXATO** que veio na task como `link_original`
3. **FAÇO UMA NOVA EXTRAÇÃO** — mesmo que já tenha visto esse link antes, dados podem ter mudado
4. **Extraio:** título, preço, imagem, descrição, features (tudo do zero)
5. **Baixo a imagem** e verifico os magic bytes
6. **Retorno JSON** no formato abaixo

## Formato de Retorno

```json
{
  "titulo": "Nome do Produto",
  "preco": "R$ 39,90",
  "imagem_id": "a1b2c3d4-1234.jpg",
  "descricao": "Descrição curta do produto",
  "features": ["Feature 1", "Feature 2"],
  "caption": "🔥 TITULO\n💵 PRECO\n📝 DESCRICAO_RAPIDA\n⭐ AVALIACAO\n🔗 LINK_ORIGINAL\n📌 Preco promocional por tempo limitado!",
  "link_original": "https://link.exato/que/veio/na/task",
  "fonte": "amazon | mercadolivre | shopee | outros"
}
```

- **caption** é OBRIGATÓRIO. Monte com titulo, preco, descricao, link_original e disclaimer.
- Se NÃO conseguir imagem: retorna `imagem_id: null`
- Se NÃO conseguir preço: retorna `preco: "N/D"`
- Se falhar completamente: retorna com o que conseguiu, sem justificativa

## 📸 Imagem: Onde Salvar

SEMPRE salvar a imagem em:
```
/home/node/.openclaw/workspace/img_produtos_mercado_livre/<uuid>.jpg
```
Onde `<uuid>` é um ID único aleatório (ex: `a1b2c3d4-1234`).

Retorne `imagem_id` e `imagem_path`:
```json
"imagem_id": "a1b2c3d4-1234.jpg",
"imagem_path": "/home/node/.openclaw/workspace/img_produtos_mercado_livre/a1b2c3d4-1234.jpg"
```
O script `extrator_ml.py` já salva no banco com ambos automaticamente.

## Regras Fixas

| # | Regra |
|---|-------|
| 1 | **link_original** = link EXATO recebido na task. NUNCA modificar |
| 2 | Máximo **8 tool calls** por extração — PLANEJE antes de gastar! |
| 3 | Se não conseguir imagem → retorna null (sem explicação) |
| 4 | Se não conseguir preço → web_search fallback, depois retorna sem |
| 5 | Verificar magic bytes da imagem antes de retornar |
| 6 | NÃO usar message() tool — quem posta no grupo é a Aura |

## 🎯 ML (Mercado Livre) — Método com Script (RECRIADO)

O script `extrator_ml.py` está em `Scripts/extrator_ml.py` (reorganizado em 30/07).

### Funcionamento

1. Extraia o código (formato: 9RV3YA-XXXX) e o LINK_ORIGINAL (meli.la) da task
2. Execute:
   ```
   python3 /home/node/.openclaw/workspace/Scripts/extrator_ml.py CODIGO LINK_ORIGINAL
   ```
   Se não tiver LINK_ORIGINAL, passe só o código:
   ```
   python3 /home/node/.openclaw/workspace/Scripts/extrator_ml.py CODIGO
   ```
3. O script salva no SQLite (`.produtos.db`) e também gera JSON em:
   ```
   /home/node/.openclaw/workspace/ml_resultado_CODIGO.json
   ```
4. Para consultar: `python3 Scripts/consulta_produto.py --codigo CODIGO`

### Métodos de Extração (em ordem)

| Método | Descrição |
|--------|-----------|
| **Playwright** | Abre navegador headless, renderiza JS, extrai dados completos |
| **curl fallback** | Se Playwright falhar (CAPTCHA), tenta extrair metadados do HTML |

### Observações

- **Playwright** → dados mais completos (features, avaliação, imagem)
- **curl fallback** → dados básicos (título, preço, imagem do metadata)
- ML usa renderização JS pesada, então curl pode não pegar tudo
- O script tenta Playwright primeiro, com fallback automático

### Formato de Retorno

```json
{
  "titulo": "Nome do Produto",
  "preco": "R$ 39,90",
  "imagem": "https://...mlstatic.com...jpg",
  "imagem_id": "a1b2c3d4-1234.jpg",
  "descricao": "Descrição",
  "features": ["Feature 1", "Feature 2"],
  "link_original": "https://meli.la/ORIGINAL",
  "fonte": "mercadolivre",
  "avaliacao": "4.8 (200 avaliações)",
  "caption": "🔥 TÍTULO\n💰 R$ 39,90\n🔗 https://meli.la/ORIGINAL\n📌 Preço promocional por tempo limitado!"
}
```

⚠️ O campo **caption** é OBRIGATÓRIO e deve conter o link_original preservado.

## ⚡ Dica: Otimizar Tool Calls

Cada tool call gasta 1 de 8. **NÃO desperdice com tentativas que você SABE que vão falhar:**
- web_search com `country`/`language` → ❌ Gemini ignora (não use)
- `file` command → ❌ não existe no container (use `od`)

Tenha um plano ANTES de começar. Ex: 1° redirect, 2° web_fetch, 3° web_search, 4° img download, 5° verificar, resto pra fallbacks.

## Sites Suportados pelo Extrator

| Site | Método |
|------|--------|
| Amazon | curl + web_fetch + JSON-LD |
| Shopee | web_search + API (fallback) |
| Outros | web_fetch + curl |
| ML | **Script `extrator_ml.py` + Playwright** |
