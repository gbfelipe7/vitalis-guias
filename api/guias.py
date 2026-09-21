"""GET /api/guias  ->  as 80 guias de agosto já conferidas, mais o relatório do lote."""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.resposta import responder
from web.rotas import rota_guias


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            responder(self, *rota_guias())
        except Exception:
            responder(self, 500, {"erro": "Não consegui conferir o lote. Tente de novo."})
