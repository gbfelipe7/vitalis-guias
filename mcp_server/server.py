"""MCP da Clínica Vitalis: regras dos convênios e conferência de guias.

Quatro ferramentas, todas em cima do mesmo motor que a página usa (pasta motor/):
  consultar_regra      o que um convênio exige e cobre para um procedimento
  verificar_guia       confere uma guia (do lote ou nova) e devolve decisão, motivo e o que corrigir
  listar_pendentes     as guias do lote que não podem ser enviadas ainda
  relatorio_de_terca   o resumo que o Dr. Renato vê toda terça

Os dados vêm de dados/regras_convenio.json e dados/guias.csv, lidos direto do disco.
Rodar:  python mcp_server/server.py   (fala MCP por stdin e stdout)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:                                   # SDK 2.x: a classe se chama MCPServer
    from mcp.server.mcpserver import MCPServer as ServidorMCP
except ImportError:                    # SDK 1.x: a mesma classe se chamava FastMCP
    from mcp.server.fastmcp import FastMCP as ServidorMCP

from motor import (carregar_guias, carregar_regras, montar_relatorio, relatorio_em_texto,
                   verificar_lote, verificar_nova)
from motor import consultar_regra as consultar_regra_no_motor
from motor.normalizar import sem_acento

mcp = ServidorMCP("vitalis-guias")

REGRAS = carregar_regras()
GUIAS = carregar_guias()
# O lote é conferido uma vez, quando o servidor sobe. As ferramentas só consultam.
LOTE_CONFERIDO = {r["id_guia"].upper(): r for r in verificar_lote(GUIAS, REGRAS)}


def _enxuto(resultado):
    """O que interessa para quem está conversando: decisão, motivo e o que corrigir."""
    return {
        "id_guia": resultado["id_guia"],
        "decisao": resultado["decisao"],
        "gravidade": resultado["gravidade"],
        "nome_da_decisao": resultado["nome_da_decisao"],
        "o_que_significa": resultado["o_que_significa"],
        "proximo_passo": resultado["proximo_passo_nome"],
        "pendencias": [{"motivo": p["motivo"], "corrigir": p["corrigir"], "gravidade": p["gravidade"]}
                       for p in resultado["pendencias"]],
        "alertas": resultado["alertas"],
        "valor_em_risco": resultado["valor_em_risco"],
        "enviar_ate": resultado["enviar_ate"],
        "conferida_em": resultado["conferida_em"],
    }


@mcp.tool()
def consultar_regra(convenio: str, procedimento: str) -> dict:
    """Consulta a regra de um convênio para um procedimento: se cobre, valor de referência,
    campos obrigatórios, limite de sessões por autorização e prazo de envio.

    convenio: Vitalcard, Saúde Interior ou Plano Bem (acento e maiúscula não importam).
    procedimento: o código (ex.: 50000470) ou um pedaço do nome (ex.: neurofuncional, consulta).
    """
    return consultar_regra_no_motor(REGRAS, convenio, procedimento)


@mcp.tool()
def verificar_guia(
    id_guia: str = "",
    convenio: str = "",
    procedimento_codigo: str = "",
    procedimento_descricao: str = "",
    data_atendimento: str = "",
    numero_autorizacao: str = "",
    autorizacao_validade: str = "",
    sessao_numero_na_autorizacao: str = "",
    autorizacao_sessoes_limite: str = "",
    carteirinha: str = "",
    cid: str = "",
    profissional: str = "",
    profissional_registro: str = "",
    valor: str = "",
    paciente: str = "",
    unidade: str = "",
    observacao_recepcao: str = "",
    data_lancamento: str = "",
) -> dict:
    """Verifica uma guia e devolve a decisão (OK ou PENDENTE), o motivo e o que corrigir.

    Dois jeitos de usar:
    1. Guia que já está no lote de agosto: passe só o id_guia (ex.: G-2608-0041). O lote é conferido na
       data de lançamento de cada guia (campo conferida_em), como se ela ainda não tivesse sido enviada.
    2. Guia nova: passe os campos que tiver. Ela é conferida com a data de hoje. Datas podem vir como 03/09/2026 ou 2026-09-03,
       valor como 62,00 ou 62.00. Copie a observação da recepção como ela escreveu, em
       observacao_recepcao: ela pode mudar a decisão.

    Campo que não estiver no texto fica vazio. Não invente valor para preencher.
    """
    id_guia = id_guia.strip()
    campos = {
        "convenio": convenio, "procedimento_codigo": procedimento_codigo,
        "procedimento_descricao": procedimento_descricao, "data_atendimento": data_atendimento,
        "numero_autorizacao": numero_autorizacao, "autorizacao_validade": autorizacao_validade,
        "sessao_numero_na_autorizacao": sessao_numero_na_autorizacao,
        "autorizacao_sessoes_limite": autorizacao_sessoes_limite, "carteirinha": carteirinha, "cid": cid,
        "profissional": profissional, "profissional_registro": profissional_registro, "valor": valor,
        "paciente": paciente, "unidade": unidade, "observacao_recepcao": observacao_recepcao,
        "data_lancamento": data_lancamento,
    }
    campos = {nome: texto for nome, texto in campos.items() if str(texto).strip()}

    if id_guia and not campos:                       # só o número: é uma guia do lote de agosto
        do_lote = LOTE_CONFERIDO.get(id_guia.upper())
        if do_lote is None:
            return {"encontrada": False, "motivo": "A guia %s não está no lote de agosto." % id_guia}
        return _enxuto(do_lote)

    base = next((g for g in GUIAS if (g.get("id_guia") or "").strip().upper() == (id_guia or "").strip().upper()), None)
    if base is not None:                             # número do lote com campos: os campos passados corrigem a guia do lote
        campos = {**{k: v for k, v in base.items() if v not in (None, "")}, **campos}
    campos["id_guia"] = id_guia
    return _enxuto(verificar_nova(campos, GUIAS, REGRAS, usar_ia=False))


@mcp.tool()
def listar_pendentes(convenio: str = "", unidade: str = "") -> dict:
    """Lista as guias do lote de agosto que estão PENDENTES, com o motivo principal.
    Filtros opcionais: convenio (Vitalcard, Saúde Interior, Plano Bem) e unidade (Centro, Norte, Sul).
    Acento e maiúscula não importam. Filtro que não existe devolve erro, não lista vazia."""
    convenios = sorted({r["guia"]["convenio"] for r in LOTE_CONFERIDO.values()})
    unidades = sorted({r["guia"]["unidade"] for r in LOTE_CONFERIDO.values()})
    if convenio and not any(sem_acento(convenio) == sem_acento(c) for c in convenios):
        return {"erro": "Convênio '%s' não existe no lote." % convenio, "convenios": convenios}
    if unidade and not any(sem_acento(unidade) == sem_acento(u) for u in unidades):
        return {"erro": "Unidade '%s' não existe no lote." % unidade, "unidades": unidades}

    pendentes = [{"id_guia": r["id_guia"], "unidade": r["guia"]["unidade"], "convenio": r["guia"]["convenio"],
                  "valor": r["valor"], "gravidade": r["gravidade"], "motivo": r["pendencias"][0]["motivo"],
                  "corrigir": r["pendencias"][0]["corrigir"]}
                 for r in LOTE_CONFERIDO.values()
                 if r["decisao"] == "PENDENTE"
                 and (not convenio or sem_acento(convenio) == sem_acento(r["guia"]["convenio"]))
                 and (not unidade or sem_acento(unidade) == sem_acento(r["guia"]["unidade"]))]
    return {"total": len(pendentes), "em_risco": round(sum(p["valor"] for p in pendentes), 2), "guias": pendentes}


@mcp.tool()
def relatorio_de_terca(semana: str = "") -> str:
    """O relatório de terça do Dr. Renato: guias verificadas, com problema, por tipo e dinheiro em risco.
    Sem 'semana', o lote inteiro. Com uma data (2026-08-24) ou 'ultima', só as guias lançadas de segunda
    a domingo daquela semana, que é o que a reunião de terça olha."""
    if not semana:
        return relatorio_em_texto(montar_relatorio(list(LOTE_CONFERIDO.values())))
    from web.rotas import rota_relatorio
    codigo, dados = rota_relatorio(semana=semana)
    return dados["texto"] if codigo == 200 else dados["erro"]


if __name__ == "__main__":
    mcp.run()
