#!/usr/bin/env python3
"""Gera diagrama ERD INTERATIVO em HTML (licitacoes/schema/diagrama_fluxo_dados.html)."""
import html as H

# ---- dados ----
FONTES = {
    "S": ("#3b82f6", "Search API (radar)"),
    "C": ("#10b981", "Consulta API (detalhe)"),
    "I": ("#f59e0b", "Itens/Arquivos API"),
    "D": ("#8b5cf6", "Domínios API"),
    "X": ("#ec4899", "Dados Abertos (fornecedor)"),
    "P": ("#94a3b8", "Processado (ingestão)"),
}

TABELAS = [
    ("orgao", 70, 200, "#0ea5e9", "Órgão/entidade pública (comprador). Vem da Search API e do cadastro de órgãos do PNCP.", [
        ("cnpj", "S", "pk"), ("razao_social", "S", ""), ("nome_fantasia", "S", ""),
        ("id_pncp", "S", ""), ("esfera (F/E/M/D)", "S", ""), ("poder (E/L/J)", "S", ""),
        ("uf", "S", ""), ("municipio", "S", ""), ("validado", "S", ""),
        ("data_validacao", "S", ""), ("status_ativo", "S", ""),
    ]),
    ("unidade_orgao", 70, 450, "#38bdf8", "Unidade gestora vinculada ao órgão (ex.: uma secretaria, um batalhão).", [
        ("(orgao_cnpj, codigo)", "S", "pk"), ("id_pncp", "S", ""),
        ("nome", "S", ""), ("uf", "S", ""), ("municipio", "S", ""),
        ("orgao_cnpj → orgao", "S", "fk"),
    ]),
    ("licitacao", 560, 200, "#2563eb", "HUB CENTRAL — a compra/contratação. Chave natural = numero_controle_pncp. Tudo converge aqui.", [
        ("numero_controle_pncp", "S", "pk"),
        ("orgao_cnpj → orgao", "S", "fk"),
        ("unidade_codigo → unidade_orgao", "S", "fk"),
        ("ano · sequencial", "S", ""), ("numero_compra", "C", ""), ("processo", "C", ""),
        ("titulo", "S", ""), ("objeto", "C", ""),
        ("modalidade_id → dominio", "S", "fk"), ("situacao_id → dominio", "S", "fk"),
        ("tipo_instrumento_id → dominio", "C", "fk"), ("amparo_legal_id → dominio", "C", "fk"),
        ("modo_disputa_id → dominio", "C", "fk"), ("fonte_orcamentaria_id → dominio", "C", "fk"),
        ("srp", "C", ""), ("orcamento_sigiloso", "C", ""),
        ("valor_estimado", "C", ""), ("valor_homologado", "C", ""),
        ("data_publicacao", "S", ""), ("data_abertura_proposta", "C", ""),
        ("data_encerramento_proposta", "C", ""), ("data_assinatura", "S", ""),
        ("data_inicio_vigencia · fim", "S", ""),
        ("uf · municipio · esfera", "S", ""), ("cancelado", "S", ""),
        ("tem_resultado", "S", ""), ("emenda_parlamentar", "C", ""),
        ("url_pncp", "S", ""), ("raw_json", "P", ""),
    ]),
    ("licitacao_item", 560, 720, "#1d4ed8", "Itens da compra (36 campos: descrição, valores, quantidade, NCM/NBS, catálogo, margens).", [
        ("id", "P", "pk"), ("licitacao_id → licitacao", "P", "fk"),
        ("numero_item", "I", ""), ("descricao", "I", ""), ("material_servico (M/S)", "I", ""),
        ("valor_unitario_estimado", "I", ""), ("valor_total", "I", ""),
        ("quantidade · unidade_medida", "I", ""), ("orcamento_sigiloso", "I", ""),
        ("item_categoria_id → dominio", "I", "fk"), ("criterio_julgamento_id → dominio", "I", "fk"),
        ("situacao_item_id → dominio", "I", "fk"), ("tipo_beneficio_id → dominio", "I", "fk"),
        ("incentivo_produtivo_basico", "I", ""), ("ncm_nbs_codigo · descricao", "I", ""),
        ("catalogo · categoria · codigo_catalogo", "I", ""),
        ("margem_pref_normal · adicional", "I", ""),
        ("pct_margem_normal · adicional", "I", ""),
        ("tipo_margem_id → dominio", "I", "fk"), ("exige_conteudo_nacional", "I", ""),
        ("patrimonio · cod_reg_imob", "I", ""),
        ("tem_resultado · tem_imagem", "I", ""), ("raw_json", "P", ""),
    ]),
    ("documento", 1180, 200, "#0284c7", "ANEXOS da licitação/contrato/ata. url_fonte SEMPRE guardado (visualizar/baixar no PNCP); caminho_local opcional (arquivo baixado). Qualquer formato (PDF, ZIP, DOCX...).", [
        ("id", "P", "pk"), ("licitacao_id → licitacao", "P", "fk"),
        ("contrato_id → contrato", "P", "fk"), ("ata_id → ata", "P", "fk"),
        ("sequencial · titulo", "I", ""),
        ("tipo_documento_id → dominio (1..20)", "I", "fk"),
        ("url_fonte (sempre)", "I", ""),
        ("url_fonte_resumo", "I", ""),
        ("caminho_local (baixado)", "P", ""),
        ("tamanho_bytes · content_type", "P", ""),
        ("formato (PDF/ZIP/OUTROS)", "P", ""),
        ("eh_compactado · formato_interno", "P", ""),
        ("conteudo_interno (jsonb)", "P", ""),
        ("data_publicacao · data_baixado", "P", ""),
    ]),
    ("licitacao_resultado", 1180, 700, "#d97706", "Resultado/homologação por item (quem venceu, valores homologados, % desconto, ME/EPP, moeda estrangeira). 37 campos reais.", [
        ("id", "P", "pk"), ("licitacao_id → licitacao", "P", "fk"),
        ("numero_item · sequencial_resultado", "P", ""),
        ("fornecedor_cnpj → fornecedor", "P", "fk"),
        ("fornecedor_nome · tipo_pessoa", "P", ""),
        ("porte_fornecedor_id · nome", "P", ""),
        ("natureza_juridica_id · nome", "P", ""),
        ("situacao_resultado_id · nome", "P", ""),
        ("valor_total_homologado", "P", ""),
        ("valor_unitario_homologado", "P", ""),
        ("quantidade_homologada", "P", ""),
        ("percentual_desconto", "P", ""),
        ("ordem_classificacao_srp", "P", ""),
        ("data_resultado · data_cancelamento", "P", ""),
        ("aplicacao_beneficio_me_epp", "P", ""),
        ("moeda_estrangeira · valor_nominal", "P", ""),
        ("raw_json", "P", ""),
    ]),
    ("documento_parte_arquivo", 1560, 200, "#0d9488", "Inventário do conteúdo interno quando o anexo é ZIP/RAR/7z — permite visualizar/baixar cada arquivo de dentro do pacote.", [
        ("id", "P", "pk"), ("documento_id → documento", "P", "fk"),
        ("nome_arquivo", "P", ""), ("formato", "P", ""),
        ("tamanho_bytes", "P", ""), ("caminho_local", "P", ""),
        ("extraido", "P", ""),
    ]),
    ("fornecedor", 1180, 500, "#ec4899", "Fornecedor/empresa licitante. Vem da API Dados Abertos do Compras.gov.br (CNPJ, CNAE, porte).", [
        ("cnpj", "X", "pk"), ("razao_social", "X", ""), ("nome", "X", ""),
        ("cnae · cnae_nome", "X", ""), ("porte_id · porte_nome", "X", ""),
        ("municipio · uf", "X", ""), ("habilitado_licitar", "X", ""),
    ]),
    ("contrato", 1180, 1030, "#0891b2", "Contrato/empenho resultante da licitação (ou fruto de ata). 44 campos mapeados no confronto.", [
        ("numero_controle_pncp", "C", "pk"),
        ("licitacao_ref → licitacao", "C", "fk"),
        ("numero_controle_pncp_ata", "C", ""), ("orgao_cnpj → orgao", "C", "fk"),
        ("ano · sequencial · numero", "C", ""), ("tipo_contrato_id → dominio", "C", "fk"),
        ("categoria_processo_id", "C", ""), ("objeto", "C", ""),
        ("fornecedor_cnpj → fornecedor", "C", "fk"),
        ("fornecedor_subcontratado_cnpj · nome", "C", ""),
        ("tipo_pessoa · pais_fornecedor", "C", ""),
        ("valor_inicial · parcela · global · acumulado", "C", ""),
        ("numero_parcelas", "C", ""), ("data_assinatura", "C", ""),
        ("vigencia_inicio · fim", "C", ""), ("processo", "C", ""),
        ("receita · emenda · num_retificacao", "C", ""),
        ("fruto_adesao · tem_remanejamento", "C", ""),
        ("identificador_cipi · url_cipi", "C", ""),
        ("raw_json", "P", ""),
    ]),
    ("ata", 70, 630, "#6366f1", "Ata de Registro de Preços (ARP) — permite adesão de outros órgãos (carona).", [
        ("numero_controle_pncp_ata", "S", "pk"),
        ("licitacao_ref → licitacao", "S", "fk"),
        ("orgao_cnpj → orgao", "S", "fk"),
        ("fornecedor_cnpj → fornecedor", "S", "fk"),
        ("numero · ano", "S", ""), ("data_assinatura", "S", ""),
        ("vigencia_inicio · fim", "S", ""), ("valor_global", "S", ""),
        ("permite_adesao", "S", ""), ("situacao_id → dominio", "S", "fk"),
        ("raw_json", "P", ""),
    ]),
    ("pca", 70, 890, "#065f46", "Plano de Contratação Anual — RADAR ANTECIPADO (o que o órgão planeja comprar). 9 campos reais.", [
        ("id", "P", "pk"), ("orgao_cnpj → orgao", "P", "fk"),
        ("ano_pca", "P", ""), ("valor_total", "P", ""),
        ("quantidade", "P", ""), ("poder · esfera", "P", ""),
        ("razao_social", "P", ""),
        ("data_publicacao · data_atualizacao", "P", ""),
    ]),
    ("pca_item", 560, 1150, "#047857", "Item do plano de contratação (o que/quanto/quando o órgão pretende comprar). 30 campos reais.", [
        ("id", "P", "pk"), ("pca_id → pca", "P", "fk"),
        ("numero_item · codigo_item", "P", ""),
        ("descricao", "P", ""), ("codigo_unidade · nome_unidade", "P", ""),
        ("quantidade · unidade_fornecimento", "P", ""),
        ("valor_unitario · valor_total", "P", ""),
        ("valor_orcamento_exercicio", "P", ""),
        ("data_desejada", "P", ""),
        ("pdm_codigo · pdm_descricao", "P", ""),
        ("grupo_contratacao_codigo · nome", "P", ""),
        ("classificacao_superior_codigo · nome", "P", ""),
        ("categoria_item_pca_id · nome", "P", ""),
        ("catalogo_id · nome_catalogo", "P", ""),
    ]),
]


