#!/usr/bin/env python3
"""
CONFRONTO schema × dados reais PNCP.
Lê amostra/ + confronto/ e compara cada campo de cada nível contra o mapeamento
conhecido (schema_licitacoes.sql). Gera relatório de compatibilidade + ALTERs.
"""
import collections
import glob
import json
import os

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "licitacoes"))

# mapeamento conhecido: campo API -> "tabela.coluna" (ou "IGNORAR")
SEARCH = {
    "id": "CONTROLE", "index": "IGNORAR", "doc_type": "IGNORAR",
    "title": "licitacao.titulo", "description": "licitacao.objeto",
    "item_url": "licitacao.url_pncp", "document_type": "licitacao.document_type",
    "createdAt": "CONTROLE", "numero": "IGNORAR",
    "ano": "licitacao.ano", "numero_sequencial": "licitacao.sequencial",
    "numero_sequencial_compra_ata": "ata.sequencial_compra_ata",
    "numero_controle_pncp": "licitacao.numero_controle_pncp",
    "orgao_id": "orgao.id_pncp", "orgao_cnpj": "orgao.cnpj",
    "orgao_nome": "orgao.razao_social",
    "orgao_subrogado_id": "licitacao.orgao_subrogado_id",
    "orgao_subrogado_nome": "licitacao.orgao_subrogado_nome",
    "unidade_id": "unidade_orgao.id_pncp", "unidade_codigo": "unidade_orgao.codigo",
    "unidade_nome": "unidade_orgao.nome",
    "esfera_id": "orgao.esfera", "esfera_nome": "IGNORAR(deriva esfera_id)",
    "poder_id": "orgao.poder", "poder_nome": "IGNORAR(deriva poder_id)",
    "municipio_id": "licitacao.municipio_id", "municipio_nome": "licitacao.municipio",
    "uf": "licitacao.uf",
    "modalidade_licitacao_id": "licitacao.modalidade_id",
    "modalidade_licitacao_nome": "IGNORAR(deriva id)",
    "situacao_id": "licitacao.situacao_id", "situacao_nome": "IGNORAR(deriva id)",
    "data_publicacao_pncp": "licitacao.data_publicacao",
    "data_atualizacao_pncp": "licitacao.data_atualizacao",
    "data_assinatura": "licitacao.data_assinatura",
    "data_inicio_vigencia": "licitacao.data_inicio_vigencia",
    "data_fim_vigencia": "licitacao.data_encerramento_proposta",
    "cancelado": "licitacao.cancelado", "valor_global": "licitacao.valor_estimado",
    "tem_resultado": "licitacao.tem_resultado",
    "tipo_id": "licitacao.tipo_instrumento_id", "tipo_nome": "IGNORAR(deriva id)",
    "tipo_contrato_id": "contrato.tipo_contrato_id",
    "tipo_contrato_nome": "IGNORAR(deriva id)",
    "fonte_orcamentaria": "licitacao.fonte_orcamentaria",
    "fonte_orcamentaria_id": "licitacao.fonte_orcamentaria_id",
    "fonte_orcamentaria_nome": "IGNORAR(deriva id)",
    "exigencia_conteudo_nacional": "licitacao.exige_conteudo_nacional",
    "permite_adesao": "ata.permite_adesao",
    "possui_emenda_parlamentar": "licitacao.emenda_parlamentar",
    "tipo_margem_preferencia": "licitacao.tipo_margem",
    "tipo_margem_preferencia_id": "licitacao.tipo_margem_id",
    "tipo_margem_preferencia_nome": "IGNORAR(deriva id)",
}

