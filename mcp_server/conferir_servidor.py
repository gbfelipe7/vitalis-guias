"""Sobe o servidor MCP de verdade, por stdin e stdout, e chama as ferramentas como um cliente faria.

Rodar:  .venv/bin/python mcp_server/conferir_servidor.py
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def texto_da_resposta(resposta):
    return "\n".join(c.text for c in resposta.content if hasattr(c, "text"))


async def main():
    servidor = StdioServerParameters(command=sys.executable, args=[os.path.join(RAIZ, "mcp_server", "server.py")])
    async with stdio_client(servidor) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()
            ferramentas = await sessao.list_tools()
            print("ferramentas:", [f.name for f in ferramentas.tools])

            regra = await sessao.call_tool("consultar_regra", {"convenio": "plano bem", "procedimento": "consulta"})
            print("\nconsultar_regra(plano bem, consulta):\n", texto_da_resposta(regra)[:420])

            do_lote = await sessao.call_tool("verificar_guia", {"id_guia": "G-2608-0041"})
            print("\nverificar_guia(G-2608-0041):\n", texto_da_resposta(do_lote)[:520])

            nova = await sessao.call_tool("verificar_guia", {
                "convenio": "Vitalcard", "procedimento_descricao": "fisio neurofuncional",
                "data_atendimento": "10/09/2026", "numero_autorizacao": "AUT700800",
                "autorizacao_validade": "25/09/2026", "sessao_numero_na_autorizacao": "11",
                "carteirinha": "123456789", "cid": "G81.9", "profissional_registro": "CREFITO-3 198302-F",
                "valor": "70,00", "data_lancamento": "11/09/2026"})
            print("\nverificar_guia(guia nova, sessão 11):\n", texto_da_resposta(nova)[:520])

            pendentes = await sessao.call_tool("listar_pendentes", {"unidade": "Sul"})
            print("\nlistar_pendentes(Sul): %d caracteres de resposta" % len(texto_da_resposta(pendentes)))

            relatorio = await sessao.call_tool("relatorio_de_terca", {})
            print("\nrelatorio_de_terca:\n", texto_da_resposta(relatorio)[:300])


asyncio.run(main())