DOMINIOS = [
    "dominio_modalidade", "dominio_situacao", "dominio_tipo_documento",
    "dominio_tipo_instrumento", "dominio_amparo_legal", "dominio_modo_disputa",
    "dominio_criterio_julgamento", "dominio_tipo_beneficio", "dominio_item_categoria",
    "dominio_tipo_contrato", "dominio_fonte_orcamentaria", "dominio_tipo_margem",
    "dominio_formato_arquivo",
]

SETAS = [
    ("src_search", "src_search", "orgao", [(225, 114), (225, 200)], None),
    ("src_search", "src_search", "licitacao", [(565, 114), (565, 200)], None),
    ("src_consulta", "src_consulta", "licitacao", [(905, 114), (905, 200)], None),
    ("src_itens", "src_itens", "documento", [(1245, 114), (1245, 200)], None),
    ("src_dados", "src_dados", "fornecedor", [(1585, 114), (1585, 500)], None),
    ("src_dominios", "src_dominios", "dominios", [(1700, 114), (1700, 1480)], None),
    ("fk_orgao_licitacao", "orgao", "licitacao", [(400, 420), (480, 420), (480, 250), (560, 250)], "1:N"),
    ("fk_unidade_licitacao", "unidade_orgao", "licitacao", [(400, 500), (560, 500)], "1:N"),
    ("fk_orgao_unidade", "orgao", "unidade_orgao", [(235, 405), (235, 450)], "1:N"),
    ("fk_licitacao_item", "licitacao", "licitacao_item", [(890, 675), (890, 720)], "1:N"),
    ("fk_licitacao_doc", "licitacao", "documento", [(560, 250), (1180, 250)], "1:N"),
    ("fk_licitacao_contrato", "licitacao", "contrato", [(890, 675), (1035, 675), (1035, 1030), (1180, 1030)], "1:N"),
    ("fk_licitacao_ata", "licitacao", "ata", [(560, 675), (250, 675), (250, 630)], "1:N"),
    ("fk_licitacao_resultado", "licitacao", "licitacao_resultado", [(890, 675), (1000, 675), (1000, 700), (1180, 700)], "1:N"),
    ("fk_resultado_fornecedor", "licitacao_resultado", "fornecedor", [(1345, 700), (1345, 645)], "1:N"),
    ("fk_fornecedor_contrato", "fornecedor", "contrato", [(1345, 645), (1345, 1030)], "1:N"),
    ("fk_doc_parte", "documento", "documento_parte_arquivo", [(1510, 300), (1560, 300)], "1:N"),
    ("src_contrato_doc", "contrato", "documento", [(1260, 1030), (1260, 445)], "1:N"),
    ("fk_pca_item", "pca", "pca_item", [(400, 950), (480, 950), (480, 1150), (560, 1150)], "1:N"),
    ("fk_pca_orgao", "pca", "orgao", [(70, 950), (25, 950), (25, 405), (70, 405)], "1:N"),
]

