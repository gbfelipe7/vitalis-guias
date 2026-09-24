"""O coração do projeto: recebe uma guia e devolve OK ou PENDENTE, com motivo e o que corrigir.

Aqui não tem IA. Cada checagem é uma função pequena que olha uma regra e, se achar
problema, devolve uma pendência. A decisão é só isto: tem pendência, é PENDENTE.

Cada pendência tem um tipo (para o relatório), uma gravidade, o motivo e o que corrigir.
As gravidades, da pior para a mais leve (os nomes que a pessoa lê estão em textos.py):
- nao_enviar: "Não enviar assim". Fere uma regra escrita do convênio: enviar assim é glosa certa.
- corrigir:   "Corrigir antes de enviar". Falta um dado ou tem dado errado, e dá para arrumar a guia.
- conferir:   "Conferir antes de enviar". Cheira a erro, mas a regra escrita não proíbe. Na dúvida, segura.
"""

from datetime import date, timedelta

from .normalizar import normalizar_guia, sem_acento
from .observacao import ler_observacao
from .regras import achar_convenio, achar_procedimento
from .textos import (ALERTA, CORRIGIR, DECISOES, EXPLICACAO, MOTIVO, NOMES_DOS_CAMPOS, ORDEM_GRAVIDADE,
                     PROXIMOS_PASSOS, TIPOS, AVISO_PARA, AVISO_TEXTO, reais)


def _br(dia):
    return dia.strftime("%d/%m/%Y") if dia else ""


def _somar_dias_uteis(inicio, dias):
    """Conta só segunda a sexta. Feriado não entra: a prova não traz calendário."""
    dia = inicio
    while dias > 0:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            dias -= 1
    return dia


# Quem resolve, pela ação que o motor manda fazer. O que não está aqui segue a gravidade:
# 'conferir' é sempre confirmar; 'corrigir' é a recepção; 'nao_enviar' sem regra própria é o financeiro.
PASSO_POR_ACAO = {
    "duplicata_exata": "copia",
    "particular": "particular", "nao_coberto_particular": "particular",
    "nao_coberto": "financeiro", "prazo_vencido": "financeiro",
    "autorizacao_vencida": "convenio", "nova_tambem_nao_cobre": "convenio", "sessao_acima": "convenio",
    "sem_autorizacao_verbal_vencida": "convenio", "sem_autorizacao": "convenio",
    "sem_autorizacao_verbal_ok": "convenio", "sem_autorizacao_verbal_nao_aceita": "convenio",
}
PASSO_DA_GRAVIDADE = {"nao_enviar": "financeiro", "corrigir": "recepcao", "conferir": "confirmar"}


def _pendencia(tipo, gravidade, chave, corrigir=None, passo=None, **dados):
    """Monta uma pendência buscando as frases em textos.py."""
    acao = corrigir or chave
    passo = passo or ("confirmar" if gravidade == "conferir" else PASSO_POR_ACAO.get(acao, PASSO_DA_GRAVIDADE[gravidade]))
    return {
        "tipo": tipo,
        "titulo": TIPOS[tipo],
        "gravidade": gravidade,
        "motivo": MOTIVO[chave].format(**dados),
        "corrigir": CORRIGIR[acao].format(**dados),
        "proximo_passo": passo,
        "regra": chave,
    }


# ---------------------------------------------------------------- checagens

def _campos_obrigatorios(guia, regra, extra, fatos, referencia, registros_conhecidos):
    pendencias = []
    for campo in regra["campos_obrigatorios"]:
        if guia[campo]:
            continue

        if campo == "numero_autorizacao":
            pendencias.append(_sem_autorizacao(guia, regra, extra, fatos, referencia))
            continue

        sugestao = ""
        if campo == "profissional_registro":
            conhecido = registros_conhecidos.get(guia["profissional"])
            if conhecido:
                sugestao = " Nas outras guias, %s aparece com %s." % (guia["profissional"], conhecido)
        pendencias.append(_pendencia(
            "campo_obrigatorio", "corrigir", "campo_vazio",
            convenio=regra["nome"], campo=NOMES_DOS_CAMPOS.get(campo, campo), sugestao=sugestao))
    return pendencias


