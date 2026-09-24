"""O relatório de terça do Dr. Renato: quantas guias, quantas com problema, de que tipo, quanto em risco."""

from datetime import date

from .textos import GRAVIDADES, ORDEM_GRAVIDADE, PROXIMOS_PASSOS, TIPOS, reais as _reais


def _agrupar(resultados, chave_de):
    grupos = {}
    for r in resultados:
        nome = chave_de(r)
        g = grupos.setdefault(nome, {"guias": 0, "pendentes": 0, "em_risco": 0.0})
        g["guias"] += 1
        if r["decisao"] == "PENDENTE":
            g["pendentes"] += 1
            g["em_risco"] += r["valor_em_risco"]
    return grupos


def montar_relatorio(resultados, gerado_em=None):
    """Cada guia pendente conta uma vez só, no tipo da pendência mais grave. Assim os
    valores por tipo somam o total em risco, sem contar a mesma guia duas vezes."""
    pendentes = [r for r in resultados if r["decisao"] == "PENDENTE"]
    total_valor = sum(r["valor"] for r in resultados)
    em_risco = sum(r["valor_em_risco"] for r in resultados)

    por_tipo = {}
    for r in pendentes:
        t = por_tipo.setdefault(r["tipo_principal"], {"nome": TIPOS[r["tipo_principal"]], "guias": 0, "em_risco": 0.0, "ids": []})
        t["guias"] += 1
        t["em_risco"] += r["valor_em_risco"]
        t["ids"].append(r["id_guia"])

    # uma guia pode ter mais de um problema: aqui contam todos, para ninguém achar que sumiu algum
    ocorrencias = {}
    for r in pendentes:
        for p in r["pendencias"]:
            ocorrencias[p["tipo"]] = ocorrencias.get(p["tipo"], 0) + 1
    for tipo, t in por_tipo.items():
        t["ocorrencias"] = ocorrencias.get(tipo, 0)

    por_gravidade = {}
    for g in ORDEM_GRAVIDADE:
        do_nivel = [r for r in pendentes if r["gravidade"] == g]
        por_gravidade[g] = {"nome": GRAVIDADES[g], "guias": len(do_nivel),
                            "em_risco": sum(r["valor_em_risco"] for r in do_nivel)}

    # O mesmo valor retido, dividido pelo que precisa acontecer. Soma o total em risco.
    # Cópia de outra guia entra à parte: não é dinheiro a receber, a original é que vale.
    por_passo = {}
    for chave, nome in PROXIMOS_PASSOS.items():
        do_passo = [r for r in pendentes if r.get("proximo_passo") == chave]
        por_passo[chave] = {"nome": nome, "guias": len(do_passo), "e_receita": chave != "copia",
                            "em_risco": sum(r["valor_em_risco"] for r in do_passo),
                            "ids": [r["id_guia"] for r in do_passo]}

    return {
        "gerado_em": (gerado_em or date.today()).isoformat(),
        "verificadas": len(resultados),
        "ok": len(resultados) - len(pendentes),
        "pendentes": len(pendentes),
        "percentual_pendente": round(100.0 * len(pendentes) / len(resultados), 1) if resultados else 0.0,
        "valor_total": round(total_valor, 2),
        "valor_em_risco": round(em_risco, 2),
        "percentual_em_risco": round(100.0 * em_risco / total_valor, 1) if total_valor else 0.0,
        "por_tipo": sorted(por_tipo.values(), key=lambda t: -t["em_risco"]),
        "por_gravidade": por_gravidade,
        "por_proximo_passo": por_passo,
        "por_unidade": _agrupar(resultados, lambda r: r["guia"]["unidade"].strip().title() or "sem unidade"),
        "por_convenio": _agrupar(resultados, lambda r: r["guia"]["convenio"] or "sem convênio"),
        "guias_pendentes": [
            {"id_guia": r["id_guia"], "unidade": r["guia"]["unidade"], "convenio": r["guia"]["convenio"],
             "valor": r["valor"], "gravidade": r["gravidade"], "motivo": r["pendencias"][0]["motivo"],
             "corrigir": r["pendencias"][0]["corrigir"]}
            for r in pendentes],
    }


def relatorio_em_texto(rel):
    """Versão para colar no WhatsApp ou ler na reunião de terça."""
    linhas = [
        "Guias de convênio, conferência antes do envio",
        "Gerado em %s" % "/".join(reversed(rel["gerado_em"].split("-"))),
        "",
        "Verificadas: %d" % rel["verificadas"],
        "Podem enviar: %d" % rel["ok"],
        "Retidas antes do envio: %d de %d" % (rel["pendentes"], rel["verificadas"]),
        "Valor retido: %s de %s (%s%%)" % (
            _reais(rel["valor_em_risco"]), _reais(rel["valor_total"]),
            str(rel["percentual_em_risco"]).replace(".", ",")),
        "",
        "Por decisão",
    ]
    for g in ORDEM_GRAVIDADE:
        nivel = rel["por_gravidade"][g]
        linhas.append("- %s: %d guias, %s" % (nivel["nome"], nivel["guias"], _reais(nivel["em_risco"])))
    linhas += ["", "O que precisa acontecer"]
    for passo in sorted(rel["por_proximo_passo"].values(), key=lambda p: -p["em_risco"]):
        if passo["guias"]:
            linhas.append("- %s: %d guias, %s%s" % (passo["nome"], passo["guias"], _reais(passo["em_risco"]),
                                                   "" if passo["e_receita"] else " (não é dinheiro a receber)"))
    linhas += ["", "Por tipo de problema"]
    for t in rel["por_tipo"]:
        linhas.append("- %s: %d guias, %s" % (t["nome"], t["guias"], _reais(t["em_risco"])))
    linhas += ["", "Por unidade"]
    for nome, g in sorted(rel["por_unidade"].items()):
        linhas.append("- %s: %d de %d retidas, %s" % (nome, g["pendentes"], g["guias"], _reais(g["em_risco"])))
    linhas += ["", "Por convênio"]
    for nome, g in sorted(rel["por_convenio"].items()):
        linhas.append("- %s: %d de %d retidas, %s" % (nome, g["pendentes"], g["guias"], _reais(g["em_risco"])))
    return "\n".join(linhas)