W, HH = 1900, 1700

# ---- helpers SVG ----
def caixa(nome, x, y, cor, desc, campos):
    lh = 15
    h = 34 + len(campos) * lh + 6
    out = []
    out.append(f'<g class="tabela" data-nome="{nome}" data-x="{x}" data-y="{y}">')
    out.append(f'<rect class="node" x="{x}" y="{y}" width="330" height="{h}" rx="8" fill="#fff" stroke="{cor}" stroke-width="2"/>')
    out.append(f'<rect x="{x}" y="{y}" width="330" height="26" rx="8" fill="{cor}"/>')
    out.append(f'<text x="{x+12}" y="{y+18}" class="tbl">{H.escape(nome)}</text>')
    cy = y + 40
    for nome_campo, fonte, flag in campos:
        cor_f, _ = FONTES[fonte]
        dot = f'<circle class="dot" cx="{x+14}" cy="{cy-4}" r="3.4" fill="{cor_f}"/>'
        suf = ' <tspan class="key">🔑</tspan>' if flag == "pk" else (' <tspan class="key">⇢</tspan>' if flag == "fk" else '')
        out.append(f'<text x="{x+24}" y="{cy}" class="fld">{dot}<tspan>{H.escape(nome_campo)}</tspan>{suf}</text>')
        cy += lh
    out.append('</g>')
    return out, h

