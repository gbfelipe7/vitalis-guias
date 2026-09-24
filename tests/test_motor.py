"""Testes do motor. Rodar da raiz do projeto:  python3 -m unittest -v

A primeira parte confere as 80 guias da prova, guia por guia nas que têm pegadinha.
A segunda simula guias novas chegando tortas, para provar que o motor aguenta.
"""

import unittest
from datetime import date

from motor import (carregar_guias, carregar_regras, consultar_regra, montar_relatorio,
                   verificar_guia, verificar_lote, verificar_nova)
from motor.entrada import interpretar_texto
from motor.observacao import ler_observacao

REGRAS = carregar_regras()
GUIAS = carregar_guias()
RESULTADOS = {r["id_guia"]: r for r in verificar_lote(GUIAS, REGRAS)}


def tipos(id_guia):
    return [p["tipo"] for p in RESULTADOS[id_guia]["pendencias"]]


class LoteDeAgosto(unittest.TestCase):

    def test_totais(self):
        rel = montar_relatorio(list(RESULTADOS.values()))
        self.assertEqual(rel["verificadas"], 80)
        self.assertEqual(rel["ok"] + rel["pendentes"], 80)
        self.assertAlmostEqual(sum(t["em_risco"] for t in rel["por_tipo"]), rel["valor_em_risco"])

    def test_autorizacao_vencida(self):
        vencidas = [i for i in RESULTADOS if "autorizacao_vencida" in tipos(i)]
        self.assertEqual(len(vencidas), 13)
        self.assertEqual(RESULTADOS["G-2608-0004"]["gravidade"], "nao_enviar")

    def test_autorizacao_no_ultimo_dia_vale(self):
        # validade 28/08, atendimento 28/08: a regra diz 'inclusive'
        self.assertEqual(RESULTADOS["G-2608-0001"]["decisao"], "OK")

    def test_vencida_mas_paciente_trouxe_nova(self):
        r = RESULTADOS["G-2608-0030"]
        self.assertEqual(r["gravidade"], "corrigir")
        self.assertIn("30/09/2026", r["pendencias"][0]["motivo"])

    def test_sessao_acima_do_limite(self):
        acima = sorted(i for i in RESULTADOS if "sessao_acima_do_limite" in tipos(i))
        self.assertEqual(acima, ["G-2608-0006", "G-2608-0008", "G-2608-0026",
                                 "G-2608-0056", "G-2608-0064", "G-2608-0077"])

    def test_ultima_sessao_passa_com_alerta(self):
        r = RESULTADOS["G-2608-0005"]          # sessão 10 de 10
        self.assertEqual(r["decisao"], "OK")
        self.assertTrue(any("última sessão" in a for a in r["alertas"]))

    def test_procedimento_nao_coberto(self):
        self.assertEqual(sorted(i for i in RESULTADOS if "procedimento_nao_coberto" in tipos(i)),
                         ["G-2608-0002", "G-2608-0006", "G-2608-0007", "G-2608-0024", "G-2608-0035"])
        self.assertIn("particular", RESULTADOS["G-2608-0002"]["pendencias"][0]["corrigir"])

    def test_cid_vazio_so_pesa_onde_o_convenio_exige(self):
        vazios = [g["id_guia"] for g in GUIAS if not g["cid"].strip()]
        cobrados = sorted(i for i in vazios if "campo_obrigatorio" in tipos(i))
        self.assertEqual(len(vazios), 13)
        self.assertEqual(cobrados, ["G-2608-0021", "G-2608-0056"])

    def test_registro_vazio_vem_com_sugestao(self):
        self.assertIn("CRM-SP 84512", RESULTADOS["G-2608-0013"]["pendencias"][0]["corrigir"])

    def test_autorizacao_por_telefone_no_convenio_que_aceita(self):
        r = RESULTADOS["G-2608-0041"]
        self.assertEqual(r["gravidade"], "corrigir")
        self.assertIn("27/08/2026", r["pendencias"][0]["corrigir"])   # 20/08 mais 5 dias úteis

    def test_sem_autorizacao_e_sem_protocolo(self):
        for i in ("G-2608-0051", "G-2608-0061", "G-2608-0063"):
            self.assertIn("sem_autorizacao", tipos(i))

    def test_observacao_que_so_gente_entende(self):
        self.assertIn("particular", RESULTADOS["G-2608-0039"]["pendencias"][0]["motivo"])
        # quer particular e convênio que não cobre pedem a mesma ação, então caem na mesma decisão
        self.assertEqual(RESULTADOS["G-2608-0039"]["gravidade"], "nao_enviar")
        self.assertEqual(RESULTADOS["G-2608-0039"]["gravidade"], RESULTADOS["G-2608-0002"]["gravidade"])
        self.assertEqual(RESULTADOS["G-2608-0039"]["nome_da_decisao"], "Não enviar assim")
        self.assertIn("drenagem", RESULTADOS["G-2608-0069"]["pendencias"][0]["motivo"])
        self.assertEqual(RESULTADOS["G-2608-0034"]["gravidade"], "conferir")

    def test_observacao_comum_nao_segura_a_guia(self):
        for g in GUIAS:
            if "atrasado" in g["observacao_recepcao"] or "recibo" in g["observacao_recepcao"]:
                self.assertNotIn("observacao_recepcao", tipos(g["id_guia"]))

    def test_duplicata_so_aparece_com_a_data_normalizada(self):
        # G-0027 tem a data como 26/08/2026 e G-0057 como 2026-08-26
        self.assertEqual(RESULTADOS["G-2608-0027"]["decisao"], "OK")
        self.assertIn("G-2608-0027", RESULTADOS["G-2608-0057"]["pendencias"][0]["motivo"])
        self.assertIn("duplicidade", tipos("G-2608-0076"))

    def test_mesmo_paciente_em_duas_unidades_fica_para_conferir(self):
        for i in ("G-2608-0017", "G-2608-0060"):
            self.assertEqual(RESULTADOS[i]["gravidade"], "conferir")

    def test_medico_em_procedimento_de_fisioterapia(self):
        for i in ("G-2608-0045", "G-2608-0074"):
            self.assertIn("profissional_incompativel", tipos(i))


