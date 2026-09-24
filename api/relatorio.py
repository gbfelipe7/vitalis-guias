"""Relatório de terça do Dr. Renato.

GET  /api/relatorio                      ->  as 80 guias de agosto
GET  /api/relatorio?semana=2026-08-24    ->  só as lançadas de segunda 24/08 a domingo 30/08
POST /api/relatorio  {"novas": [guia…], "semana": "2026-08-24"}  ->  com as guias novas desta sessão
"""

import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.resposta import ler_json, responder
from web.rotas import rota_relatorio


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            semana = (parse_qs(urlparse(self.path).query).get("semana") or [None])[0]
            responder(self, *rota_relatorio(semana=semana))
        except Exception:
            responder(self, 500, {"erro": "Não consegui montar o relatório."})

    def do_POST(self):
        dados, erro = ler_json(self)
        if erro:
            return responder(self, 400, {"erro": erro})
        try:
            responder(self, *rota_relatorio(dados.get("novas"), dados.get("semana")))
        except Exception:
            responder(self, 500, {"erro": "Não consegui montar o relatório."})
