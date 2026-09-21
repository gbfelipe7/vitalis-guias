"""Confere um lote inteiro. É aqui que entra o que uma guia sozinha não mostra: duplicidade."""

import csv
import os
from datetime import datetime, timedelta

from .normalizar import normalizar_guia
from .regras import PASTA_DADOS
from .verificar import verificar_guia


def hoje():
    """O dia de hoje no horário de Brasília. O servidor da Vercel roda em UTC."""
    return (datetime.utcnow() - timedelta(hours=3)).date()


def carregar_guias(caminho=None):
    caminho = caminho or os.path.join(PASTA_DADOS, "guias.csv")
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:     # utf-8-sig aceita arquivo salvo pelo Excel
        return list(csv.DictReader(arquivo))


def registros_conhecidos(guias_brutas):
    """{profissional: registro}, tirado das guias em que o registro foi preenchido."""
    conhecidos = {}
    for bruta in guias_brutas:
        nome, registro = (bruta.get("profissional") or "").strip(), (bruta.get("profissional_registro") or "").strip()
        if nome and registro:
            conhecidos.setdefault(nome, registro)
    return conhecidos


def mapear_duplicidades(guias_brutas, chegou_agora=None):
    """Devolve uma lista do tamanho do lote: None, ou {"tipo": "exata" | "suspeita", "outra": id}.

    Exata:    mesmo paciente, data, procedimento, autorização e sessão de uma guia anterior.
              A anterior segue normal; a repetida não deve ser enviada.
    Suspeita: mesmo paciente, data e procedimento, mas com outra autorização. As duas ficam
              para conferir, porque não dá para saber qual está errada.

    'Anterior' é a que foi lançada antes. A guia que está chegando agora (posição chegou_agora)
    é sempre a mais nova, tenha ou não data de lançamento. As datas são comparadas já
    normalizadas: 26/08/2026 e 2026-08-26 são o mesmo dia.
    """
    guias = [normalizar_guia(b) for b in guias_brutas]
    grupos = {}
    for posicao, guia in enumerate(guias):
        chave = (guia["paciente"].upper(), guia["_atendimento"], guia["procedimento_codigo"])
        if all(chave):
            grupos.setdefault(chave, []).append(posicao)

    mapa = [None] * len(guias)
    for posicoes in grupos.values():
        if len(posicoes) < 2:
            continue
        posicoes.sort(key=lambda p: (p == chegou_agora,
                                     guias[p]["_lancamento"] or guias[p]["_atendimento"], guias[p]["id_guia"]))
        for i, atual in enumerate(posicoes[1:], start=1):
            anteriores = posicoes[:i]
            gemea = [p for p in anteriores
                     if (guias[p]["numero_autorizacao"].upper(), guias[p]["_sessao"]) ==
                        (guias[atual]["numero_autorizacao"].upper(), guias[atual]["_sessao"])]
            if gemea:
                mapa[atual] = {"tipo": "exata", "outra": guias[gemea[0]]["id_guia"]}
            else:
                mapa[atual] = {"tipo": "suspeita", "outra": guias[anteriores[0]]["id_guia"]}
                if mapa[anteriores[0]] is None:
                    mapa[anteriores[0]] = {"tipo": "suspeita", "outra": guias[atual]["id_guia"]}
    return mapa


def verificar_lote(guias_brutas, regras, usar_ia=False):
    """Confere todas as guias, cada uma na sua data de lançamento: a guia acabou de ser lançada
    e ainda não foi enviada. Sem IA, para o lote dar sempre o mesmo resultado."""
    duplicidades = mapear_duplicidades(guias_brutas)
    conhecidos = registros_conhecidos(guias_brutas)
    return [verificar_guia(bruta, regras, duplicidade=duplicidades[posicao],
                           registros_conhecidos=conhecidos, usar_ia=usar_ia)
            for posicao, bruta in enumerate(guias_brutas)]


def verificar_nova(bruta, guias_do_lote, regras, usar_ia=True, referencia=None):
    """Confere uma guia que está chegando agora. A conferência vale para HOJE, não para a data
    de lançamento que veio escrita, e a guia é comparada com o lote para achar duplicidade."""
    bruta = dict(bruta) if isinstance(bruta, dict) else {}
    bruta["id_guia"] = str(bruta.get("id_guia") or "").strip() or "NOVA"
    # mesma guia conferida de novo (mesmo id) não é duplicata de si mesma
    outras = [g for g in guias_do_lote if (g.get("id_guia") or "").strip() != bruta["id_guia"]]
    duplicidades = mapear_duplicidades(outras + [bruta], chegou_agora=len(outras))
    return verificar_guia(bruta, regras, referencia=referencia or hoje(), duplicidade=duplicidades[-1],
                          registros_conhecidos=registros_conhecidos(guias_do_lote), usar_ia=usar_ia,
                          veio_do_sistema=False)