class GuiaNova(unittest.TestCase):

    BOA = {"id_guia": "T-1", "unidade": "Sul", "data_atendimento": "2026-09-01", "paciente": "P-9001",
           "convenio": "Vitalcard", "carteirinha": "111222333", "cid": "M54.5",
           "procedimento_codigo": "50000470", "numero_autorizacao": "AUT1", "autorizacao_validade": "2026-09-20",
           "autorizacao_sessoes_limite": "10", "sessao_numero_na_autorizacao": "2",
           "profissional": "Bruno Castanho", "profissional_registro": "CREFITO-3 204411-F",
           "valor": "62.00", "data_lancamento": "2026-09-02"}

    def nova(self, **troca):
        return verificar_guia(dict(self.BOA, **troca), REGRAS)

    def test_guia_boa_passa(self):
        self.assertEqual(self.nova()["decisao"], "OK")

    def test_aceita_data_valor_e_convenio_como_a_recepcao_digita(self):
        r = self.nova(data_atendimento="01/09/2026", valor="R$ 62,00", convenio="vitalcard ")
        self.assertEqual(r["decisao"], "OK")

    def test_guia_vazia_nao_quebra(self):
        self.assertEqual(verificar_guia({}, REGRAS)["decisao"], "PENDENTE")

    def test_campo_com_lixo_nao_quebra(self):
        r = self.nova(sessao_numero_na_autorizacao="sétima", valor="sessenta", data_atendimento="ontem")
        self.assertEqual(r["decisao"], "PENDENTE")

    def test_convenio_que_nao_existe(self):
        self.assertIn("não está nas regras", self.nova(convenio="Unimed")["pendencias"][0]["motivo"])

    def test_valor_diferente_da_referencia(self):
        self.assertIn("dado_invalido", [p["tipo"] for p in self.nova(valor="80")["pendencias"]])

    def test_prazo_de_envio_conta_do_atendimento(self):
        no_prazo = verificar_guia(self.BOA, REGRAS, referencia=date(2026, 10, 1))   # dia 30
        fora = verificar_guia(self.BOA, REGRAS, referencia=date(2026, 10, 2))       # dia 31
        self.assertEqual(no_prazo["decisao"], "OK")
        self.assertIn("prazo_de_envio", [p["tipo"] for p in fora["pendencias"]])

    def test_protocolo_por_telefone_vence(self):
        base = dict(self.BOA, convenio="Saúde Interior", numero_autorizacao="",
                    observacao_recepcao="Autorizado por telefone, protocolo 998877.")
        dentro = verificar_guia(base, REGRAS, referencia=date(2026, 9, 8))    # 5º dia útil
        fora = verificar_guia(base, REGRAS, referencia=date(2026, 9, 9))
        self.assertEqual(dentro["gravidade"], "corrigir")
        self.assertEqual(fora["gravidade"], "nao_enviar")

    def test_protocolo_por_telefone_onde_nao_vale(self):
        r = self.nova(numero_autorizacao="", observacao_recepcao="Autorizado por telefone, protocolo 998877.")
        self.assertIn("não aceita autorização verbal", r["pendencias"][0]["motivo"])

    def test_guia_nova_repetida_do_lote(self):
        r = verificar_nova(dict(GUIAS[0], id_guia="G-NOVA"), GUIAS, REGRAS, usar_ia=False)
        self.assertIn("duplicidade", [p["tipo"] for p in r["pendencias"]])

    def test_observacao_desconhecida_segura_sem_ia(self):
        r = self.nova(observacao_recepcao="Mãe do paciente disse que o plano mudou semana passada.")
        self.assertEqual(r["gravidade"], "conferir")


