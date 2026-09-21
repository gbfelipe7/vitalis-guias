"""Lê o que a recepção escreveu na guia e devolve FATOS. Não decide nada.

É o único lugar do projeto em que entra IA, e mesmo assim como segunda opção:

1. Palavras-chave primeiro. É de graça, instantâneo e dá sempre o mesmo resultado.
2. Se sobrou texto que as palavras-chave não reconhecem, e existe GEMINI_API_KEY
   no ambiente, o modelo lê e devolve os mesmos fatos em JSON.
3. Sem chave, o texto não reconhecido vira um fato "nao_reconhecida" e o motor
   segura a guia para uma pessoa ler. Na dúvida, segura.

Quem decide se a guia passa é sempre o motor (verificar.py), em cima destes fatos.
"""

import json
import os
import re
import urllib.request

from .normalizar import ler_data, sem_acento

FATOS_VAZIOS = {
    "particular": False,              # paciente quer faturar como particular
    "protocolo_verbal": "",           # autorização por telefone, com o protocolo
    "autorizacao_nova": False,        # trouxe autorização nova, número ainda não lançado
    "nova_validade": None,            # validade da autorização nova, se a recepção escreveu
    "procedimento_real": "",          # o que foi feito de verdade, se for outro
    "remarcada": False,               # sessão remarcada com autorização da data original
    "nao_reconhecida": False,         # tem texto, ninguém entendeu
    "lido_por": "",                   # 'palavras-chave' ou 'ia'
}

# Frases que aparecem muito e não mudam nada na guia.
SEM_EFEITO = ("atrasad", "recibo", "confirmado pelo whatsapp", "exame novo", "anexado ao prontuario")


def _por_palavras_chave(texto, ano):
    fatos = dict(FATOS_VAZIOS)
    t = sem_acento(texto)
    achou = False

    if "particular" in t and ("faturar" in t or "nao quer usar" in t or "sem convenio" in t):
        fatos["particular"] = True
        achou = True

    protocolo = re.search(r"protocolo\s*(?:n[ºo.]*\s*)?(\d{4,})", t)
    if protocolo and ("telefone" in t or "verbal" in t or "aguardando" in t):
        fatos["protocolo_verbal"] = protocolo.group(1)
        achou = True

    if "autorizacao nova" in t or "nova autorizacao" in t:
        fatos["autorizacao_nova"] = True
        validade = re.search(r"validade\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", t)
        if validade:
            dia = validade.group(1)
            if dia.count("/") == 1:
                dia = "%s/%s" % (dia, ano)
            fatos["nova_validade"] = ler_data(dia)
        achou = True

    real = re.search(r"procedimento realizado foi ([^,.;]+)", texto, flags=re.IGNORECASE)
    if real or "codigo certo" in t or "codigo errado" in t:
        fatos["procedimento_real"] = real.group(1).strip() if real else "outro procedimento"
        achou = True

    if "remarcad" in t and "autorizacao" in t:
        fatos["remarcada"] = True
        achou = True

    if achou:
        fatos["lido_por"] = "palavras-chave"
    return fatos, achou


def _por_ia(texto):
    """Pede ao Gemini os mesmos fatos, em JSON. Qualquer erro devolve None e o chamador segue sem IA."""
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    instrucao = (
        "Você lê a observação que a recepção de uma clínica escreveu numa guia de convênio. "
        "Devolva só um JSON com estas chaves: particular (true se o paciente quer faturar como "
        "particular), protocolo_verbal (número do protocolo se a autorização foi por telefone, "
        "senão string vazia), autorizacao_nova (true se o paciente trouxe autorização nova ainda "
        "não lançada), nova_validade (AAAA-MM-DD ou string vazia), procedimento_real (nome do "
        "procedimento realmente feito, se for diferente do lançado, senão string vazia), remarcada "
        "(true se a sessão foi remarcada e a autorização era da data original). Se a observação "
        "não fala de nada disso, devolva tudo falso ou vazio. Não invente."
    )
    corpo = json.dumps({
        "systemInstruction": {"parts": [{"text": instrucao}]},
        "contents": [{"role": "user", "parts": [{"text": texto}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }).encode("utf-8")
    pedido = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        data=corpo, headers={"Content-Type": "application/json", "x-goog-api-key": chave})
    try:
        with urllib.request.urlopen(pedido, timeout=8) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        lido = json.loads(dados["candidates"][0]["content"]["parts"][0]["text"])
    except Exception:
        return None

    fatos = dict(FATOS_VAZIOS)
    fatos["particular"] = bool(lido.get("particular"))
    fatos["protocolo_verbal"] = str(lido.get("protocolo_verbal") or "")
    fatos["autorizacao_nova"] = bool(lido.get("autorizacao_nova"))
    fatos["nova_validade"] = ler_data(lido.get("nova_validade") or "")
    fatos["procedimento_real"] = str(lido.get("procedimento_real") or "")
    fatos["remarcada"] = bool(lido.get("remarcada"))
    fatos["lido_por"] = "ia"
    return fatos


def ler_observacao(texto, ano=2026, usar_ia=False):
    """Devolve os fatos da observação. usar_ia=False deixa tudo por palavras-chave."""
    texto = str(texto or "").strip()
    if not texto:
        return dict(FATOS_VAZIOS)

    fatos, achou = _por_palavras_chave(texto, ano)
    if achou:
        return fatos

    if any(frase in sem_acento(texto) for frase in SEM_EFEITO):
        fatos["lido_por"] = "palavras-chave"
        return fatos

    if usar_ia:
        da_ia = _por_ia(texto)
        if da_ia is not None:
            return da_ia

    fatos["nao_reconhecida"] = True
    fatos["lido_por"] = "ninguém"
    return fatos
