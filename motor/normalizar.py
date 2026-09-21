"""Deixa a guia num formato só, venha ela do CSV, do formulário ou do MCP.

A recepção digita data como 03/08/2026, valor como 62,00 e às vezes deixa espaço
sobrando. Aqui tudo isso vira um dicionário limpo, com as datas e os números já
convertidos. Nada é decidido neste arquivo: ele só lê. O que não dá para ler vira
None, e quem reclama é o motor (verificar.py).
"""

import math
import re
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

# Como cada campo de data aparece para quem lê o aviso.
NOME_DA_DATA = {
    "data_atendimento": "A data do atendimento",
    "autorizacao_validade": "A validade da autorização",
    "data_lancamento": "A data de lançamento",
}

FORMATOS_DE_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y")
TAMANHO_MAXIMO = {"observacao_recepcao": 1000}      # os outros campos: 200 caracteres


def sem_acento(texto):
    """'Saúde Interior' vira 'saude interior'. Serve para comparar nomes sem depender de digitação."""
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower().strip()


def limpar_texto(valor, limite=200):
    """Qualquer coisa vira texto curto e seguro: número vira texto, None vira vazio,
    caractere de controle some e o tamanho é cortado."""
    if valor is None or isinstance(valor, (list, dict, bool)):
        return ""
    texto = str(valor).encode("utf-8", "ignore").decode("utf-8")
    texto = "".join(c for c in texto if c == "\n" or unicodedata.category(c)[0] != "C")
    return texto.strip()[:limite]


def ler_data(texto, ano_padrao=None):
    """Aceita 2026-08-03, 03/08/2026 e também 03/08 (sem ano, vale o ano_padrao).
    Devolve None quando não dá para entender ou quando o ano é absurdo."""
    if isinstance(texto, date):
        return texto
    texto = str(texto or "").strip()
    if re.match(r"^\d{1,2}/\d{1,2}$", texto):
        texto = "%s/%d" % (texto, ano_padrao or date.today().year)
    for formato in FORMATOS_DE_DATA:
        try:
            lida = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        return lida if 2000 <= lida.year <= 2100 else None
    return None


def ler_inteiro(texto):
    """Vale o número inteiro do começo: '11', '11ª' e '11 de 10' viram 11.
    '-3', 'sétima', '1e999' e '7,5' viram None."""
    achado = re.match(r"^(\d{1,6})(?![\d.,eE])", str(texto or "").strip())
    return int(achado.group(1)) if achado else None


def ler_valor(texto):
    """Aceita 62.00, 62,00 e R$ 62,00. Negativo, 'nan', 'inf' e texto viram None."""
    texto = str(texto or "").replace("R$", "").strip()
    if "," in texto and "." in texto:      # 1.300,00
        texto = texto.replace(".", "")
    texto = texto.replace(",", ".")
    try:
        valor = float(texto)
    except (ValueError, OverflowError):
        return None
    return valor if math.isfinite(valor) and valor >= 0 else None


def normalizar_guia(bruta):
    """Recebe um dicionário com as colunas da guia (faltando ou sobrando) e devolve:

    - os 18 campos como texto limpo;
    - as versões já convertidas, com sublinhado na frente (_atendimento, _validade...);
    - avisos_de_leitura: o que foi entendido apesar de estar fora do padrão.
    """
    bruta = bruta if isinstance(bruta, dict) else {}
    guia = {campo: limpar_texto(bruta.get(campo), TAMANHO_MAXIMO.get(campo, 200)) for campo in CAMPOS}
    avisos = []

    for campo, chave in (("data_atendimento", "_atendimento"),
                         ("autorizacao_validade", "_validade"),
                         ("data_lancamento", "_lancamento")):
        guia[chave] = ler_data(guia[campo])
        digitado = guia[campo]
        if digitado and guia[chave] and digitado != guia[chave].isoformat():
            avisos.append("%s foi digitada como '%s', fora do padrão do sistema. Foi lida como %s." % (
                NOME_DA_DATA[campo], digitado, guia[chave].strftime("%d/%m/%Y")))

    guia["_sessao"] = ler_inteiro(guia["sessao_numero_na_autorizacao"])
    guia["_limite_declarado"] = ler_inteiro(guia["autorizacao_sessoes_limite"])
    guia["_valor"] = ler_valor(guia["valor"])
    guia["avisos_de_leitura"] = avisos
    return guia