def seta(sid, de, para, points, label):
    pts = " ".join(f"{a},{b}" for a, b in points)
    s = f'<polyline class="edge" id="seta-{sid}" data-de="{de}" data-para="{para}" points="{pts}" marker-end="url(#arr)"/>'
    if label:
        mx = sum(p[0] for p in points) / len(points)
        my = sum(p[1] for p in points) / len(points)
        s += f'<text x="{mx}" y="{my-4}" class="elab">{label}</text>'
    return s

# ---- monta SVG ----
svg = []
svg.append(f'<svg id="svg" viewBox="0 0 {W} {HH}" xmlns="http://www.w3.org/2000/svg">')
svg.append('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/></marker></defs>')

# fontes (topo)
fx = [70, 410, 750, 1090, 1430]
fnames = [
    ("src_search", "Search API", "busca/radar · 53 campos", "S"),
    ("src_consulta", "Consulta API", "detalhe compra/contrato", "C"),
    ("src_itens", "Itens/Arquivos API", "itens + anexos", "I"),
    ("src_dominios", "Domínios API", "13 tabelas de referência", "D"),
    ("src_dados", "Dados Abertos", "fornecedor · CNAE · porte", "X"),
]
for (x, (sid, t, sub, cod)) in zip(fx, fnames):
    cor, _ = FONTES[cod]
    svg.append(f'<g class="fonte" data-nome="{sid}">')
    svg.append(f'<rect class="node" x="{x}" y="62" width="310" height="52" rx="8" fill="{cor}" opacity="0.92"/>')
    svg.append(f'<text x="{x+12}" y="82" class="ft">{H.escape(t)}</text>')
    svg.append(f'<text x="{x+12}" y="101" class="fts">{H.escape(sub)}</text>')
    svg.append('</g>')