class EntradaEMais(unittest.TestCase):

    def test_consultar_regra(self):
        self.assertFalse(consultar_regra(REGRAS, "plano bem", "consulta")["coberto"])
        self.assertTrue(consultar_regra(REGRAS, "Saúde Interior", "40201015")["coberto"])
        self.assertFalse(consultar_regra(REGRAS, "Unimed", "50000470")["encontrado"])

    def test_texto_colado_em_campos(self):
        lido = interpretar_texto("Convênio: Plano Bem\nData: 02/09/2026\nCódigo: 20103301\nSessão: 1 de 12\nCRM: CRM-SP 1",
                                 REGRAS, usar_ia=False)
        self.assertEqual(lido["campos"]["autorizacao_sessoes_limite"], "12")
        self.assertEqual(lido["faltando"], [])

    def test_texto_corrido_sem_ia(self):
        lido = interpretar_texto("paciente P-3003 do vitalcard, fisio neurofuncional dia 10/09/2026, aut AUT700800 "
                                 "val 25/09/2026, sessão 11 de 10. obs: quer faturar como particular", REGRAS, usar_ia=False)
        self.assertEqual(lido["campos"]["procedimento_codigo"], "50000560")
        self.assertEqual(lido["campos"]["numero_autorizacao"], "AUT700800")

    def test_observacao_vira_fato(self):
        self.assertEqual(ler_observacao("Autorizado por telefone, protocolo 771203, aguardando número.")["protocolo_verbal"], "771203")
        self.assertFalse(ler_observacao("Paciente chegou 10 min atrasado.")["nao_reconhecida"])


if __name__ == "__main__":
    unittest.main()


