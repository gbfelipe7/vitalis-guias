"""GET /api/regra?convenio=Vitalcard&procedimento=50000470  ->  o que o convênio exige e cobre."""

import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.resposta import responder
from web.rotas import rota_regra


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        consulta = parse_qs(urlparse(self.path).query)
        try:
            responder(self, *rota_regra((consulta.get("convenio") or [""])[0],
                                        (consulta.get("procedimento") or [""])[0]))
        except Exception:
            responder(self, 500, {"erro": "Não consegui consultar a regra."})
