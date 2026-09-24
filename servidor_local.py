"""Roda a página e a API na sua máquina, sem Vercel:  python3 servidor_local.py

Abre em http://localhost:8000. As regras e as respostas vêm das mesmas funções de web/rotas.py que a
versão publicada usa. O que muda é só quem recebe o pedido: aqui um servidor simples, lá a Vercel.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from web.resposta import ler_json, responder
from web.rotas import rota_guias, rota_regra, rota_relatorio, rota_verificar

RAIZ = os.path.dirname(os.path.abspath(__file__))


class Local(BaseHTTPRequestHandler):
    timeout = 10          # cliente que abre conexão e não manda nada é derrubado em 10 segundos

    def do_GET(self):
        caminho = urlparse(self.path)
        if caminho.path in ("/", "/index.html"):
            with open(os.path.join(RAIZ, "public", "index.html"), "rb") as arquivo:
                pagina = arquivo.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(pagina)
        elif caminho.path == "/api/guias":
            responder(self, *rota_guias())
        elif caminho.path == "/api/relatorio":
            responder(self, *rota_relatorio(semana=(parse_qs(caminho.query).get("semana") or [None])[0]))
        elif caminho.path == "/api/regra":
            q = parse_qs(caminho.query)
            responder(self, *rota_regra((q.get("convenio") or [""])[0], (q.get("procedimento") or [""])[0]))
        else:
            responder(self, 404, {"erro": "Endereço não existe."})

    def do_POST(self):
        dados, erro = ler_json(self)
        if erro:
            return responder(self, 400, {"erro": erro})
        caminho = urlparse(self.path).path
        if caminho == "/api/verificar":
            responder(self, *rota_verificar(dados))
        elif caminho == "/api/relatorio":
            responder(self, *rota_relatorio(dados.get("novas"), dados.get("semana")))
        else:
            responder(self, 404, {"erro": "Endereço não existe."})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Rodando em http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("127.0.0.1", 8000), Local).serve_forever()