COMPRA = {
    "valorTotalEstimado": "licitacao.valor_estimado",
    "valorTotalHomologado": "licitacao.valor_homologado",
    "orcamentoSigilosoCodigo": "licitacao.orcamento_sigiloso",
    "orcamentoSigilosoDescricao": "IGNORAR(deriva codigo)",
    "numeroControlePNCP": "licitacao.numero_controle_pncp",
    "linkSistemaOrigem": "licitacao.link_sistema_origem",
    "linkProcessoEletronico": "licitacao.link_processo_eletronico",
    "anoCompra": "licitacao.ano", "sequencialCompra": "licitacao.sequencial",
    "numeroCompra": "licitacao.numero_compra", "processo": "licitacao.processo",
    "orgaoEntidade": "orgao(cnpj,razao,esfera,poder)",
    "unidadeOrgao": "unidade_orgao(codigo,nome,uf,municipio)",
    "orgaoSubRogado": "licitacao.orgao_subrogado_json",
    "unidadeSubRogada": "licitacao.unidade_subrogada_json",
    "modalidadeId": "licitacao.modalidade_id", "modalidadeNome": "IGNORAR(deriva id)",
    "justificativaPresencial": "licitacao.justificativa_presencial",
    "modoDisputaId": "licitacao.modo_disputa_id", "modoDisputaNome": "IGNORAR(deriva id)",
    "tipoInstrumentoConvocatorioCodigo": "licitacao.tipo_instrumento_id",
    "tipoInstrumentoConvocatorioNome": "IGNORAR(deriva id)",
    "amparoLegal": "licitacao.amparo_legal_id(+nome/descricao jsonb)",
    "objetoCompra": "licitacao.objeto",
    "informacaoComplementar": "licitacao.informacao_complementar",
    "srp": "licitacao.srp",
    "fontesOrcamentarias": "licitacao.fontes_orcamentarias_json",
    "emendaParlamentar": "licitacao.emenda_parlamentar",
    "dataPublicacaoPncp": "licitacao.data_publicacao",
    "dataAberturaProposta": "licitacao.data_abertura_proposta",
    "dataEncerramentoProposta": "licitacao.data_encerramento_proposta",
    "situacaoCompraId": "licitacao.situacao_id", "situacaoCompraNome": "IGNORAR(deriva id)",
    "existeResultado": "licitacao.tem_resultado",
    "dataInclusao": "licitacao.data_inclusao",
    "dataAtualizacao": "licitacao.data_atualizacao",
    "dataAtualizacaoGlobal": "licitacao.data_atualizacao_global",
    "usuarioNome": "CONTROLE",
}

ITEM = {
    "numeroItem": "licitacao_item.numero_item", "descricao": "licitacao_item.descricao",
    "materialOuServico": "licitacao_item.material_servico",
    "materialOuServicoNome": "IGNORAR(deriva id)",
    "valorUnitarioEstimado": "licitacao_item.valor_unitario_estimado",
    "valorTotal": "licitacao_item.valor_total", "quantidade": "licitacao_item.quantidade",
    "unidadeMedida": "licitacao_item.unidade_medida",
    "orcamentoSigiloso": "licitacao_item.orcamento_sigiloso",
    "itemCategoriaId": "licitacao_item.item_categoria_id",
    "itemCategoriaNome": "IGNORAR(deriva id)",
    "patrimonio": "licitacao_item.patrimonio",
    "codigoRegistroImobiliario": "licitacao_item.codigo_registro_imobiliario",
    "criterioJulgamentoId": "licitacao_item.criterio_julgamento_id",
    "criterioJulgamentoNome": "IGNORAR(deriva id)",
    "situacaoCompraItem": "licitacao_item.situacao_item_id",
    "situacaoCompraItemNome": "IGNORAR(deriva id)",
    "tipoBeneficio": "licitacao_item.tipo_beneficio_id",
    "tipoBeneficioNome": "IGNORAR(deriva id)",
    "incentivoProdutivoBasico": "licitacao_item.incentivo_produtivo_basico",
    "dataInclusao": "licitacao_item.data_inclusao",
    "dataAtualizacao": "licitacao_item.data_atualizacao",
    "temResultado": "licitacao_item.tem_resultado",
    "imagem": "licitacao_item.tem_imagem",
    "aplicabilidadeMargemPreferenciaNormal": "licitacao_item.margem_pref_normal",
    "aplicabilidadeMargemPreferenciaAdicional": "licitacao_item.margem_pref_adicional",
    "percentualMargemPreferenciaNormal": "licitacao_item.pct_margem_normal",
    "percentualMargemPreferenciaAdicional": "licitacao_item.pct_margem_adicional",
    "ncmNbsCodigo": "licitacao_item.ncm_nbs_codigo",
    "ncmNbsDescricao": "licitacao_item.ncm_nbs_descricao",
    "catalogo": "licitacao_item.catalogo",
    "categoriaItemCatalogo": "licitacao_item.categoria_catalogo",
    "catalogoCodigoItem": "licitacao_item.codigo_catalogo",
    "informacaoComplementar": "licitacao_item.informacao_complementar",
    "tipoMargemPreferencia": "licitacao_item.tipo_margem_id",
    "exigenciaConteudoNacional": "licitacao_item.exige_conteudo_nacional",
}

