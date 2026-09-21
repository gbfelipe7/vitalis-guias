"""Deixa a guia num formato só, venha ela do CSV, do formulário ou do MCP.

A recepção digita data como 03/08/2026, valor como 62,00 e às vezes deixa espaço
sobrando. Aqui tudo isso vira um dicionário limpo, com as datas e os números já
convertidos. Nada é decidido neste arquivo: ele só lê.
"""

import unicodedata
from datetime import date, datetime

# As 18 colunas do guias.csv, na ordem do arquivo.
CAMPOS = [
    "id_guia", "unidade", "data_atendimento", "paciente", "convenio", "carteirinha",
    "cid", "procedimento_codigo", "procedimento_descricao", "numero_autorizacao",
    "autorizacao_validade", "autorizacao_sessoes_limite", "sessao_numero_na_autorizacao",
    "profissional", "profissional_registro", "valor", "observacao_recepcao",
    "data_lancamento",
]

FORMATOS_DE_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y")


def sem_acento(texto):
    """'Saúde Interior' vira 'saude interior'. Serve para comparar nomes sem depender de digitação."""
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower().strip()


def ler_data(texto):
    """Aceita 2026-08-03 e também 03/08/2026. Devolve None quando não dá para entender."""
    if isinstance(texto, date):
        return texto
    texto = str(texto or "").strip()
    for formato in FORMATOS_DE_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler_inteiro(texto):
    try:
        return int(float(str(texto).strip().replace(",", ".")))
    except (ValueError, TypeError):
        return None


def ler_valor(texto):
    """Aceita 62.00, 62,00 e R$ 62,00."""
    texto = str(texto or "").replace("R$", "").strip()
    if "," in texto and "." in texto:      # 1.300,00
        texto = texto.replace(".", "")
    texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def normalizar_guia(bruta):
    """Recebe um dicionário com as colunas da guia (faltando ou sobrando) e devolve:

    - os 18 campos como texto limpo;
    - as versões já convertidas, com sublinhado na frente (_atendimento, _validade...);
    - avisos_de_leitura: o que foi entendido apesar de estar fora do padrão.
    """
    guia = {campo: str(bruta.get(campo, "") or "").strip() for campo in CAMPOS}
    avisos = []

    for campo, chave in (("data_atendimento", "_atendimento"),
                         ("autorizacao_validade", "_validade"),
                         ("data_lancamento", "_lancamento")):
        guia[chave] = ler_data(guia[campo])
        digitado = guia[campo]
        if digitado and guia[chave] and digitado != guia[chave].isoformat():
            avisos.append("%s foi digitada como '%s', fora do padrão AAAA-MM-DD do sistema. Foi lida sem problema." % (
                campo, digitado))

    guia["_sessao"] = ler_inteiro(guia["sessao_numero_na_autorizacao"])
    guia["_limite_declarado"] = ler_inteiro(guia["autorizacao_sessoes_limite"])
    guia["_valor"] = ler_valor(guia["valor"])
    guia["avisos_de_leitura"] = avisos
    return guia