class AchadosDaAuditoria(unittest.TestCase):
    """Cada teste aqui nasceu de um furo que a auditoria achou. Se voltar a quebrar, o furo voltou."""

    BOA = GuiaNova.BOA

    def nova(self, **troca):
        return verificar_guia(dict(self.BOA, **troca), REGRAS)

    def tipos(self, resultado):
        return [p["tipo"] for p in resultado["pendencias"]]

    # ----- duplicidade
    def test_repetida_do_lote_sem_data_de_lancamento(self):
        sem_lancamento = {k: v for k, v in GUIAS[0].items() if k != "data_lancamento"}
        r = verificar_nova(dict(sem_lancamento, id_guia="X-1"), GUIAS, REGRAS, usar_ia=False)
        self.assertIn("duplicidade", self.tipos(r))

    def test_terceira_copia_tambem_e_duplicata(self):
        from motor.lote import mapear_duplicidades
        copia = dict(self.BOA)
        mapa = mapear_duplicidades([dict(copia, id_guia="A"), dict(copia, id_guia="B"), dict(copia, id_guia="C")])
        self.assertEqual([m and m["tipo"] for m in mapa], [None, "exata", "exata"])

    def test_duas_novas_iguais_no_relatorio(self):
        from web.rotas import rota_relatorio
        nova = dict(self.BOA, id_guia="")
        _, corpo = rota_relatorio([nova, nova])
        self.assertEqual(corpo["relatorio"]["verificadas"], 82)
        self.assertGreaterEqual(corpo["relatorio"]["pendentes"], 40)      # a segunda é repetida da primeira

    # ----- observação
    def test_frase_comum_nao_esconde_o_resto(self):
        for obs in ("Paciente chegou atrasado e a sessão foi cancelada.",
                    "Sessão não realizada, paciente faltou. Pediu recibo da anterior.",
                    "Protocolo 771203 por telefone. Paciente avisou que cancelou o plano semana passada."):
            self.assertEqual(self.nova(observacao_recepcao=obs)["decisao"], "PENDENTE", obs)

    def test_pagou_particular_segura_mesmo_com_recibo(self):
        self.assertEqual(self.nova(observacao_recepcao="Paciente pagou particular, pediu recibo.")["decisao"], "PENDENTE")

    def test_negacao_nao_vira_fato(self):
        vencida = dict(self.BOA, autorizacao_validade="2026-08-20")
        for obs in ("Paciente NÃO trouxe autorização nova.", "Precisa pedir nova autorização ao convênio.",
                    "Convênio negou a nova autorização."):
            r = verificar_guia(dict(vencida, observacao_recepcao=obs), REGRAS)
            self.assertEqual(r["gravidade"], "nao_enviar", obs)

    def test_autorizacao_nova_que_tambem_nao_cobre(self):
        r = self.nova(autorizacao_validade="2026-08-20",
                      observacao_recepcao="Paciente trouxe autorização nova, validade 25/08.")
        self.assertEqual(r["gravidade"], "nao_enviar")

    def test_silencio_da_ia_nao_libera_guia(self):
        from unittest import mock
        calada = {"particular": False, "protocolo_verbal": "", "autorizacao_nova": False,
                  "nova_validade": "", "procedimento_real": "", "remarcada": False}
        with mock.patch("motor.observacao.perguntar_json", return_value=calada):
            r = verificar_guia(dict(self.BOA, observacao_recepcao="A carteirinha apresentada é do marido, não dela."),
                               REGRAS, usar_ia=True)
        self.assertEqual(r["decisao"], "PENDENTE")

    def test_ia_com_tipo_errado_nao_quebra(self):
        from unittest import mock
        with mock.patch("motor.observacao.perguntar_json", return_value={"particular": "sim", "protocolo_verbal": 12}):
            r = verificar_guia(dict(self.BOA, observacao_recepcao="Texto que ninguém conhece."), REGRAS, usar_ia=True)
        self.assertEqual(r["decisao"], "PENDENTE")

    def test_recibo_para_reembolso_avisa_sem_segurar(self):
        r = self.nova(observacao_recepcao="Pediu recibo para reembolso do plano.")
        self.assertEqual(r["decisao"], "OK")
        self.assertTrue(any("reembolso" in a for a in r["alertas"]))

    # ----- dados mínimos e números tortos
    def test_sessao_torta_nao_passa_calada(self):
        self.assertIn("sessao_acima_do_limite", self.tipos(self.nova(sessao_numero_na_autorizacao="11ª")))
        for torta in ("", "sétima", "0", "-3", "1e999", "inf"):
            self.assertEqual(self.nova(sessao_numero_na_autorizacao=torta)["decisao"], "PENDENTE", torta)

    def test_valor_torto_nao_passa_calado(self):
        for torto in ("", "nan", "inf", "-5", "sessenta", "0"):
            r = self.nova(valor=torto)
            self.assertEqual(r["decisao"], "PENDENTE", torto)
            self.assertEqual(r["valor_em_risco"], r["valor_em_risco"])       # não é NaN

    def test_guia_sem_paciente(self):
        self.assertEqual(self.nova(paciente="")["decisao"], "PENDENTE")

    def test_sessao_acima_do_que_a_guia_declara(self):
        r = self.nova(sessao_numero_na_autorizacao="7", autorizacao_sessoes_limite="5")
        self.assertEqual(r["gravidade"], "conferir")

    def test_valores_que_nao_sao_texto(self):
        from web.rotas import rota_verificar
        status, corpo = rota_verificar({"guia": {"convenio": 12, "valor": 62.0, "cid": ["M54.5"],
                                                 "paciente": {"a": 1}, "sessao_numero_na_autorizacao": True}})
        self.assertEqual(status, 200)
        self.assertEqual(corpo["resultado"]["decisao"], "PENDENTE")
        self.assertEqual(rota_verificar({"texto": ["lista"]})[0], 400)

    def test_datas_absurdas(self):
        for absurda in ("31/02/2026", "00/00/0000", "2026-13-40", "9999-12-31"):
            self.assertEqual(self.nova(data_atendimento=absurda)["decisao"], "PENDENTE", absurda)

    # ----- data de referência
    def test_guia_nova_e_conferida_hoje(self):
        velha = dict(self.BOA, data_atendimento="2026-06-01", autorizacao_validade="2026-06-20",
                     data_lancamento="2026-06-02")
        r = verificar_nova(velha, GUIAS, REGRAS, usar_ia=False, referencia=date(2026, 9, 21))
        self.assertIn("prazo_de_envio", self.tipos(r))

    def test_atendimento_no_futuro(self):
        r = verificar_nova(dict(self.BOA, data_atendimento="2026-12-01", autorizacao_validade="2026-12-20"),
                           GUIAS, REGRAS, usar_ia=False, referencia=date(2026, 9, 21))
        self.assertEqual(r["decisao"], "PENDENTE")

    # ----- entrada por texto corrido
    TEXTO = ("Paciente P-2003 do Vitalcard, fisio neuro dia 04/09/2026 com o Felipe Andrade, aut AUT700800 val 25/08/2026, "
             "sessão 14 de 10, cid G81.9, carteirinha 123456789, R$ 70,00.")

    def test_no_texto_corrido_vale_o_que_esta_escrito(self):
        from unittest import mock
        da_ia = {"convenio": "Vitalcard", "autorizacao_validade": "2026-09-25", "sessao_numero_na_autorizacao": "4",
                 "profissional": "Felipe Andrade"}
        with mock.patch("motor.entrada.perguntar_json", return_value=da_ia):
            lido = interpretar_texto(self.TEXTO + " CORREÇÃO: a validade certa é 2026-09-25 e a sessão é 4.", REGRAS)
        self.assertEqual(lido["campos"]["autorizacao_validade"], "25/08/2026")
        self.assertEqual(lido["campos"]["sessao_numero_na_autorizacao"], "14")
        self.assertEqual(lido["campos"]["profissional"], "Felipe Andrade")       # o que só a IA pega continua valendo
        self.assertTrue(any("Vale o que está escrito" in a for a in lido["avisos"]))

    def test_fisio_neuro_acha_o_procedimento(self):
        lido = interpretar_texto(self.TEXTO, REGRAS, usar_ia=False)
        self.assertEqual(lido["campos"]["procedimento_codigo"], "50000560")

    def test_data_sem_ano_e_do_ano_corrente(self):
        from motor.normalizar import ler_data
        self.assertEqual(ler_data("04/09", ano_padrao=2026), date(2026, 9, 4))

    def test_arquivo_salvo_pelo_excel(self):
        import os, tempfile
        with open(os.path.join(os.path.dirname(__file__), "..", "dados", "guias.csv"), encoding="utf-8") as original:
            conteudo = original.read()
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig") as com_bom:
            com_bom.write(conteudo)
        try:
            self.assertEqual(carregar_guias(com_bom.name)[0]["id_guia"], "G-2608-0001")
        finally:
            os.remove(com_bom.name)


