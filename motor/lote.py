"""Confere um lote inteiro. É aqui que entra o que uma guia sozinha não mostra: duplicidade."""

import csv
import os

from .normalizar import normalizar_guia
from .regras import PASTA_DADOS
from .verificar import verificar_guia


def carregar_guias(caminho=None):
    caminho = caminho or os.path.join(PASTA_DADOS, "guias.csv")
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def registros_conhecidos(guias_brutas):
    """{profissional: registro}, tirado das guias em que o registro foi preenchido."""
    conhecidos = {}
    for bruta in guias_brutas:
        nome, registro = (bruta.get("profissional") or "").strip(), (bruta.get("profissional_registro") or "").strip()
        if nome and registro:
            conhecidos.setdefault(nome, registro)
    return conhecidos


def mapear_duplicidades(guias_brutas):
    """Devolve {id_guia: {"tipo": "exata" | "suspeita", "outra": id}}.

    Exata:    mesmo paciente, data, procedimento, autorização e sessão. A que foi lançada
              depois é a duplicada; a primeira segue normal.
    Suspeita: mesmo paciente, data e procedimento, mas com autorização diferente. As duas
              ficam para conferir, porque não dá para saber qual está errada.

    As datas são comparadas já normalizadas: 26/08/2026 e 2026-08-26 são o mesmo dia.
    """
    guias = [normalizar_guia(b) for b in guias_brutas]
    por_atendimento = {}
    for guia in guias:
        chave = (guia["paciente"], guia["_atendimento"], guia["procedimento_codigo"])
        if all(chave):
            por_atendimento.setdefault(chave, []).append(guia)

    mapa = {}
    for grupo in por_atendimento.values():
        if len(grupo) < 2:
            continue
        grupo.sort(key=lambda g: (g["_lancamento"] or g["_atendimento"], g["id_guia"]))
        primeira = grupo[0]
        for outra in grupo[1:]:
            mesma_autorizacao = (outra["numero_autorizacao"], outra["_sessao"]) == \
                                (primeira["numero_autorizacao"], primeira["_sessao"])
            if mesma_autorizacao:
                mapa[outra["id_guia"]] = {"tipo": "exata", "outra": primeira["id_guia"]}
            else:
                mapa[outra["id_guia"]] = {"tipo": "suspeita", "outra": primeira["id_guia"]}
                mapa.setdefault(primeira["id_guia"], {"tipo": "suspeita", "outra": outra["id_guia"]})
    return mapa


def verificar_lote(guias_brutas, regras, usar_ia=False):
    """Confere todas as guias, cada uma na sua data de lançamento (a guia acabou de ser lançada
    e ainda não foi enviada)."""
    duplicidades = mapear_duplicidades(guias_brutas)
    conhecidos = registros_conhecidos(guias_brutas)
    return [
        verificar_guia(bruta, regras,
                       duplicidade=duplicidades.get((bruta.get("id_guia") or "").strip()),
                       registros_conhecidos=conhecidos, usar_ia=usar_ia)
        for bruta in guias_brutas
    ]


def verificar_nova(bruta, guias_do_lote, regras, usar_ia=True):
    """Confere uma guia que acabou de chegar, olhando o lote para achar duplicidade."""
    bruta = dict(bruta)
    if not (bruta.get("id_guia") or "").strip():
        bruta["id_guia"] = "NOVA"
    todas = [g for g in guias_do_lote if (g.get("id_guia") or "").strip() != bruta["id_guia"]] + [bruta]
    duplicidades = mapear_duplicidades(todas)
    return verificar_guia(bruta, regras, duplicidade=duplicidades.get(bruta["id_guia"]),
                          registros_conhecidos=registros_conhecidos(guias_do_lote), usar_ia=usar_ia)
