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
        self.assertEqual(RESULTADOS["G-2608-0004"]["gravidade"], "vai_glosar")

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
        self.assertEqual(fora["gravidade"], "vai_glosar")

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