# setas (desenha antes das caixas, por trás)
for sid, de, para, points, label in SETAS:
    svg.append(seta(sid, de, para, points, label))

# tabelas
for nome, x, y, cor, desc, campos in TABELAS:
    out, _ = caixa(nome, x, y, cor, desc, campos)
    svg.extend(out)

# faixa domínios
dy = 1480
svg.append(f'<g class="tabela" data-nome="dominios">')
svg.append(f'<rect class="zone" x="70" y="{dy}" width="1630" height="120" rx="10"/>')
svg.append(f'<text x="86" y="{dy+24}" class="zone-t">TABELAS DE DOMÍNIO — todas com (id PK · nome · descricao · status_ativo)</text>')
for i, d in enumerate(DOMINIOS):
    col = i % 4
    row = i // 4
    x = 90 + col * 400
    y = dy + 40 + row * 34
    svg.append(f'<text x="{x}" y="{y}" class="dom">• {H.escape(d)}</text>')
svg.append('</g>')

svg.append('</svg>')
svg_html = "".join(svg)

# ---- dados p/ JS ----
tabelas_js = {nome: {"desc": desc, "campos": [[c, f, fl] for c, f, fl in campos]} for nome, _, _, _, desc, campos in [(t[0], t[1], t[2], t[3], t[4], t[5]) for t in TABELAS]}
tabelas_js["dominios"] = {"desc": "Tabelas de referência consultadas pelas FKs (*_id) das demais tabelas.", "campos": [[d, "D", ""] for d in DOMINIOS]}
setas_js = [[sid, de, para] for sid, de, para, _, _ in SETAS]
fontes_js = {k: v for k, v in FONTES.items()}

import json as _json
json_tabelas = _json.dumps(tabelas_js, ensure_ascii=False)
json_setas = _json.dumps(setas_js)
json_fontes = _json.dumps(fontes_js)

# ---- HTML ----
html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Diagrama — Fluxo e Interligação dos Dados (Licitações PNCP)</title>
<style>
:root {{
  color-scheme: light dark;
  --bg:#f1f5f9; --fg:#0f172a; --muted:#64748b; --panel:#ffffff; --border:#cbd5e1;
  --edge:#94a3b8; --hl:#f59e0b;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg:#0b1220; --fg:#e2e8f0; --muted:#8fa0b8; --panel:#111a2c; --border:#26334d;
    --edge:#475569;
  }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.45 ui-sans-serif,system-ui,"Segoe UI",sans-serif; }}