ARQUIVO = {
    "uri": "documento.url_fonte", "url": "documento.url_fonte",
    "cnpj": "documento.orgao_cnpj", "anoCompra": "documento.ano_compra",
    "sequencialCompra": "documento.sequencial_compra",
    "statusAtivo": "documento.ativo",
    "dataPublicacaoPncp": "documento.data_publicacao",
    "sequencialDocumento": "documento.sequencial", "titulo": "documento.titulo",
    "tipoDocumentoNome": "IGNORAR(deriva id)",
    "tipoDocumentoId": "documento.tipo_documento_id",
    "tipoDocumentoDescricao": "IGNORAR(deriva id)",
}

CONTRATO = {
    "dataPublicacaoPncp": "contrato.data_publicacao_pncp",
    "anoContrato": "contrato.ano", "tipoContrato": "contrato.tipo_contrato_id(+nome)",
    "numeroContratoEmpenho": "contrato.numero",
    "niFornecedor": "contrato.fornecedor_cnpj",
    "niFornecedorSubContratado": "contrato.fornecedor_subcontratado_cnpj",
    "orgaoEntidade": "orgao(cnpj,razao,esfera,poder)",
    "dataAssinatura": "contrato.data_assinatura",
    "dataVigenciaFim": "contrato.vigencia_fim",
    "tipoParteEnvolvida": "contrato.tipo_parte_envolvida_json",
    "orgaoParteEnvolvida": "contrato.orgao_parte_envolvida_json",
    "unidadeOrgaoParteEnvolvida": "contrato.unidade_parte_envolvida_json",
    "frutoAdesao": "contrato.fruto_adesao",
    "dataVigenciaInicio": "contrato.vigencia_inicio",
    "dataAtualizacao": "contrato.data_atualizacao",
    "tipoPessoa": "contrato.tipo_pessoa",
    "categoriaProcesso": "contrato.categoria_processo_id(+nome)",
    "nomeRazaoSocialFornecedor": "contrato.fornecedor_nome",
    "orgaoSubRogado": "contrato.orgao_subrogado_json",
    "unidadeOrgao": "unidade_orgao(codigo,nome,uf,municipio)",
    "unidadeSubRogada": "contrato.unidade_subrogada_json",
    "informacaoComplementar": "contrato.informacao_complementar",
    "sequencialContrato": "contrato.sequencial",
    "processo": "contrato.processo",
    "tipoPessoaSubContratada": "contrato.tipo_pessoa_subcontratada",
    "numeroRetificacao": "contrato.numero_retificacao",
    "nomeFornecedorSubContratado": "contrato.fornecedor_subcontratado_nome",
    "objetoContrato": "contrato.objeto",
    "valorInicial": "contrato.valor_inicial", "valorParcela": "contrato.valor_parcela",
    "valorGlobal": "contrato.valor_global", "valorAcumulado": "contrato.valor_acumulado",
    "dataAtualizacaoGlobal": "contrato.data_atualizacao_global",
    "identificadorCipi": "contrato.identificador_cipi", "urlCipi": "contrato.url_cipi",
    "numeroControlePNCP": "contrato.numero_controle_pncp",
    "receita": "contrato.receita", "numeroParcelas": "contrato.numero_parcelas",
    "temRemanejamento": "contrato.tem_remanejamento",
    "emendaParlamentar": "contrato.emenda_parlamentar",
    "usuarioNome": "CONTROLE", "codigoPaisFornecedor": "contrato.pais_fornecedor",
    "numeroControlePncpAta": "contrato.numero_controle_pncp_ata",
    "numeroControlePncpCompra": "contrato.licitacao_ref",
}

NIVEIS = {
    "SEARCH": SEARCH,
    "COMPRA": COMPRA,
    "ITEM": ITEM,
    "ARQUIVO": ARQUIVO,
    "CONTRATO": CONTRATO,
}


def campos_unicos(lista_objs):
    d = collections.OrderedDict()
    for obj in lista_objs:
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if k not in d:
                d[k] = {"tipos": set(), "n": 0, "ex": None, "null": 0}
            d[k]["n"] += 1
            d[k]["tipos"].add(type(v).__name__)
            if v is None:
                d[k]["null"] += 1
            elif d[k]["ex"] is None:
                d[k]["ex"] = v
    return d