def _sem_autorizacao(guia, regra, extra, fatos, referencia):
    protocolo = fatos["protocolo_verbal"]
    if not protocolo:                      # inclui "autorizado por telefone" sem o número do protocolo
        return _pendencia("sem_autorizacao", "corrigir", "sem_autorizacao")

    dias_uteis = extra.get("autorizacao_verbal_dias_uteis", 0)
    if not dias_uteis:
        return _pendencia("sem_autorizacao", "corrigir", "sem_autorizacao_verbal_nao_aceita",
                          protocolo=protocolo, convenio=regra["nome"])

    limite = _somar_dias_uteis(guia["_atendimento"], dias_uteis) if guia["_atendimento"] else None
    if limite and referencia and referencia > limite:
        return _pendencia("sem_autorizacao", "nao_enviar", "sem_autorizacao_verbal_vencida",
                          protocolo=protocolo, convenio=regra["nome"],
                          dias_uteis=dias_uteis, limite=_br(limite))
    return _pendencia("sem_autorizacao", "corrigir", "sem_autorizacao_verbal_ok",
                      protocolo=protocolo, convenio=regra["nome"],
                      dias_uteis=dias_uteis, limite=_br(limite))


def _dados_minimos(guia):
    """Sem paciente, sessão ou valor a guia não tem como ser conferida. Não passa calada."""
    pendencias = []
    if not guia["paciente"]:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "sem_paciente"))
    if guia["_sessao"] is None or guia["_sessao"] < 1:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "sem_sessao",
                                     valor=guia["sessao_numero_na_autorizacao"]))
    if guia["_valor"] is None or guia["_valor"] <= 0:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "sem_valor", valor=guia["valor"]))
    return pendencias


def _datas(guia, referencia):
    pendencias = []
    if not guia["data_atendimento"]:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "sem_data_atendimento"))
    if guia["_atendimento"] and referencia and guia["_atendimento"] > referencia:
        pendencias.append(_pendencia("dado_invalido", "conferir", "atendimento_no_futuro",
                                     atendimento=_br(guia["_atendimento"]), referencia=_br(referencia)))
    for campo, chave in (("data_atendimento", "_atendimento"), ("autorizacao_validade", "_validade")):
        if guia[campo] and guia[chave] is None:
            pendencias.append(_pendencia("dado_invalido", "corrigir", "data_ilegivel",
                                         campo=campo, valor=guia[campo]))
    if guia["_atendimento"] and guia["_lancamento"] and guia["_lancamento"] < guia["_atendimento"]:
        pendencias.append(_pendencia("dado_invalido", "conferir", "lancada_antes",
                                     lancamento=_br(guia["_lancamento"]),
                                     atendimento=_br(guia["_atendimento"])))
    return pendencias


def _validade_da_autorizacao(guia, fatos):
    """A autorização vale até a data de validade, inclusive, comparada com o atendimento."""
    atendimento, validade = guia["_atendimento"], guia["_validade"]
    if not (atendimento and validade) or atendimento <= validade:
        return []

    if fatos["autorizacao_nova"]:
        nova = fatos["nova_validade"]
        if nova and nova < atendimento:
            return [_pendencia("autorizacao_vencida", "nao_enviar", "nova_tambem_nao_cobre",
                               validade=_br(validade), nova=_br(nova), atendimento=_br(atendimento))]
        return [_pendencia("autorizacao_vencida", "corrigir", "autorizacao_vencida_com_nova",
                           validade=_br(validade),
                           nova_validade=", válida até %s" % _br(nova) if nova else "")]
    return [_pendencia("autorizacao_vencida", "nao_enviar", "autorizacao_vencida",
                       validade=_br(validade), atendimento=_br(atendimento),
                       dias=(atendimento - validade).days)]


def _limite_efetivo(guia, regra):
    """A autorização pode cobrir menos que o máximo do convênio: vale o menor dos dois."""
    limite = regra["limite_sessoes_por_autorizacao"]
    return min(limite, guia["_limite_declarado"] or limite)


def _limite_de_sessoes(guia, regra, extra):
    sessao, limite = guia["_sessao"], regra["limite_sessoes_por_autorizacao"]
    if sessao is None:
        return []                       # quem reclama de sessão ilegível é _dados_minimos
    if sessao > limite:
        acao = extra.get("ao_passar_do_limite", "Pedir nova autorização ao convênio antes de enviar.")
        return [_pendencia("sessao_acima_do_limite", "nao_enviar", "sessao_acima",
                           sessao=sessao, limite=limite, convenio=regra["nome"], acao=acao)]
    # A autorização pode cobrir menos que o máximo do convênio. Não é regra escrita do convênio,
    # é o que a própria guia declara: por isso 'conferir'.
    declarado = guia["_limite_declarado"]
    if declarado and sessao > declarado:
        return [_pendencia("sessao_acima_do_limite", "conferir", "sessao_acima_do_declarado",
                           sessao=sessao, declarado=declarado)]
    return []