header {{ position:sticky; top:0; z-index:10; background:var(--panel); border-bottom:1px solid var(--border); padding:12px 20px; display:flex; align-items:center; gap:18px; flex-wrap:wrap; }}
header h1 {{ font-size:17px; margin:0; font-weight:700; }}
header .sub {{ font-size:12px; color:var(--muted); }}
.controles {{ margin-left:auto; display:flex; gap:6px; align-items:center; }}
.controles button {{ background:var(--bg); color:var(--fg); border:1px solid var(--border); border-radius:6px; padding:5px 10px; font-size:13px; cursor:pointer; }}
.controles button:hover {{ border-color:var(--hl); }}
.legenda {{ display:flex; gap:14px; flex-wrap:wrap; font-size:11.5px; color:var(--muted); }}
.legenda span {{ display:inline-flex; align-items:center; gap:5px; }}
.legenda i {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
main {{ display:flex; gap:0; min-height:calc(100vh - 58px); }}
#wrap {{ flex:1; overflow:auto; padding:16px; }}
#wrap svg {{ width:100%; height:auto; min-width:1180px; display:block; transform-origin:top left; transition:transform .15s ease; }}
aside {{ width:330px; flex-shrink:0; border-left:1px solid var(--border); background:var(--panel); padding:16px; overflow-y:auto; max-height:calc(100vh - 58px); position:sticky; top:58px; }}
aside h2 {{ font-size:14px; margin:0 0 4px; }}
aside .desc {{ font-size:12.5px; color:var(--muted); margin-bottom:12px; }}
aside ul {{ list-style:none; margin:0; padding:0; }}
aside li {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; padding:3px 0; border-bottom:1px dashed var(--border); display:flex; align-items:center; gap:7px; }}
aside li .d {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
aside .k {{ font-size:11px; margin-left:auto; opacity:.75; }}
.empty {{ color:var(--muted); font-size:12.5px; }}
.tbl {{ font-size:13px; font-weight:700; fill:#fff; }}
.fld {{ font-size:11px; fill:var(--fg); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
.key {{ font-size:10px; }}
.ft {{ font-size:14px; font-weight:700; fill:#fff; }}
.fts {{ font-size:11px; fill:#fff; opacity:.92; }}
.edge {{ stroke:var(--edge); stroke-width:1.5; fill:none; transition:stroke .12s, stroke-width .12s, opacity .12s; }}
.elab {{ font-size:10px; fill:var(--muted); font-weight:600; }}
.zone {{ fill:none; stroke:var(--edge); stroke-width:1.2; stroke-dasharray:6 5; opacity:.85; }}
.zone-t {{ font-size:12px; font-weight:650; fill:var(--fg); }}
.dom {{ font-size:12px; fill:var(--fg); font-family:ui-monospace,Menlo,monospace; }}
g.tabela, g.fonte {{ cursor:pointer; }}
g.tabela .node, g.fonte .node {{ transition:opacity .12s, filter .12s; }}
/* estados */
body.zoom-in #wrap svg {{ transform:scale(1.35); }}
body.zoom-out #wrap svg {{ transform:scale(.72); }}
g.dim .node, g.dim .fld, g.dim .tbl, g.dim .zone-t, g.dim .dom {{ opacity:.22; }}
g.dim .dot {{ opacity:.15; }}
.edge.dim {{ opacity:.15; }}
.edge.hl {{ stroke:var(--hl); stroke-width:2.6; }}
g.hlbox .node {{ stroke-width:3; filter:drop-shadow(0 0 6px rgba(245,158,11,.45)); }}
</style>
</head>
<body>
<header>
  <div>
    <h1>🧭 Fluxo e interligação dos dados — PNCP → PostgreSQL</h1>
    <div class="sub">Passe o mouse numa tabela para ver as conexões · clique para detalhar no painel · 🔑 chave primária · ⇢ chave estrangeira</div>
  </div>
  <div class="legenda">
    <span><i style="background:#3b82f6"></i>Search</span>
    <span><i style="background:#10b981"></i>Consulta</span>
    <span><i style="background:#f59e0b"></i>Itens/Arquivos</span>
    <span><i style="background:#8b5cf6"></i>Domínios</span>
    <span><i style="background:#ec4899"></i>Dados Abertos</span>
    <span><i style="background:#94a3b8"></i>Processado</span>
  </div>
  <div class="controles">
    <button onclick="zoom(1.25)">+</button>
    <button onclick="zoom(0.8)">−</button>
    <button onclick="zoom(1,true)">100%</button>
  </div>
</header>
<main>
  <div id="wrap">{svg_html}</div>
  <aside id="painel">
    <h2>Detalhes</h2>
    <div class="desc">Clique numa tabela do diagrama para ver todos os campos.</div>
    <ul id="campos"></ul>
  </aside>
</main>
<script>
const TABELAS = {json_tabelas};
const SETAS = {json_setas};
const FONTES = {json_fontes};

const svg = document.getElementById('svg');
const painelCampos = document.getElementById('campos');
const painelDesc = document.querySelector('#painel .desc');
const painelTitulo = document.querySelector('#painel h2');

function camposHtml(nome) {{
  const t = TABELAS[nome];
  if (!t) return '';
  return t.campos.map(([c, f, fl]) => {{
    const cor = (FONTES[f] || ['#888'])[0];
    const suf = fl === 'pk' ? '<span class="k">🔑 PK</span>' : (fl === 'fk' ? '<span class="k">⇢ FK</span>' : '');
    return `<li><span class="d" style="background:${{cor}}"></span>${{c}}${{suf}}</li>`;
  }}).join('');
}}

function mostrar(nome) {{
  const t = TABELAS[nome];
  painelTitulo.textContent = nome;
  painelDesc.textContent = t ? t.desc : '';
  painelCampos.innerHTML = t ? camposHtml(nome) : '<li class="empty">—</li>';
}}

function limpar() {{
  document.querySelectorAll('g.tabela,g.fonte').forEach(g => g.classList.remove('dim','hlbox'));
  document.querySelectorAll('.edge').forEach(e => e.classList.remove('dim','hl'));
}}
function destacar(nome) {{
  limpar();
  // setas que tocam a tabela
  const tocam = SETAS.filter(([,de,para]) => de === nome || para === nome).map(s => 'seta-' + s[0]);
  document.querySelectorAll('.edge').forEach(e => {{
    if (tocam.includes(e.id)) e.classList.add('hl'); else e.classList.add('dim');
  }});
  // tabelas ligadas
  const ligadas = new Set();
  SETAS.forEach(([,de,para]) => {{ if (de === nome) ligadas.add(para); if (para === nome) ligadas.add(de); }});
  document.querySelectorAll('g.tabela,g.fonte').forEach(g => {{
    const n = g.dataset.nome;
    if (n === nome) {{ g.classList.add('hlbox'); }}
    else if (ligadas.has(n)) {{ /* mantém visível */ }}
    else g.classList.add('dim');
  }});
}}

document.querySelectorAll('g.tabela,g.fonte').forEach(g => {{
  g.addEventListener('mouseenter', () => destacar(g.dataset.nome));
  g.addEventListener('mouseleave', limpar);
  g.addEventListener('click', () => mostrar(g.dataset.nome));
}});

let escala = 1;
function zoom(fator, reset) {{
  escala = reset ? 1 : Math.min(2.4, Math.max(0.5, escala * fator));
  const w = document.getElementById('wrap');
  w.scrollTo((w.scrollWidth - w.clientWidth) / 2, (w.scrollHeight - w.clientHeight) / 2);
  svg.style.transform = 'scale(' + escala + ')';
}}

mostrar('licitacao');
</script>
</body>
</html>"""

with open("/home/node/.openclaw/workspace/licitacoes/schema/diagrama_fluxo_dados.html", "w", encoding="utf-8") as f:
    f.write(html)
print("HTML interativo gerado:", len(html), "bytes")
