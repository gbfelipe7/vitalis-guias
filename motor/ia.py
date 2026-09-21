"""O único lugar do projeto que fala com um modelo de IA (Gemini, nível gratuito).

Quem chama recebe um dicionário ou None. None quer dizer 'segue sem IA': sem chave,
sem internet, resposta torta ou qualquer erro. Nada aqui levanta exceção.

A IA é usada só para LER texto livre, em dois pontos: separar os campos de uma guia
colada em texto corrido (entrada.py) e ler a observação da recepção (observacao.py).
Ela nunca decide se a guia passa.
"""

import json
import os
import urllib.request

ENDERECO = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
MAXIMO_DE_TEXTO = 2000      # caracteres mandados ao modelo: uma guia não passa disso


def tem_chave():
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def perguntar_json(instrucao, texto):
    """Manda a instrução e o texto, pede resposta em JSON e devolve o dicionário. Em qualquer problema, None."""
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    corpo = json.dumps({
        "systemInstruction": {"parts": [{"text": instrucao}]},
        "contents": [{"role": "user", "parts": [{"text": str(texto)[:MAXIMO_DE_TEXTO]}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0, "maxOutputTokens": 1024},
    }).encode("utf-8")
    pedido = urllib.request.Request(ENDERECO, data=corpo,
                                    headers={"Content-Type": "application/json", "x-goog-api-key": chave})
    try:
        with urllib.request.urlopen(pedido, timeout=9) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        lido = json.loads(dados["candidates"][0]["content"]["parts"][0]["text"])
    except Exception:
        return None
    return lido if isinstance(lido, dict) else None
