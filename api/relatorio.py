"""Relatório de terça do Dr. Renato.

GET  /api/relatorio                      ->  as 80 guias de agosto
POST /api/relatorio  {"novas": [guia…]}  ->  as 80 mais as guias novas conferidas nesta sessão
"""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.resposta import ler_json, responder
from web.rotas import rota_relatorio


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            responder(self, *rota_relatorio())
        except Exception:
            responder(self, 500, {"erro": "Não consegui montar o relatório."})

    def do_POST(self):
        dados, erro = ler_json(self)
        if erro:
            return responder(self, 400, {"erro": erro})
        try:
            responder(self, *rota_relatorio(dados.get("novas")))
        except Exception:
            responder(self, 500, {"erro": "Não consegui montar o relatório."})
