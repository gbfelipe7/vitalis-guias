"""Ajudantes pequenos para as funções da pasta api/ (Vercel, Python puro, sem framework)."""

import json

LIMITE_DO_CORPO = 20000   # bytes. Uma guia tem menos de 1 KB; isso barra abuso sem atrapalhar ninguém.


def responder(handler, status, corpo):
    dados = json.dumps(corpo, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(dados)))
    handler.end_headers()
    handler.wfile.write(dados)


def ler_json(handler):
    """Devolve (dados, erro). Nunca levanta exceção: corpo vazio, grande demais ou torto vira mensagem."""
    try:
        tamanho = int(handler.headers.get("Content-Length") or 0)
    except ValueError:
        tamanho = 0
    if tamanho <= 0:
        return None, "Mande um JSON no corpo do pedido."
    if tamanho > LIMITE_DO_CORPO:
        return None, "Corpo grande demais. O limite é %d bytes." % LIMITE_DO_CORPO
    try:
        dados = json.loads(handler.rfile.read(tamanho).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "O corpo não é um JSON válido."
    if not isinstance(dados, dict):
        return None, "O JSON precisa ser um objeto, com as chaves 'guia' ou 'texto'."
    return dados, None
