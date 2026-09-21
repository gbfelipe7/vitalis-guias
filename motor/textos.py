"""Tudo que a recepção, a Carla e o Dr. Renato leem sai daqui.

Os textos ficam separados do motor de propósito: quem conhece a clínica consegue
mudar uma frase sem mexer em regra nenhuma. As chaves entre chaves {assim} são
preenchidas pelo motor.
"""

# Nome que aparece no relatório para cada tipo de problema.
TIPOS = {
    "autorizacao_vencida": "Autorização vencida",
    "sem_autorizacao": "Sem número de autorização",
    "sessao_acima_do_limite": "Sessão acima do limite da autorização",
    "procedimento_nao_coberto": "Procedimento que o convênio não cobre",
    "campo_obrigatorio": "Campo obrigatório vazio",
    "profissional_incompativel": "Profissional não combina com o procedimento",
    "duplicidade": "Guia duplicada ou repetida",
    "observacao_recepcao": "A observação da recepção muda a guia",
    "prazo_de_envio": "Prazo de envio vencido",
    "dado_invalido": "Dado inválido ou divergente",
}

# Três níveis, do mais grave para o mais leve.
GRAVIDADES = {
    "vai_glosar": "Vai glosar se for enviada assim",
    "corrigir": "A recepção corrige e envia",
    "conferir": "Precisa de alguém olhar",
}
ORDEM_GRAVIDADE = ["vai_glosar", "corrigir", "conferir"]

MOTIVO = {
    "convenio_desconhecido": "O convênio '{convenio}' não está nas regras.",
    "campo_vazio": "{convenio} exige {campo} e o campo está vazio.",
    "data_ilegivel": "Não deu para entender a data em {campo}: '{valor}'.",
    "sem_data_atendimento": "A guia está sem a data do atendimento. Sem ela não dá para conferir validade nem prazo.",
    "sem_procedimento": "A guia está sem o procedimento.",
    "autorizacao_vencida": "A autorização venceu em {validade}, {dias} dia(s) antes do atendimento de {atendimento}.",
    "autorizacao_vencida_com_nova": "A autorização lançada venceu em {validade}, mas a recepção anotou que o paciente trouxe uma nova{nova_validade}.",
    "sem_autorizacao": "A guia está sem número de autorização.",
    "sem_autorizacao_verbal_ok": "Sem número de autorização, mas autorizada por telefone com o protocolo {protocolo}. {convenio} aceita isso por {dias_uteis} dias úteis.",
    "sem_autorizacao_verbal_vencida": "Autorizada por telefone com o protocolo {protocolo}, mas o prazo de {dias_uteis} dias úteis do {convenio} acabou em {limite}.",
    "sem_autorizacao_verbal_nao_aceita": "Autorizada por telefone com o protocolo {protocolo}, mas {convenio} não aceita autorização verbal.",
    "sessao_acima": "É a sessão {sessao} de uma autorização que cobre {limite} no {convenio}.",
    "procedimento_desconhecido": "O código '{codigo}' não está na tabela de procedimentos.",
    "nao_coberto": "{convenio} não cobre {descricao} ({codigo}).",
    "descricao_divergente": "O código {codigo} é '{certa}', mas a guia diz '{lancada}'.",
    "valor_divergente": "O valor lançado é R$ {lancado} e a referência do procedimento é R$ {referencia}.",
    "profissional_incompativel": "{descricao} pede registro {exigido}, mas a guia tem {registro}.",
    "prazo_vencido": "O prazo de {prazo} dias do {convenio} para enviar venceu em {limite}.",
    "lancada_antes": "A guia foi lançada em {lancamento}, antes do atendimento de {atendimento}.",
    "particular": "A recepção anotou que o paciente quer faturar como particular.",
    "procedimento_real": "A recepção anotou que o procedimento feito foi '{real}', mas a guia está como {descricao}.",
    "remarcada": "A sessão foi remarcada e a autorização era da data original.",
    "autorizacao_nova_solta": "A recepção anotou que o paciente trouxe autorização nova, ainda não lançada.",
    "observacao_nao_reconhecida": "A observação não foi reconhecida: '{texto}'.",
    "duplicata_exata": "É a mesma guia já lançada como {outra}: mesmo paciente, data, procedimento, autorização e sessão.",
    "duplicata_suspeita": "O mesmo paciente tem o mesmo procedimento no mesmo dia na guia {outra}.",
}

CORRIGIR = {
    "convenio_desconhecido": "Conferir o nome do convênio.",
    "campo_vazio": "Preencher {campo} antes de enviar.{sugestao}",
    "data_ilegivel": "Corrigir a data para o formato dia/mês/ano.",
    "sem_data_atendimento": "Preencher a data do atendimento.",
    "sem_procedimento": "Preencher o código do procedimento.",
    "autorizacao_vencida": "Pedir nova autorização ou prorrogação ao convênio antes de enviar.",
    "autorizacao_vencida_com_nova": "Lançar o número e a validade da autorização nova antes de enviar.",
    "sem_autorizacao": "Conseguir o número com o convênio e lançar antes de enviar.",
    "sem_autorizacao_verbal_ok": "Lançar o número até {limite}, antes de enviar.",
    "sem_autorizacao_verbal_vencida": "Falar com o convênio: sem o número a guia é recusada.",
    "sem_autorizacao_verbal_nao_aceita": "Conseguir o número de autorização antes de enviar.",
    "sessao_acima": "{acao}",
    "procedimento_desconhecido": "Corrigir o código do procedimento.",
    "nao_coberto_particular": "Tirar do lote do convênio e faturar como particular.",
    "nao_coberto": "Não enviar a este convênio. Conferir com o financeiro como faturar.",
    "descricao_divergente": "Conferir qual procedimento foi feito e acertar código e descrição.",
    "valor_divergente": "Acertar o valor para a referência do procedimento.",
    "profissional_incompativel": "Conferir quem atendeu e qual procedimento foi feito de verdade.{extra}",
    "prazo_vencido": "Falar com o convênio antes de enviar: fora do prazo ele recusa.",
    "lancada_antes": "Conferir a data do atendimento e a data de lançamento.",
    "particular": "Tirar do lote do convênio e faturar como particular.",
    "procedimento_real": "Trocar o código pelo do procedimento feito.{cobertura}",
    "remarcada": "Confirmar com o convênio se a autorização vale para {atendimento}.",
    "autorizacao_nova_solta": "Conferir se o número lançado é o da autorização nova.",
    "observacao_nao_reconhecida": "Ler a observação antes de enviar.",
    "duplicata_exata": "Não enviar esta. Manter só a {outra}.",
    "duplicata_suspeita": "Conferir paciente, data e unidade nas duas guias.",
}

NOMES_DOS_CAMPOS = {
    "numero_autorizacao": "o número da autorização",
    "autorizacao_validade": "a validade da autorização",
    "profissional_registro": "o registro do profissional",
    "carteirinha": "a carteirinha",
    "cid": "o CID",
}