class SegundaRodadaDeAtaque(unittest.TestCase):
    """A segunda auditoria atacou o código já corrigido. Estes são os furos que ela ainda achou."""

    BOA = GuiaNova.BOA

    def nova(self, **troca):
        return verificar_guia(dict(self.BOA, **troca), REGRAS)

    def test_frase_comum_colada_a_informacao_grave(self):
        for obs in ("Paciente chegou atrasado pois a autorização foi negada", "Chegou atrasado: autorização negada pelo convênio",
                    "Confirmado pelo WhatsApp que o plano foi cancelado", "Pediu recibo porque pagou a sessão",
                    "Pediu recibo pois vai pagar particular sem usar o plano", "Guia anexado ao prontuário de outro paciente"):
            self.assertEqual(self.nova(observacao_recepcao=obs)["decisao"], "PENDENTE", obs)

    def test_frase_comum_sozinha_continua_passando(self):
        for obs in ("Paciente chegou 10 min atrasado.", "Chegou atrasado.", "Confirmado pelo WhatsApp na véspera.",
                    "Trouxe exame novo, anexado ao prontuário.", "Pediu recibo para reembolso do plano."):
            self.assertEqual(self.nova(observacao_recepcao=obs)["decisao"], "OK", obs)

    def test_todo_fato_vira_pendencia(self):
        # a guia TEM número de autorização e a recepção fala em autorização por telefone
        for obs in ("Autorizado por telefone, protocolo 771203, aguardando número.",
                    "Protocolo 771203 anotado mas o convênio cancelou depois"):
            self.assertEqual(self.nova(observacao_recepcao=obs)["decisao"], "PENDENTE", obs)

    def test_a_ia_so_endurece(self):
        from unittest import mock
        # modelo manipulado tenta amolecer: devolve fatos que rebaixariam a gravidade. Eles nem são lidos.
        amolece = {"particular": False, "procedimento_real": "", "remarcada": False,
                   "protocolo_verbal": "771203", "autorizacao_nova": True, "nova_validade": "2026-12-30"}
        with mock.patch("motor.observacao.perguntar_json", return_value=amolece):
            vencida = verificar_guia(dict(self.BOA, autorizacao_validade="2026-08-20",
                                          observacao_recepcao="Texto que as palavras-chave não conhecem."), REGRAS, usar_ia=True)
            com_numero = verificar_guia(dict(self.BOA, observacao_recepcao="A carteirinha é do marido."), REGRAS, usar_ia=True)
        self.assertEqual(vencida["gravidade"], "nao_enviar")
        self.assertEqual(com_numero["decisao"], "PENDENTE")
        # e quando a IA acha algo que endurece, entra
        with mock.patch("motor.observacao.perguntar_json", return_value={"particular": True, "procedimento_real": "", "remarcada": False}):
            r = verificar_guia(dict(self.BOA, observacao_recepcao="Vai acertar direto no caixa, do bolso dele."), REGRAS, usar_ia=True)
        self.assertIn("particular", " ".join(p["motivo"] for p in r["pendencias"]))

    def test_marcador_de_vazio_conta_como_vazio(self):
        for marcador in ("aguardando", "-", "N/A", "?", "pendente"):
            self.assertIn("sem_autorizacao", [p["tipo"] for p in self.nova(numero_autorizacao=marcador)["pendencias"]], marcador)

    def test_numero_com_lixo_no_meio(self):
        for torta in ("1 1", "1O", "2 (na verdade 12)"):
            self.assertEqual(self.nova(sessao_numero_na_autorizacao=torta)["decisao"], "PENDENTE", torta)
        for torto in ("6_2", "1e308", "62.000"):
            self.assertEqual(self.nova(valor=torto)["decisao"], "PENDENTE", torto)

    def test_validade_sem_ano_usa_o_ano_do_atendimento(self):
        r = verificar_guia(dict(self.BOA, data_atendimento="2025-12-20", autorizacao_validade="15/12",
                                data_lancamento="2025-12-21"), REGRAS)
        self.assertIn("autorizacao_vencida", [p["tipo"] for p in r["pendencias"]])

    def test_validade_29_02_na_observacao_nao_derruba(self):
        r = self.nova(autorizacao_validade="2026-08-20", observacao_recepcao="Paciente trouxe autorização nova, validade 29/02.")
        self.assertEqual(r["decisao"], "PENDENTE")

    def test_mesma_autorizacao_e_mesma_sessao_em_outra_data(self):
        copia = dict(GUIAS[0], id_guia="C-1", data_atendimento="2026-08-29", procedimento_codigo="")
        r = verificar_nova(copia, GUIAS, REGRAS, usar_ia=False)
        self.assertIn("duplicidade", [p["tipo"] for p in r["pendencias"]])

    def test_guia_reconferida_nao_conta_duas_vezes(self):
        from web.rotas import rota_relatorio
        _, corpo = rota_relatorio([dict(GUIAS[3], id_guia="g-2608-0004")])
        self.assertEqual(corpo["relatorio"]["verificadas"], 80)

    def test_comentario_sem_rotulo_nao_e_jogado_fora(self):
        lido = interpretar_texto("Convênio: Vitalcard\nData: 02/09/2026\nCódigo: 50000470\nSessão: 1 de 10\n"
                                 "Paciente disse que o plano foi cancelado", REGRAS, usar_ia=False)
        self.assertIn("plano foi cancelado", lido["campos"]["observacao_recepcao"])
        corrido = interpretar_texto("P-1 do Vitalcard, fisio neuro dia 04/09/2026, aut AUT700800 val 25/09/2026, "
                                    "sessão 4 de 10. A mãe avisou que ele quer faturar como particular.", REGRAS, usar_ia=False)
        self.assertIn("particular", corrido["campos"]["observacao_recepcao"])

    def test_texto_corrido_pede_confirmacao(self):
        from web.rotas import rota_verificar
        status, corpo = rota_verificar({"texto": "P-1 do Vitalcard, fisio neuro dia 04/09/2026, aut AUT700800 "
                                                 "val 25/09/2026, sessão 4 de 10, cid G81.9"})
        self.assertEqual(status, 200)
        self.assertTrue(corpo["confirmar"])
        self.assertNotIn("resultado", corpo)

    def test_ia_nao_inventa_campo(self):
        from unittest import mock
        inventa = {"numero_autorizacao": "AUT999999", "convenio": "Saúde Interior", "cid": "M54.5", "profissional": "Dr. Fulano"}
        with mock.patch("motor.entrada.perguntar_json", return_value=inventa):
            lido = interpretar_texto("P-1 do Vitalcard, fisio neuro dia 04/09/2026, sessão 4 de 10", REGRAS)
        self.assertNotIn("numero_autorizacao", lido["campos"])
        self.assertEqual(lido["campos"]["convenio"], "Vitalcard")
        self.assertNotIn("profissional", lido["campos"])

    def test_a_ordem_das_pendencias_e_fixa(self):
        # G-0006 tem dois problemas de mesma gravidade: o relatório conta a guia no primeiro
        # empate de gravidade: vem na frente o passo mais definitivo (o Vitalcard nem cobre infiltração)
        self.assertEqual(RESULTADOS["G-2608-0006"]["tipo_principal"], "procedimento_nao_coberto")
        self.assertEqual(RESULTADOS["G-2608-0056"]["tipo_principal"], "sessao_acima_do_limite")