def _procedimento(guia, regras, regra, extra):
    codigo = guia["procedimento_codigo"]
    if not codigo:
        return [_pendencia("dado_invalido", "corrigir", "sem_procedimento")]
    proc = regras["procedimentos"].get(codigo)
    if proc is None:
        return [_pendencia("dado_invalido", "corrigir", "procedimento_desconhecido", codigo=codigo)]

    pendencias = []
    if codigo not in regra["procedimentos_cobertos"]:
        vira_particular = codigo in extra.get("nao_coberto_vira_particular", [])
        pendencias.append(_pendencia(
            "procedimento_nao_coberto", "nao_enviar", "nao_coberto",
            corrigir="nao_coberto_particular" if vira_particular else "nao_coberto",
            convenio=regra["nome"], descricao=proc["descricao"], codigo=codigo))

    # só reclama quando a descrição aponta para OUTRO procedimento. 'fisio neuro' abreviado não é erro.
    pela_descricao = achar_procedimento(regras, guia["procedimento_descricao"])
    if pela_descricao and pela_descricao["codigo"] != codigo:
        pendencias.append(_pendencia("dado_invalido", "conferir", "descricao_divergente",
                                     codigo=codigo, certa=proc["descricao"],
                                     lancada=guia["procedimento_descricao"]))

    if guia["_valor"] and abs(guia["_valor"] - proc["valor_referencia"]) > 0.005:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "valor_divergente",
                                     lancado=reais(guia["_valor"]),
                                     referencia=reais(proc["valor_referencia"])))
    return pendencias


def _profissional(guia, regras, regra, extra):
    """CREFITO para fisioterapia, CRM para consulta e infiltração. A regra escrita não proíbe o contrário,
    por isso é 'conferir' e não 'nao_enviar'."""
    codigo, registro = guia["procedimento_codigo"], guia["profissional_registro"].upper()
    exigido = regras["registro_por_procedimento"].get(codigo)
    if not (registro and exigido) or registro.startswith(exigido):
        return []
    extra_texto = ""
    if extra.get("nao_coberto_vira_particular") and registro.startswith("CRM"):
        extra_texto = " Se foi consulta médica, %s não cobre: faturar como particular." % regra["nome"]
    return [_pendencia("profissional_incompativel", "conferir", "profissional_incompativel",
                       descricao=regras["procedimentos"][codigo]["descricao"],
                       exigido=exigido, registro=guia["profissional_registro"], extra=extra_texto)]


def _prazo_de_envio(guia, regra, referencia, dias_de_alerta):
    """O prazo conta da data do atendimento. Devolve (pendencias, alertas, enviar_ate)."""
    if not guia["_atendimento"]:
        return [], [], None
    limite = guia["_atendimento"] + timedelta(days=regra["prazo_envio_dias"])
    if referencia and referencia > limite:
        return [_pendencia("prazo_de_envio", "nao_enviar", "prazo_vencido",
                           prazo=regra["prazo_envio_dias"], convenio=regra["nome"],
                           limite=_br(limite))], [], limite
    alertas = []
    if referencia and (limite - referencia).days <= dias_de_alerta:
        alertas.append(ALERTA["prazo_perto"].format(limite=_br(limite), dias=(limite - referencia).days,
                                                    convenio=regra["nome"]))
    return [], alertas, limite


def _observacao(guia, fatos, regras, regra, ja_tratou_autorizacao_nova):
    pendencias = []
    if fatos["particular"]:
        # Mesma ação de um procedimento que o convênio não cobre: a guia sai do lote e vira particular.
        pendencias.append(_pendencia("observacao_recepcao", "nao_enviar", "particular"))

    if fatos["procedimento_real"]:
        proc = regras["procedimentos"].get(guia["procedimento_codigo"], {})
        real = fatos["procedimento_real"]
        # O procedimento feito está na tabela? E este convênio cobre? Isso decide quem resolve:
        # coberto, a recepção troca o código; fora da tabela ou sem cobertura, o financeiro decide.
        feito = achar_procedimento(regras, real)
        if feito is None:
            passo, cobertura = "financeiro", " '%s' não está na tabela de procedimentos dos convênios: conferir cobertura antes de enviar." % real
        elif feito["codigo"] in regra["procedimentos_cobertos"]:
            passo, cobertura = "recepcao", ""
        else:
            passo, cobertura = "financeiro", " %s não cobre %s." % (regra["nome"], feito["descricao"].lower())
        pendencias.append(_pendencia("observacao_recepcao", "corrigir", "procedimento_real", passo=passo,
                                     real=real, descricao=proc.get("descricao", guia["procedimento_descricao"]),
                                     cobertura=cobertura))

    if fatos["remarcada"]:
        pendencias.append(_pendencia("observacao_recepcao", "conferir", "remarcada",
                                     atendimento=_br(guia["_atendimento"])))

    if fatos["por_telefone"] and guia["numero_autorizacao"]:
        pendencias.append(_pendencia("observacao_recepcao", "conferir", "verbal_com_numero",
                                     numero=guia["numero_autorizacao"]))

    if guia["_observacao_cortada"]:
        pendencias.append(_pendencia("observacao_recepcao", "conferir", "observacao_cortada"))

    if fatos["autorizacao_nova"] and not ja_tratou_autorizacao_nova:
        pendencias.append(_pendencia("observacao_recepcao", "conferir", "autorizacao_nova_solta"))

    if fatos["nao_reconhecida"]:
        pendencias.append(_pendencia("observacao_recepcao", "conferir", "observacao_nao_reconhecida",
                                     texto=guia["observacao_recepcao"]))
    return pendencias


