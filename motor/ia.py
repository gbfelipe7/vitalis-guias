"""O único lugar do projeto que fala com um modelo de IA (Gemini, nível gratuito).

Quem chama recebe um dicionário ou None. None quer dizer 'segue sem IA': sem chave,
sem internet, cota estourada, resposta torta ou qualquer erro. Nada aqui levanta exceção.

A IA é usada só para LER texto livre, em dois pontos: separar os campos de uma guia
colada em texto corrido (entrada.py) e ler a observação da recepção (observacao.py).
Ela nunca decide se a guia passa.
"""

import json
import os
import time
import urllib.request

# O nível gratuito tem cota por modelo. Se o primeiro estiver sem cota ou fora do ar, tenta o próximo.
MODELOS = ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite")   # os "lite" respondem em 1 a 2 segundos
ENDERECO = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
MAXIMO_DE_TEXTO = 2000      # caracteres mandados ao modelo: uma guia não passa disso
TEMPO_TOTAL = 8             # segundos, somando todas as tentativas


def perguntar_json(instrucao, texto):
    """Manda a instrução e o texto, pede resposta em JSON e devolve o dicionário. Em qualquer problema, None."""
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    corpo = json.dumps({
        "systemInstruction": {"parts": [{"text": instrucao}]},
        "contents": [{"role": "user", "parts": [{"text": str(texto)[:MAXIMO_DE_TEXTO]}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0, "maxOutputTokens": 4096},
    }).encode("utf-8")

    inicio = time.time()
    for modelo in MODELOS:
        sobra = TEMPO_TOTAL - (time.time() - inicio)
        if sobra < 2:
            break
        pedido = urllib.request.Request(ENDERECO % modelo, data=corpo,
                                        headers={"Content-Type": "application/json", "x-goog-api-key": chave})
        try:
            with urllib.request.urlopen(pedido, timeout=min(4, sobra)) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
            lido = json.loads(dados["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            continue                      # sem cota, fora do ar ou resposta torta: tenta o próximo modelo
        if isinstance(lido, dict):
            return lido
    return None