def nivel_do_arquivo(path):
    """Retorna lista de (nivel, objeto) por arquivo."""
    res = []
    nome = os.path.basename(path)
    try:
        dados = json.load(open(path, encoding="utf-8"))
    except Exception:
        return res
    if isinstance(dados, dict):
        if "search_item" in dados and "detalhe" in dados:
            res.append(("SEARCH", dados["search_item"]))
            if dados.get("detalhe"):
                # distingue compra vs contrato pelos campos
                if "objetoCompra" in dados["detalhe"] or "anoCompra" in dados["detalhe"]:
                    res.append(("COMPRA", dados["detalhe"]))
                elif "objetoContrato" in dados["detalhe"]:
                    res.append(("CONTRATO", dados["detalhe"]))
            for it in dados.get("itens") or []:
                res.append(("ITEM", it))
            for a in dados.get("arquivos") or []:
                res.append(("ARQUIVO", a))
            for r in dados.get("resultados") or []:
                for res_interno in (r.get("resultados") if isinstance(r, dict) else []) or []:
                    res.append(("RESULTADO", res_interno))
            for a in dados.get("atas") or []:
                res.append(("ATA", a))
        elif "detalhe" in dados and "empenhos" in dados:
            res.append(("SEARCH", dados.get("search_item", {})))
            if dados.get("detalhe"):
                res.append(("CONTRATO", dados["detalhe"]))
            for e in dados.get("empenhos") or []:
                res.append(("EMPENHO", e))
        elif nome.startswith("pca_"):
            res.append(("PCA", dados))
        elif nome.startswith("consolidado_busca"):
            for it in dados:
                res.append(("SEARCH", it))
    elif isinstance(dados, list):
        if nome.startswith("pca_itens_"):
            for it in dados:
                res.append(("PCA_ITEM", it))
        elif nome.startswith("consolidado_busca"):
            for it in dados:
                res.append(("SEARCH", it))
        elif "items" in nome or nome.endswith("_busca.json") or "busca_" in nome:
            for it in dados:
                if isinstance(it, dict):
                    res.append(("SEARCH", it))
        elif "items" in dados:
            for it in dados.get("items") or []:
                res.append(("SEARCH", it))
    return res


def main():
    por_nivel = collections.defaultdict(list)
    for pasta in ["amostra", "confronto"]:
        base = os.path.join(RAIZ, pasta)
        for path in glob.glob(os.path.join(base, "**", "*.json"), recursive=True):
            for nivel, obj in nivel_do_arquivo(path):
                por_nivel[nivel].append(obj)

    rel = []
    rel.append("# 🔬 Relatório de Confronto — Schema × Dados Reais PNCP\n")
    rel.append(f"Gerado em 12/08/2026 · amostras: `amostra/` (698 buscas + 20 detalhes) e `confronto/` (buscas novas + detalhes com resultados/atas/empenhos/PCA)\n")

    for nivel, mapeamento in NIVEIS.items():
        objs = por_nivel.get(nivel, [])
        if not objs:
            rel.append(f"\n## {nivel} — sem dados\n")
            continue
        campos = campos_unicos(objs)
        novos = sorted(k for k in campos if k not in mapeamento)
        rel.append(f"\n## {nivel} — {len(objs)} objetos · {len(campos)} campos únicos · mapeados {len(campos)-len(novos)}")
        if novos:
            rel.append(f"\n### ⚠️ Campos NOVOS (sem mapeamento no schema)\n")
            for k in novos:
                c = campos[k]
                ex = str(c["ex"])[:80].replace("\n", " ")
                rel.append(f"- `{k}` ({', '.join(sorted(c['tipos']))}, n={c['n']}) ex: {ex}")
        else:
            rel.append("\n✅ Todos os campos já estão mapeados.\n")

    # níveis novos (descoberta)
    for nivel in ["RESULTADO", "ATA", "EMPENHO", "PCA", "PCA_ITEM"]:
        objs = por_nivel.get(nivel, [])
        if not objs:
            continue
        campos = campos_unicos(objs)
        rel.append(f"\n## {nivel} — {len(objs)} objetos · {len(campos)} campos únicos (NOVO nível — precisa de tabela)")
        for k, c in campos.items():
            ex = str(c["ex"])[:80].replace("\n", " ")
            rel.append(f"- `{k}` ({', '.join(sorted(c['tipos']))}, n={c['n']}) ex: {ex}")

    txt = "\n".join(rel)
    with open(os.path.join(RAIZ, "schema", "relatorio_confronto.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt[:6000])


if __name__ == "__main__":
    main()
