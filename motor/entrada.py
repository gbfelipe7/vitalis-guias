"""Transforma o que a pessoa colou em campos de guia.

A recepção não escreve em JSON. Então a entrada aceita, nesta ordem:
1. uma linha do CSV (com ou sem o cabeçalho);
2. linhas no formato 'campo: valor', com os apelidos que a recepção usa;
3. texto corrido. Com GEMINI_API_KEY, quem separa os campos é a IA. Sem chave,
   expressões regulares pegam o que dá e avisam o que ficou de fora.

Em nenhum caso este arquivo decide se a guia está certa. Ele só separa os campos.
"""

import csv
import io
import json
import os
import re
import urllib.request

from .normalizar import CAMPOS, sem_acento
from .regras import achar_procedimento

APELIDOS = {
    "id_guia": ("id", "guia", "id guia", "numero da guia"),
    "unidade": ("unidade",),
    "data_atendimento": ("data", "atendimento", "data atendimento", "data do atendimento", "dia"),
    "paciente": ("paciente", "codigo do paciente"),
    "convenio": ("convenio", "plano"),
    "carteirinha": ("carteirinha", "carteira", "matricula"),
    "cid": ("cid",),
    "procedimento_codigo": ("codigo", "procedimento codigo", "codigo do procedimento", "cod"),
    "procedimento_descricao": ("procedimento", "descricao", "procedimento descricao"),
    "numero_autorizacao": ("autorizacao", "numero autorizacao", "numero da autorizacao", "aut", "senha"),
    "autorizacao_validade": ("validade", "validade da autorizacao", "autorizacao validade", "val"),
    "autorizacao_sessoes_limite": ("limite", "sessoes autorizadas", "limite de sessoes"),
    "sessao_numero_na_autorizacao": ("sessao", "numero da sessao", "sessao numero"),
    "profissional": ("profissional", "fisioterapeuta", "medico", "atendeu"),
    "profissional_registro": ("registro", "crefito", "crm", "registro profissional"),
    "valor": ("valor", "preco"),
    "observacao_recepcao": ("obs", "observacao", "observacoes", "observacao recepcao", "nota"),
    "data_lancamento": ("lancamento", "data lancamento", "data de lancamento", "lancada em"),
}
_POR_APELIDO = {sem_acento(a): campo for campo, lista in APELIDOS.items() for a in lista + (campo,)}
_POR_APELIDO.update({sem_acento(c.replace("_", " ")): c for c in CAMPOS})


def _de_csv(texto):
    linhas = [l for l in csv.reader(io.StringIO(texto.strip())) if l]
    if not linhas:
        return None
    if len(linhas) >= 2 and [c.strip() for c in linhas[0]] == CAMPOS:
        linhas = linhas[1:]
    if len(linhas[0]) != len(CAMPOS):
        return None
    return dict(zip(CAMPOS, [c.strip() for c in linhas[0]]))


def _de_campos(texto):
    campos = {}
    for linha in texto.splitlines():
        if ":" not in linha and "=" not in linha:
            continue
        nome, valor = re.split(r"[:=]", linha, maxsplit=1)
        campo = _POR_APELIDO.get(sem_acento(nome.strip(" -*\t")))
        if campo and valor.strip():
            campos[campo] = valor.strip()
    sessao = re.match(r"^(\d+)\s*(?:/|de)\s*(\d+)$", campos.get("sessao_numero_na_autorizacao", ""))
    if sessao:
        campos["sessao_numero_na_autorizacao"], campos["autorizacao_sessoes_limite"] = sessao.groups()
    return campos if len(campos) >= 4 else None


