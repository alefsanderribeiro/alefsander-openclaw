# 🛠️ Scripts (`Scripts/`)

Automações prontas para o workspace do agente main. Instale com:

```bash
cp -r Scripts ~/.openclaw/workspace/
```

> Os scripts lêem credenciais de `~/.openclaw/secrets/` (nunca hardcoded).

## Mercado Livre

### `extrator_ml.py` — Extração de produtos

Extrai título, preço, imagem e descrição de produtos do Mercado Livre, com
**Camoufox** (anti-detecção — o ML bloqueia Playwright headless com
account-verification).

```bash
# Procedimento A — código + link de afiliado
python3 extrator_ml.py CODIGO "https://meli.la/XXXX"

# Procedimento B — só o link (recomendado)
python3 extrator_ml.py "https://meli.la/XXXX"
```

Saída: JSON com `titulo`, `preco`, `imagem_path`, `caption` + gravação no
SQLite (`.produtos.db`) + imagem em `img_produtos_mercado_livre/`.

### `ml_token.py` — Token OAuth2 do ML

Gerencia o access token com refresh automático. Credenciais em
`~/.openclaw/secrets/ml-api-credentials` (`ML_CLIENT_ID`, `ML_SECRET_KEY`).

```bash
python3 ml_token.py              # imprime o token (renova se precisar)
python3 ml_token.py --status     # status sem imprimir
python3 ml_token.py --force-refresh
```

### `consulta_produto.py` + `db_produtos.py` — Banco de produtos

```bash
python3 consulta_produto.py --codigo 9RV3YA-XXXX
python3 consulta_produto.py --ultimos 10
python3 consulta_produto.py --busca "termo"
python3 consulta_produto.py --stats
```

### `teste_rotas_ml.py` — Conformidade da API

Testa as rotas da API do ML documentadas localmente e gera relatório de
conformidade (200/403/404) em `teste-rotas-YYYY-MM-DD.md`.

### `crawl_ml_docs.py` — Documentação offline

Baixa a documentação do Mercado Livre (developers.mercadolivre.com.br) para
Markdown local — útil para consulta sem internet.

## Licitações / PNCP (dados públicos)

| Script | Função |
|---|---|
| `coletor_pncp_amostra.py` | Busca multi-filtro (UFs, modalidades, status) → amostra consolidada |
| `coletor_pncp_detalhes.py` | Baixa detalhes completos via API oficial (`/api/pncp/v1`) |
| `coletor_pncp_confronto.py` | Segunda amostra: modalidades novas + contratos + empenhos + PCA |
| `confrontar_schema.py` | Compara schema × dados reais, gera relatório + ALTERs |
| `gerar_diagrama_licitacoes.py` | Gera diagrama ERD interativo em HTML |

Saídas em `licitacoes/` (amostra, confronto, schema).

## Indexador de arquivos

### `indexador.py`

Varre `~/Documentos/Mega/Drive/` e indexa metadados + conteúdo em SQLite.

```bash
python3 indexador.py            # estrutura rápida (~1s)
python3 indexador.py --completo # + extração de conteúdo
python3 indexador.py --busca "termo"
python3 indexador.py --stats
```

## WhatsApp

### `wacli-sync.sh`

Sincroniza mensagens das contas WhatsApp (wacli) — usado via cron a cada 5 min.

> Requer o binário `wacli` no workspace (não incluído no repo por ser
> proprietário).

## Utilitários

### `cdp_shot.js`

Screenshot via Chrome DevTools Protocol (Node 24, WebSocket nativo):

```bash
node cdp_shot.js <wsUrl> <outPath> [width]
```