class NomesEProximoPasso(unittest.TestCase):
    """Os nomes que a pessoa lê e a divisão do valor segurado pelo que precisa acontecer."""

    def test_nomes_das_decisoes(self):
        self.assertEqual(RESULTADOS["G-2608-0001"]["nome_da_decisao"], "Pode enviar")
        self.assertEqual(RESULTADOS["G-2608-0004"]["nome_da_decisao"], "Não enviar assim")
        self.assertEqual(RESULTADOS["G-2608-0021"]["nome_da_decisao"], "Corrigir antes de enviar")
        self.assertEqual(RESULTADOS["G-2608-0045"]["nome_da_decisao"], "Conferir antes de enviar")

    def test_valor_por_proximo_passo_soma_o_total(self):
        rel = montar_relatorio(list(RESULTADOS.values()))
        passos = rel["por_proximo_passo"]
        self.assertAlmostEqual(sum(p["em_risco"] for p in passos.values()), rel["valor_em_risco"])
        self.assertEqual(sum(p["guias"] for p in passos.values()), rel["pendentes"])
        self.assertEqual(passos["convenio"]["em_risco"], 1378.0)
        self.assertEqual(passos["recepcao"]["em_risco"], 292.0)
        self.assertEqual(passos["financeiro"]["em_risco"], 370.0)
        self.assertEqual(sorted(passos["copia"]["ids"]), ["G-2608-0057", "G-2608-0076"])
        self.assertFalse(passos["copia"]["e_receita"])

    def test_passo_mais_definitivo_vence(self):
        # sessão acima do limite numa infiltração que o Vitalcard nem cobre: pedir autorização não resolve
        self.assertEqual(RESULTADOS["G-2608-0006"]["proximo_passo"], "financeiro")
        # autorização vencida, mas o paciente trouxe uma nova: é a recepção que lança
        self.assertEqual(RESULTADOS["G-2608-0030"]["proximo_passo"], "recepcao")
        self.assertEqual(RESULTADOS["G-2608-0039"]["proximo_passo"], "particular")
        # 'drenagem linfática' não está na tabela de nenhum convênio: trocar o código não resolve
        self.assertEqual(RESULTADOS["G-2608-0069"]["proximo_passo"], "financeiro")
        self.assertEqual(RESULTADOS["G-2608-0001"]["proximo_passo"], "")


