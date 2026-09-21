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

# O que a recepção digita para dizer "ainda não tenho". Conta como campo vazio.
MARCADORES_DE_VAZIO = {"-", "--", "---", "?", "??", "x", "xx", "xxx", "n/a", "na", "nt", "nd", "0", "00",
                       "aguardando", "pendente", "a confirmar", "confirmar", "sem", "nao tem", "nao informado",
                       "nao consta", "vazio", "null", "none"}


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


def _interpretar_data(texto):
    for formato in FORMATOS_DE_DATA:
        try:
            lida = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        return lida if 2000 <= lida.year <= 2100 else None
    return None


def ler_data(texto, ano_padrao=None, depois_de=None):
    """Aceita 2026-08-03, 03/08/2026 e também 03/08, sem ano.

    Data sem ano: vale o ano_padrao. Se ainda assim ela cair mais de 6 meses ANTES de
    depois_de, é do ano seguinte ("validade 15/01" numa guia de dezembro). Data com o ano
    escrito nunca é mexida. Devolve None quando não dá para entender ou o ano é absurdo."""
    if isinstance(texto, date):
        return texto
    texto = str(texto or "").strip()
    if not re.match(r"^\d{1,2}/\d{1,2}$", texto):
        return _interpretar_data(texto)
    ano = ano_padrao or (depois_de.year if depois_de else date.today().year)
    lida = _interpretar_data("%s/%d" % (texto, ano))
    if lida and depois_de and (depois_de - lida).days > 180:
        lida = _interpretar_data("%s/%d" % (texto, ano + 1)) or lida
    return lida


def ler_inteiro(texto):
    """Só aceita o que é claramente um número de sessão: '11', '11ª', '11 de 10' e '11/10' viram 11.
    Qualquer outra coisa ('1 1', '1O', '-3', 'sétima', '2 (na verdade 12)', '1e999') vira None,
    e o motor segura a guia em vez de adivinhar."""
    achado = re.match(r"^(\d{1,4})\s*[ªºa]?(\s*(/|de)\s*\d{1,4})?$", str(texto or "").strip(), flags=re.IGNORECASE)
    return int(achado.group(1)) if achado else None


def ler_valor(texto):
    """Aceita 62, 62.00, 62,00, R$ 62,00 e 1.300,00. Negativo, 'nan', '6_2', '1e308' e texto viram None."""
    texto = str(texto or "").replace("R$", "").strip()
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$", texto):       # 1.300,00 ou 62.000: ponto é milhar
        texto = texto.replace(".", "")
    if not re.match(r"^\d{1,7}([.,]\d{1,2})?$", texto):
        return None
    valor = float(texto.replace(",", "."))
    return valor if math.isfinite(valor) else None


def normalizar_guia(bruta):
    """Recebe um dicionário com as colunas da guia (faltando ou sobrando) e devolve:

    - os 18 campos como texto limpo;
    - as versões já convertidas, com sublinhado na frente (_atendimento, _validade...);
    - avisos_de_leitura: o que foi entendido apesar de estar fora do padrão.
    """
    bruta = bruta if isinstance(bruta, dict) else {}
    guia = {campo: limpar_texto(bruta.get(campo), TAMANHO_MAXIMO.get(campo, 200)) for campo in CAMPOS}
    avisos = []

    for campo in CAMPOS:                     # "aguardando", "-" e "N/A" são jeitos de deixar vazio
        if campo != "observacao_recepcao" and sem_acento(guia[campo]) in MARCADORES_DE_VAZIO:
            guia[campo] = ""
    # observação cortada: o que ficou de fora pode ser justamente o que segura a guia
    guia["_observacao_cortada"] = len(limpar_texto(bruta.get("observacao_recepcao"), 100000)) > TAMANHO_MAXIMO["observacao_recepcao"]

    guia["_atendimento"] = ler_data(guia["data_atendimento"])
    for campo, chave in (("data_atendimento", "_atendimento"),
                         ("autorizacao_validade", "_validade"),
                         ("data_lancamento", "_lancamento")):
        # validade e lançamento sem ano são do ano do atendimento, não do ano de hoje
        guia[chave] = ler_data(guia[campo], depois_de=guia["_atendimento"] if campo == "autorizacao_validade" else None,
                               ano_padrao=guia["_atendimento"].year if guia["_atendimento"] and campo != "data_atendimento" else None)
        digitado = guia[campo]
        if digitado and guia[chave] and digitado != guia[chave].isoformat():
            avisos.append("%s foi digitada como '%s', fora do padrão do sistema. Foi lida como %s." % (
                NOME_DA_DATA[campo], digitado, guia[chave].strftime("%d/%m/%Y")))

    guia["_sessao"] = ler_inteiro(guia["sessao_numero_na_autorizacao"])
    guia["_limite_declarado"] = ler_inteiro(guia["autorizacao_sessoes_limite"])
    guia["_valor"] = ler_valor(guia["valor"])
    guia["avisos_de_leitura"] = avisos
    return guia
