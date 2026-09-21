"""Carrega as regras dos convênios e responde consultas sobre elas.

Duas fontes, as duas na pasta dados/:
- regras_convenio.json: o arquivo que a Carla mandou, sem alteração.
- regras_extras.json: as frases de observação dos convênios transformadas em regra.
"""

import json
import os

from .normalizar import sem_acento

PASTA_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")


def carregar_regras(pasta=PASTA_DADOS):
    with open(os.path.join(pasta, "regras_convenio.json"), encoding="utf-8") as arquivo:
        oficiais = json.load(arquivo)
    with open(os.path.join(pasta, "regras_extras.json"), encoding="utf-8") as arquivo:
        extras = json.load(arquivo)

    return {
        "versao": oficiais.get("versao", ""),
        "procedimentos": {p["codigo"]: p for p in oficiais["procedimentos"]},
        # a chave é o nome sem acento e minúsculo, para achar 'saude interior' também
        "convenios": {sem_acento(c["nome"]): c for c in oficiais["convenios"]},
        "extras_convenio": {sem_acento(nome): regra for nome, regra in extras["convenios"].items()},
        "registro_por_procedimento": extras["registro_por_procedimento"],
        "dias_de_alerta_prazo": extras.get("dias_de_alerta_para_prazo_de_envio", 5),
    }


def achar_convenio(regras, nome):
    return regras["convenios"].get(sem_acento(nome))


def achar_procedimento(regras, codigo_ou_nome):
    """Procura pelo código (50000470) e, se não achar, por um pedaço da descrição ('neurofuncional')."""
    procurado = str(codigo_ou_nome or "").strip()
    if procurado in regras["procedimentos"]:
        return regras["procedimentos"][procurado]
    alvo = sem_acento(procurado)
    if not alvo:
        return None
    achados = [p for p in regras["procedimentos"].values()
               if alvo in sem_acento(p["descricao"]) or sem_acento(p["descricao"]) in alvo]
    if len(achados) == 1:
        return achados[0]
    # palavra marcante: 'neurofuncional' só existe em um procedimento, 'fisioterapia' em dois
    for palavra in alvo.replace(",", " ").split():
        if len(palavra) < 7:
            continue
        com_a_palavra = [p for p in regras["procedimentos"].values() if palavra in sem_acento(p["descricao"])]
        if len(com_a_palavra) == 1:
            return com_a_palavra[0]
    return None


def consultar_regra(regras, convenio, procedimento):
    """O que este convênio exige e cobre para este procedimento. É a primeira ferramenta do MCP."""
    regra = achar_convenio(regras, convenio)
    if regra is None:
        return {
            "encontrado": False,
            "motivo": "Convênio '%s' não está nas regras." % convenio,
            "convenios_conhecidos": [c["nome"] for c in regras["convenios"].values()],
        }

    proc = achar_procedimento(regras, procedimento)
    if proc is None:
        return {
            "encontrado": False,
            "convenio": regra["nome"],
            "motivo": "Procedimento '%s' não está na tabela de procedimentos." % procedimento,
            "procedimentos_conhecidos": [
                "%s %s" % (p["codigo"], p["descricao"]) for p in regras["procedimentos"].values()],
        }

    coberto = proc["codigo"] in regra["procedimentos_cobertos"]
    extra = regras["extras_convenio"].get(sem_acento(regra["nome"]), {})
    return {
        "encontrado": True,
        "convenio": regra["nome"],
        "procedimento": "%s %s" % (proc["codigo"], proc["descricao"]),
        "coberto": coberto,
        "se_nao_coberto": (
            "Faturar como particular." if proc["codigo"] in extra.get("nao_coberto_vira_particular", [])
            else "Não enviar a este convênio.") if not coberto else "",
        "valor_referencia": proc["valor_referencia"],
        "registro_exigido": regras["registro_por_procedimento"].get(proc["codigo"], ""),
        "campos_obrigatorios": regra["campos_obrigatorios"],
        "limite_sessoes_por_autorizacao": regra["limite_sessoes_por_autorizacao"],
        "prazo_envio_dias": regra["prazo_envio_dias"],
        "validade_maxima_autorizacao_dias": regra["validade_maxima_autorizacao_dias"],
        "autorizacao_verbal_dias_uteis": extra.get("autorizacao_verbal_dias_uteis", 0),
        "observacao_do_convenio": regra.get("observacao", ""),
        "versao_das_regras": regras["versao"],
    }