def _de_regex(texto, regras):
    """Melhor esforço, sem IA. Pega só o que tem formato inconfundível."""
    campos, t = {}, sem_acento(texto)
    for regra in regras["convenios"].values():
        if sem_acento(regra["nome"]) in t:
            campos["convenio"] = regra["nome"]
    for codigo, proc in regras["procedimentos"].items():
        if codigo in texto:
            campos["procedimento_codigo"], campos["procedimento_descricao"] = codigo, proc["descricao"]
    if "procedimento_codigo" not in campos:
        pelo_nome = achar_procedimento(regras, texto)
        if pelo_nome:
            campos["procedimento_codigo"], campos["procedimento_descricao"] = pelo_nome["codigo"], pelo_nome["descricao"]
    achados = {
        "numero_autorizacao": r"\b(AUT\s?\d{4,})\b",
        "profissional_registro": r"\b(CREFITO[-\s]?\d*\s?\d{4,}(?:-F)?|CRM[-\s]?[A-Z]{2}\s?\d{3,})",
        "cid": r"\b([A-TV-Z]\d{2}(?:\.\d)?)\b",
        "carteirinha": r"\b(\d{9})\b",
        "paciente": r"\b(P-\d{3,})\b",
        "id_guia": r"\b(G-\d{4}-\d{4})\b",
        "valor": r"R\$\s?(\d+[.,]\d{2})",
    }
    for campo, padrao in achados.items():
        m = re.search(padrao, texto, flags=re.IGNORECASE if campo in ("numero_autorizacao", "profissional_registro") else 0)
        if m:
            campos[campo] = m.group(1).replace(" ", "") if campo == "numero_autorizacao" else m.group(1)
    sessao = re.search(r"sess[aã]o\s*(\d+)\s*(?:/|de)\s*(\d+)", texto, flags=re.IGNORECASE)
    if sessao:
        campos["sessao_numero_na_autorizacao"], campos["autorizacao_sessoes_limite"] = sessao.groups()
    validade = re.search(r"val(?:idade)?\.?\s*(?:at[eé]\s*)?(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})", texto, flags=re.IGNORECASE)
    if validade:
        campos["autorizacao_validade"] = validade.group(1)
    datas = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}", texto)
    datas = [d for d in datas if d != campos.get("autorizacao_validade")]
    if datas:
        campos["data_atendimento"] = datas[0]
    for unidade in ("Centro", "Norte", "Sul"):
        if re.search(r"\bunidade\s+%s\b|\b%s\b" % (unidade, unidade), texto):
            campos.setdefault("unidade", unidade)
    obs = re.search(r"obs(?:erva[cç][aã]o)?\.?\s*[:\-]?\s*(.+)$", texto, flags=re.IGNORECASE | re.DOTALL)
    if obs:
        campos["observacao_recepcao"] = obs.group(1).strip()
    return campos


def _de_ia(texto, regras):
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    instrucao = (
        "Separe em campos o texto que a recepção de uma clínica escreveu sobre uma guia de convênio. "
        "Devolva só um JSON com estas chaves, todas como texto, vazias quando a informação não estiver "
        "no texto: %s. Datas como AAAA-MM-DD. Convênios conhecidos: %s. Procedimentos (código e nome): %s. "
        "id_guia só quando o texto trouxer um número de guia (formato G-0000-0000). paciente é o código "
        "do paciente (formato P-0000) quando existir. Tudo que for comentário da recepção vai em "
        "observacao_recepcao, copiado como está. Não invente nada que não esteja escrito." % (
            ", ".join(CAMPOS),
            ", ".join(r["nome"] for r in regras["convenios"].values()),
            "; ".join("%s %s" % (c, p["descricao"]) for c, p in regras["procedimentos"].items())))
    corpo = json.dumps({
        "systemInstruction": {"parts": [{"text": instrucao}]},
        "contents": [{"role": "user", "parts": [{"text": texto}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }).encode("utf-8")
    pedido = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        data=corpo, headers={"Content-Type": "application/json", "x-goog-api-key": chave})
    try:
        with urllib.request.urlopen(pedido, timeout=9) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        lido = json.loads(dados["candidates"][0]["content"]["parts"][0]["text"])
        return {c: str(lido.get(c) or "").strip() for c in CAMPOS if str(lido.get(c) or "").strip()}
    except Exception:
        return None


def interpretar_texto(texto, regras, usar_ia=True):
    """Devolve {"campos": {...}, "lido_por": ..., "faltando": [...]}."""
    texto = str(texto or "").strip()
    campos, lido_por = _de_csv(texto), "linha do CSV"
    if campos is None:
        campos, lido_por = _de_campos(texto), "campos 'nome: valor'"
    if campos is None and usar_ia:
        campos, lido_por = _de_ia(texto, regras), "IA"
    if campos is None:
        campos, lido_por = _de_regex(texto, regras), "expressões regulares, sem IA"

    essenciais = ("convenio", "procedimento_codigo", "data_atendimento")
    return {"campos": campos, "lido_por": lido_por,
            "faltando": [c for c in essenciais if not campos.get(c)]}