class TerceiraRodada(unittest.TestCase):
    """Achados da verificação da página nova e das mudanças do motor."""

    def _guia(self, **mudar):
        base = {"convenio": "Vitalcard", "unidade": "Sul", "paciente": "P-9", "data_atendimento": "2026-09-21",
                "procedimento_codigo": "50000470", "numero_autorizacao": "AUT123456", "autorizacao_validade": "2026-10-10",
                "sessao_numero_na_autorizacao": "3", "carteirinha": "123456789", "cid": "M54.5",
                "profissional_registro": "CREFITO-3 204411-F", "valor": "62.00"}
        base.update(mudar)
        return base

    def test_mesma_guia_lancada_duas_vezes_na_sessao(self):
        from web.rotas import rota_verificar
        primeira = self._guia(id_guia="G-NOVA-1")
        _, corpo = rota_verificar({"guia": self._guia(id_guia="G-NOVA-2"), "rascunho": True, "anteriores": [primeira]})
        self.assertEqual(corpo["resultado"]["gravidade"], "nao_enviar")
        self.assertEqual(corpo["resultado"]["proximo_passo"], "copia")

    def test_so_ler_nao_confere(self):
        from web.rotas import rota_verificar
        _, corpo = rota_verificar({"texto": "Convênio: Vitalcard\nProcedimento: 50000470\nData: 21-09-2026\nPaciente: P-1",
                                   "so_ler": True, "rascunho": True})
        self.assertTrue(corpo["confirmar"])
        self.assertEqual(corpo["entrada"]["campos"]["procedimento_codigo"], "50000470")
        self.assertEqual(corpo["entrada"]["campos"]["data_atendimento"], "2026-09-21")

    def test_avisos_de_leitura_voltam_para_a_pagina(self):
        from web.rotas import rota_verificar
        _, corpo = rota_verificar({"texto": "Convênio: Vitalcard\nConvênio: Plano Bem\nCódigo: 50000470\nData: 21/09/2026\nPaciente: P-1\nSessão: 1 de 10",
                                   "rascunho": True})
        self.assertTrue(corpo["entrada"]["avisos"])

    def test_limite_declarado_menor_entra_na_folga(self):
        r = verificar_nova(self._guia(sessao_numero_na_autorizacao="5", autorizacao_sessoes_limite="5"), [], REGRAS,
                           usar_ia=False, referencia=date(2026, 9, 22))
        self.assertEqual(r["folga_da_autorizacao"]["sessoes"], 0)

    def test_validade_longa_demais_gera_aviso(self):
        r = verificar_nova(self._guia(autorizacao_validade="2062-10-10"), [], REGRAS, usar_ia=False,
                           referencia=date(2026, 9, 22))
        self.assertTrue(any("Conferir se o ano está certo" in a for a in r["alertas"]))

    def test_procedimento_real_coberto_e_com_a_recepcao(self):
        r = verificar_nova(self._guia(observacao_recepcao="O procedimento realizado foi fisioterapia neurofuncional."),
                           [], REGRAS, usar_ia=False, referencia=date(2026, 9, 22))
        self.assertEqual(r["proximo_passo"], "recepcao")

    def test_valor_em_reais_no_formato_da_clinica(self):
        r = verificar_nova(self._guia(valor="1200.50"), [], REGRAS, usar_ia=False, referencia=date(2026, 9, 22))
        self.assertTrue(any("R$ 1.200,50" in p["motivo"] for p in r["pendencias"]))

    def test_aviso_vai_para_quem_resolve_sem_dado_do_paciente(self):
        r = RESULTADOS["G-2608-0021"]
        self.assertEqual(r["aviso"]["para"], "Recepção da unidade Norte")
        self.assertNotIn(r["guia"]["paciente"], r["aviso"]["texto"])
        self.assertIsNone(RESULTADOS["G-2608-0001"]["aviso"])
        self.assertEqual(RESULTADOS["G-2608-0045"]["aviso"]["para"], "Carla")

    def test_tabela_da_pagina_bate_com_o_codigo(self):
        # a tela Como funciona mostra a decisão de cada regra: ela tem que ser a mesma do motor
        import re, os
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        codigo = open(os.path.join(raiz, "motor", "verificar.py"), encoding="utf-8").read()
        pagina = open(os.path.join(raiz, "public", "index.html"), encoding="utf-8").read()
        do_motor = {chave: grav for _, grav, chave in re.findall(r'_pendencia\(\s*"(\w+)",\s*"(\w+)",\s*"(\w+)"', codigo)}
        bloco = re.search(r"const GRAV_DA_REGRA = \{(.*?)\};", pagina, re.S).group(1)
        da_pagina = dict(re.findall(r"(\w+): '(\w+)'", bloco))
        self.assertEqual(do_motor, da_pagina)
