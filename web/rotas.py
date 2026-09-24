"""O que cada endereço da API faz, em funções simples que devolvem (status, corpo).

As funções da pasta api/ (Vercel) e o servidor_local.py chamam estas mesmas funções.
Assim o que roda na minha máquina é exatamente o que roda publicado.
"""

from datetime import timedelta

from motor import (carregar_guias, carregar_regras, consultar_regra, montar_relatorio,
                   relatorio_em_texto, verificar_lote, verificar_nova)
from motor.entrada import interpretar_texto
from motor.normalizar import CAMPOS, ler_data, limpar_texto, sem_acento

MAXIMO_DE_NOVAS = 50


def _so_texto(campos):
    """Só chave conhecida e só valor simples. Lista, objeto aninhado e chave estranha ficam de fora."""
    return {c: limpar_texto(campos[c], 1000 if c == "observacao_recepcao" else 200)
            for c in CAMPOS if isinstance(campos.get(c), (str, int, float)) and not isinstance(campos.get(c), bool)
            and limpar_texto(campos[c])}


def _datas_em_iso(campos):
    """As datas que o motor entende voltam em AAAA-MM-DD, para o formulário conseguir mostrar.
    Data que ele não entende volta como veio, e a pessoa corrige no formulário."""
    campos = dict(campos)
    atendimento = ler_data(campos.get("data_atendimento", ""))
    for chave, depois_de in (("data_atendimento", None), ("autorizacao_validade", atendimento)):
        if campos.get(chave):
            lida = ler_data(campos[chave], depois_de=depois_de)
            if lida:
                campos[chave] = lida.isoformat()
    return campos


def _regras_para_o_formulario(regras):
    """O que o formulário de guia nova precisa saber para ajudar quem preenche: os convênios,
    os campos que cada um exige e os procedimentos, com os que cada convênio cobre."""
    return {
        "procedimentos": [{"codigo": p["codigo"], "descricao": p["descricao"], "valor": p["valor_referencia"]}
                          for p in regras["procedimentos"].values()],
        "convenios": [{"nome": c["nome"], "campos_obrigatorios": c["campos_obrigatorios"],
                       "cobertos": c["procedimentos_cobertos"],
                       "limite_sessoes": c["limite_sessoes_por_autorizacao"],
                       "prazo_envio_dias": c["prazo_envio_dias"],
                       "validade_maxima_dias": c["validade_maxima_autorizacao_dias"],
                       "observacao": c.get("observacao", ""),
                       "extra": regras["extras_convenio"].get(sem_acento(c["nome"]), {})}
                      for c in regras["convenios"].values()],
        "registro_por_procedimento": {k: v for k, v in regras["registro_por_procedimento"].items() if not k.startswith("_")},
        "dias_de_alerta_prazo": regras["dias_de_alerta_prazo"],
    }


def _referencia_do_lote(campos, lote_por_id):
    """Guia de agosto corrigida continua conferida no dia em que foi lançada, como o resto do lote
    (orientação do recrutador). Guia que não é do lote é conferida hoje."""
    original = lote_por_id.get((campos.get("id_guia") or "").strip().upper())
    return ler_data(original.get("data_lancamento", "")) if original else None


def rota_guias():
    """GET /api/guias: as 80 guias de agosto conferidas, o relatório do lote e as regras."""
    regras = carregar_regras()
    resultados = verificar_lote(carregar_guias(), regras)     # sem IA: o lote dá sempre o mesmo resultado
    return 200, {"versao_das_regras": regras["versao"], "regras": _regras_para_o_formulario(regras),
                 "relatorio": montar_relatorio(resultados), "guias": resultados}