def _duplicidade(contexto):
    if not contexto:
        return []
    if contexto["tipo"] == "exata":
        return [_pendencia("duplicidade", "nao_enviar", "duplicata_exata", outra=contexto["outra"])]
    if contexto["tipo"] == "mesma_sessao":
        return [_pendencia("duplicidade", "conferir", "mesma_sessao", outra=contexto["outra"])]
    return [_pendencia("duplicidade", "conferir", "duplicata_suspeita", outra=contexto["outra"])]


# ---------------------------------------------------------------- a decisão

def verificar_guia(bruta, regras, referencia=None, duplicidade=None,
                   registros_conhecidos=None, usar_ia=False, veio_do_sistema=True):
    """Confere uma guia.

    bruta                 dicionário com as colunas da guia, do jeito que vier
    referencia            em que dia a conferência acontece. Sem isso, usa a data de
                          lançamento da guia; sem ela, hoje.
    duplicidade           o que o lote sabe sobre esta guia (ver lote.py)
    registros_conhecidos  {profissional: registro}, para sugerir o registro que falta
    usar_ia               deixa a observação ser lida por IA quando as palavras-chave não bastam
    veio_do_sistema       guia exportada do sistema deveria ter data em AAAA-MM-DD, e se não tiver vale
                          um aviso. Guia digitada por gente em dia/mês/ano é o normal, sem aviso.
    """
    guia = normalizar_guia(bruta)
    referencia = referencia or guia["_lancamento"] or date.today()
    ano = (guia["_atendimento"] or referencia).year
    fatos = ler_observacao(guia["observacao_recepcao"], ano=ano, depois_de=guia["_atendimento"], usar_ia=usar_ia)

    pendencias, alertas, enviar_ate = [], (list(guia["avisos_de_leitura"]) if veio_do_sistema else []), None
    regra = achar_convenio(regras, guia["convenio"])

    if not guia["procedimento_codigo"] and guia["procedimento_descricao"]:
        pelo_nome = achar_procedimento(regras, guia["procedimento_descricao"])
        if pelo_nome:
            guia["procedimento_codigo"] = pelo_nome["codigo"]
            guia["procedimento_descricao"] = pelo_nome["descricao"]
            alertas.append(ALERTA["codigo_pela_descricao"].format(codigo=pelo_nome["codigo"]))

    if regra is None:
        pendencias.append(_pendencia("dado_invalido", "corrigir", "convenio_desconhecido",
                                     convenio=guia["convenio"]))
    else:
        guia["convenio"] = regra["nome"]             # 'vitalcard ' e 'VITALCARD' viram o nome oficial
        extra = regras["extras_convenio"].get(sem_acento(regra["nome"]), {})
        pendencias += _campos_obrigatorios(guia, regra, extra, fatos, referencia, registros_conhecidos or {})
        pendencias += _dados_minimos(guia)
        pendencias += _datas(guia, referencia)
        vencida = _validade_da_autorizacao(guia, fatos)
        pendencias += vencida
        pendencias += _limite_de_sessoes(guia, regra, extra)
        pendencias += _procedimento(guia, regras, regra, extra)
        pendencias += _profissional(guia, regras, regra, extra)
        do_prazo, alertas_prazo, enviar_ate = _prazo_de_envio(
            guia, regra, referencia, regras["dias_de_alerta_prazo"])
        pendencias += do_prazo
        alertas += alertas_prazo
        pendencias += _observacao(guia, fatos, regras, regra, ja_tratou_autorizacao_nova=bool(vencida))

        limite = regra["limite_sessoes_por_autorizacao"]
        if guia["_sessao"] == _limite_efetivo(guia, regra):
            alertas.append(ALERTA["ultima_sessao"])
        if guia["_limite_declarado"] and guia["_limite_declarado"] != limite:
            alertas.append(ALERTA["limite_diferente"].format(declarado=guia["_limite_declarado"],
                                                         convenio=regra["nome"], limite=limite))
        if guia["autorizacao_sessoes_limite"] and guia["_limite_declarado"] is None:
            alertas.append(ALERTA["limite_ilegivel"].format(valor=guia["autorizacao_sessoes_limite"]))
        if fatos["recibo_reembolso"]:
            alertas.append(ALERTA["recibo_reembolso"])
        maximo = regra["validade_maxima_autorizacao_dias"]
        if guia["_validade"] and guia["_atendimento"] and (guia["_validade"] - guia["_atendimento"]).days > maximo:
            alertas.append(ALERTA["validade_longa"].format(validade=_br(guia["_validade"]), maximo=maximo,
                                                           convenio=regra["nome"]))
        nova = fatos["nova_validade"]
        if nova and guia["_atendimento"] and (nova - guia["_atendimento"]).days > regra["validade_maxima_autorizacao_dias"]:
            alertas.append(ALERTA["nova_validade_longa"].format(
                nova=_br(nova), maximo=regra["validade_maxima_autorizacao_dias"], convenio=regra["nome"]))

    pendencias += _duplicidade(duplicidade)
    # Empate de gravidade: fica na frente o passo mais definitivo. Sessão acima do limite numa
    # infiltração que o convênio nem cobre é, antes de tudo, procedimento não coberto.
    passos = list(PROXIMOS_PASSOS)
    pendencias.sort(key=lambda p: (ORDEM_GRAVIDADE.index(p["gravidade"]), passos.index(p["proximo_passo"])))

    pendente = bool(pendencias)
    valor = guia["_valor"] or 0.0
    gravidade = pendencias[0]["gravidade"] if pendente else "ok"
    # Guia com dois problemas fica com o passo mais definitivo: sessão acima do limite num procedimento
    # que o convênio nem cobre não se resolve pedindo autorização.
    passo = min((p["proximo_passo"] for p in pendencias), key=passos.index) if pendente else ""
    return {
        "id_guia": guia["id_guia"],
        "decisao": "PENDENTE" if pendente else "OK",
        "gravidade": gravidade,
        "nome_da_decisao": DECISOES[gravidade],
        "o_que_significa": EXPLICACAO[gravidade],
        "proximo_passo": passo,
        "proximo_passo_nome": PROXIMOS_PASSOS.get(passo, ""),
        "aviso": {
            "para": AVISO_PARA[passo].format(unidade=guia["unidade"] or "sem unidade"),
            "texto": AVISO_TEXTO.format(guia=guia["id_guia"], unidade=guia["unidade"] or "sem unidade",
                                        convenio=guia["convenio"] or "sem convênio",
                                        problema=pendencias[0]["titulo"].lower(), acao=pendencias[0]["corrigir"]),
        } if pendente else None,
        # Quanto sobra da autorização depois deste atendimento. Serve para pedir a renovação
        # antes da próxima sessão, e não depois que a guia já nasceu errada.
        "folga_da_autorizacao": {
            "dias": (guia["_validade"] - guia["_atendimento"]).days if guia["_validade"] and guia["_atendimento"] else None,
            "sessoes": (_limite_efetivo(guia, regra) - guia["_sessao"]) if regra and guia["_sessao"] else None,
            "limite": _limite_efetivo(guia, regra) if regra else None,
        },
        "tipo_principal": pendencias[0]["tipo"] if pendente else "",
        "pendencias": pendencias,
        "alertas": alertas,
        "valor": valor,
        "valor_em_risco": valor if pendente else 0.0,
        "enviar_ate": enviar_ate.isoformat() if enviar_ate else "",
        "conferida_em": referencia.isoformat(),
        "observacao_lida_por": fatos["lido_por"],
        "guia": {campo: guia[campo] for campo in (
            "id_guia", "unidade", "data_atendimento", "paciente", "convenio", "carteirinha", "cid",
            "procedimento_codigo", "procedimento_descricao", "numero_autorizacao", "autorizacao_validade",
            "autorizacao_sessoes_limite", "sessao_numero_na_autorizacao", "profissional",
            "profissional_registro", "valor", "observacao_recepcao", "data_lancamento")},
    }
