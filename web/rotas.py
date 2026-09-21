"""O que cada endereço da API faz, em funções simples que devolvem (status, corpo).

As funções da pasta api/ (Vercel) e o servidor_local.py chamam estas mesmas funções.
Assim o que roda na minha máquina é exatamente o que roda publicado.
"""

from motor import (carregar_guias, carregar_regras, consultar_regra, montar_relatorio,
                   relatorio_em_texto, verificar_lote, verificar_nova)
from motor.entrada import interpretar_texto

MAXIMO_DE_NOVAS = 50


def _so_texto(campos):
    return {str(k): str(v) for k, v in campos.items() if v is not None and str(v).strip()}


def rota_guias():
    """GET /api/guias: as 80 guias de agosto conferidas e o relatório do lote."""
    regras = carregar_regras()
    resultados = verificar_lote(carregar_guias(), regras)     # sem IA: o lote dá sempre o mesmo resultado
    return 200, {"versao_das_regras": regras["versao"],
                 "relatorio": montar_relatorio(resultados), "guias": resultados}


def rota_verificar(dados):
    """POST /api/verificar: confere uma guia nova. Aceita {"guia": {...}} ou {"texto": "..."}."""
    regras = carregar_regras()
    entrada = {"lido_por": "campos enviados", "faltando": []}

    if isinstance(dados.get("guia"), dict):
        campos = _so_texto(dados["guia"])
    elif str(dados.get("texto") or "").strip():
        entrada = interpretar_texto(dados["texto"], regras, usar_ia=True)
        campos = _so_texto(entrada["campos"])
    else:
        return 400, {"erro": "Mande 'guia' (os campos) ou 'texto' (o que a recepção escreveu)."}

    if not campos:
        return 422, {"erro": "Não consegui separar nenhum campo desse texto.",
                     "dica": "Escreva um campo por linha, como 'Convênio: Vitalcard'."}

    resultado = verificar_nova(campos, carregar_guias(), regras, usar_ia=True)
    return 200, {"entrada": {"lido_por": entrada["lido_por"], "campos": campos,
                             "faltando": entrada["faltando"]},
                 "resultado": resultado}


def rota_relatorio(novas=None):
    """GET ou POST /api/relatorio: o relatório de terça. 'novas' são guias conferidas na sessão."""
    novas = novas or []
    if not isinstance(novas, list):
        return 400, {"erro": "Mande 'novas' como uma lista de guias."}
    regras, guias = carregar_regras(), carregar_guias()
    resultados = verificar_lote(guias, regras)
    for i, nova in enumerate(novas[:MAXIMO_DE_NOVAS]):
        if isinstance(nova, dict):
            campos = _so_texto(nova)
            campos.setdefault("id_guia", "NOVA-%d" % (i + 1))
            resultados.append(verificar_nova(campos, guias, regras, usar_ia=False))
    relatorio = montar_relatorio(resultados)
    return 200, {"relatorio": relatorio, "texto": relatorio_em_texto(relatorio)}


def rota_regra(convenio, procedimento):
    """GET /api/regra?convenio=...&procedimento=..."""
    if not convenio or not procedimento:
        return 400, {"erro": "Informe convenio e procedimento na URL."}
    return 200, consultar_regra(carregar_regras(), convenio, procedimento)