def rota_verificar(dados):
    """POST /api/verificar: confere uma guia nova. Aceita {"guia": {...}} ou {"texto": "..."}.

    Com "rascunho": true a conferência roda sem IA. É o que o formulário usa enquanto a pessoa
    preenche: rápido, sem gastar a cota do modelo. O botão Conferir manda sem rascunho.

    Com "so_ler": true o texto só é lido e os campos voltam para a pessoa conferir, sem conferência.
    "anteriores" são as guias já lançadas nesta sessão: a nova também é comparada com elas, para
    a mesma guia lançada duas vezes não sair como Pode enviar nas duas."""
    regras = carregar_regras()
    usar_ia = dados.get("rascunho") is not True
    so_ler = dados.get("so_ler") is True
    entrada = {"lido_por": "campos enviados", "faltando": [], "avisos": []}

    if isinstance(dados.get("guia"), dict):
        campos = _so_texto(dados["guia"])
    elif isinstance(dados.get("texto"), str) and dados["texto"].strip():
        entrada = interpretar_texto(dados["texto"], regras, usar_ia=usar_ia)
        campos = _so_texto(entrada["campos"])
        if (entrada["precisa_confirmar"] or so_ler) and campos:
            # Texto corrido é leitura, não é dado: devolve os campos lidos para a pessoa conferir.
            # A conferência de verdade acontece quando eles voltarem em "guia".
            return 200, {"confirmar": True, "entrada": {"lido_por": entrada["lido_por"], "campos": _datas_em_iso(campos),
                                                        "faltando": entrada["faltando"], "avisos": entrada["avisos"]}}
    else:
        return 400, {"erro": "Mande 'guia' (os campos) ou 'texto' (o que a recepção escreveu)."}

    if not campos and isinstance(dados.get("guia"), dict):
        return 422, {"erro": "A guia veio sem nenhum campo."}
    if not campos:
        return 422, {"erro": "Não consegui separar nenhum campo desse texto.",
                     "dica": "Escreva um campo por linha, como 'Convênio: Vitalcard'."}

    anteriores = dados.get("anteriores") if isinstance(dados.get("anteriores"), list) else []
    anteriores = [_so_texto(g) for g in anteriores[:MAXIMO_DE_NOVAS] if isinstance(g, dict)]
    lote = carregar_guias()
    lote_por_id = {(g.get("id_guia") or "").strip().upper(): g for g in lote}
    resultado = verificar_nova(campos, lote + anteriores, regras, usar_ia=usar_ia,
                               referencia=_referencia_do_lote(campos, lote_por_id))
    resultado["alertas"] = entrada.get("avisos", []) + resultado["alertas"]
    return 200, {"entrada": {"lido_por": entrada["lido_por"], "campos": campos,
                             "faltando": entrada["faltando"], "avisos": entrada.get("avisos", [])},
                 "resultado": resultado}


def _segunda_da_semana(valor):
    """A segunda-feira da semana de uma data, ou None se a data não fizer sentido."""
    dia = ler_data(valor)
    return dia - timedelta(days=dia.weekday()) if dia else None


def rota_relatorio(novas=None, semana=None):
    """GET ou POST /api/relatorio: o relatório de terça. 'novas' são guias conferidas na sessão.
    'semana' é uma data da semana a mostrar: o relatório pega as guias lançadas de segunda a domingo dessa semana.
    'ultima' é a última semana completa do lote, a que o Dr. Renato veria na terça seguinte."""
    novas = novas or []
    if not isinstance(novas, list):
        return 400, {"erro": "Mande 'novas' como uma lista de guias."}
    regras, guias = carregar_regras(), carregar_guias()
    inicio = None
    if semana and str(semana).strip().lower() == "ultima":
        ultimo = max(d for d in (ler_data(g.get("data_lancamento")) for g in guias) if d)
        inicio = ultimo - timedelta(days=(ultimo.weekday() + 1) % 7) - timedelta(days=6)   # o domingo mais recente, menos 6 dias
    elif semana:
        inicio = _segunda_da_semana(semana)
        if not inicio:
            return 400, {"erro": "Mande 'semana' como uma data, por exemplo 2026-08-24, ou 'ultima'."}
    resultados = verificar_lote(guias, regras)
    for r in resultados:
        r["origem"] = "lote"
    lote_por_id = {(g.get("id_guia") or "").strip().upper(): g for g in guias}
    ja_vistas = list(guias)                  # cada guia nova é comparada com o lote e com as novas anteriores
    for i, nova in enumerate(novas[:MAXIMO_DE_NOVAS]):
        if isinstance(nova, dict):
            campos = _so_texto(nova)
            campos.setdefault("id_guia", "NOVA-%d" % (i + 1))
            conferida = verificar_nova(campos, ja_vistas, regras, usar_ia=False,
                                       referencia=_referencia_do_lote(campos, lote_por_id))
            conferida["origem"] = "corrigida" if conferida["id_guia"].upper() in lote_por_id else "nova"
            # guia corrigida e conferida de novo (mesmo número) entra no lugar da antiga, não conta duas vezes
            resultados = [r for r in resultados if r["id_guia"].upper() != conferida["id_guia"].upper()] + [conferida]
            ja_vistas = [g for g in ja_vistas if (g.get("id_guia") or "").strip().upper() != conferida["id_guia"].upper()] + [campos]
    # as semanas que têm guia, para a página montar a escolha; a conferência acima usou o lote inteiro
    semanas = sorted({s.isoformat() for s in (_segunda_da_semana(r["guia"].get("data_lancamento")) for r in resultados) if s})
    do_periodo = resultados
    if inicio:
        fim = inicio + timedelta(days=6)
        do_periodo = [r for r in resultados if (ler_data(r["guia"].get("data_lancamento")) or inicio - timedelta(days=1)) >= inicio
                      and ler_data(r["guia"].get("data_lancamento")) <= fim]
    relatorio = montar_relatorio(do_periodo)
    if inicio:
        relatorio["semana"] = [inicio.isoformat(), fim.isoformat()]
    return 200, {"relatorio": relatorio, "texto": relatorio_em_texto(relatorio), "guias": resultados, "semanas": semanas}


def rota_regra(convenio, procedimento):
    """GET /api/regra?convenio=...&procedimento=..."""
    if not convenio or not procedimento:
        return 400, {"erro": "Informe convenio e procedimento na URL."}
    return 200, consultar_regra(carregar_regras(), convenio, procedimento)
