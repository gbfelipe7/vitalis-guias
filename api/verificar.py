"""POST /api/verificar  ->  confere uma guia nova e devolve a decisão.

Corpo, um dos dois:
  {"guia": {"convenio": "Vitalcard", "procedimento_codigo": "50000470", ...}}
  {"texto": "o que a recepção escreveu, do jeito que escreveu"}

É este endereço que o sistema de gestão (ou um fluxo no n8n) chama a cada guia lançada,
para a conferência acontecer antes do envio sem depender de alguém lembrar.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.resposta import ler_json, responder
from web.rotas import rota_verificar


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        dados, erro = ler_json(self)
        if erro:
            return responder(self, 400, {"erro": erro})
        try:
            responder(self, *rota_verificar(dados))
        except Exception:
            responder(self, 500, {"erro": "Erro ao conferir a guia. Ela não foi conferida: não envie ainda."})

    def do_GET(self):
        responder(self, 405, {"erro": "Use POST com 'guia' ou 'texto' no corpo."})
