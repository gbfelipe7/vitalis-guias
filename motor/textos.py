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
    "sem_paciente": "A guia está sem o paciente.",
    "sem_sessao": "A guia está sem o número da sessão, ou ele não é um número: '{valor}'. Sem ele não dá para conferir o limite da autorização.",
    "sem_valor": "A guia está sem valor, ou o valor não é um número válido: '{valor}'.",
    "atendimento_no_futuro": "O atendimento está marcado para {atendimento}, depois do dia da conferência ({referencia}).",
    "sessao_acima_do_declarado": "É a sessão {sessao}, mas a própria guia diz que a autorização cobre {declarado}.",
    "nova_tambem_nao_cobre": "A autorização lançada venceu em {validade} e a nova, que a recepção anotou, vale só até {nova}, antes do atendimento de {atendimento}.",
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
    "verbal_com_numero": "A recepção anotou autorização por telefone, mas a guia já tem o número {numero}.",
    "observacao_cortada": "A observação passa de 1.000 caracteres e foi lida só até ali.",
    "duplicata_exata": "É a mesma guia já lançada como {outra}: mesmo paciente, data, procedimento, autorização e sessão.",
    "duplicata_suspeita": "O mesmo paciente tem o mesmo procedimento no mesmo dia na guia {outra}.",
    "mesma_sessao": "A guia {outra} já usa esta mesma autorização com este mesmo número de sessão.",
}

CORRIGIR = {
    "convenio_desconhecido": "Conferir o nome do convênio.",
    "campo_vazio": "Preencher {campo} antes de enviar.{sugestao}",
    "data_ilegivel": "Corrigir a data para o formato dia/mês/ano.",
    "sem_data_atendimento": "Preencher a data do atendimento.",
    "sem_procedimento": "Preencher o código do procedimento.",
    "sem_paciente": "Preencher o paciente.",
    "sem_sessao": "Preencher o número da sessão, só com algarismos.",
    "sem_valor": "Preencher o valor da guia.",
    "atendimento_no_futuro": "Conferir a data do atendimento. Guia só é enviada depois que a sessão aconteceu.",
    "sessao_acima_do_declarado": "Conferir o limite desta autorização. Se for mesmo {declarado}, pedir nova autorização antes de enviar.",
    "nova_tambem_nao_cobre": "Pedir ao convênio uma autorização que cubra a data do atendimento.",
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
    "verbal_com_numero": "Conferir se o número lançado é o definitivo do convênio, e não o protocolo.",
    "observacao_cortada": "Ler a observação inteira no sistema antes de enviar.",
    "duplicata_exata": "Não enviar esta. Manter só a {outra}.",
    "duplicata_suspeita": "Conferir paciente, data e unidade nas duas guias.",
    "mesma_sessao": "Conferir se é a mesma sessão lançada duas vezes ou se o número da sessão está errado.",
}

NOMES_DOS_CAMPOS = {
    "numero_autorizacao": "o número da autorização",
    "autorizacao_validade": "a validade da autorização",
    "profissional_registro": "o registro do profissional",
    "carteirinha": "a carteirinha",
    "cid": "o CID",
}

# Avisos que não seguram a guia. Aparecem junto da decisão.
ALERTA = {
    "codigo_pela_descricao": "O código do procedimento não veio. Pela descrição, usei {codigo}.",
    "prazo_perto": "Enviar até {limite}: faltam {dias} dia(s) para o prazo do {convenio}.",
    "ultima_sessao": "É a última sessão desta autorização. A próxima precisa de autorização nova.",
    "limite_diferente": "A guia diz que a autorização cobre {declarado} sessões; a regra do {convenio} diz {limite}.",
    "limite_ilegivel": "O limite de sessões da autorização veio como '{valor}' e não foi lido. Vale o limite do convênio.",
    "recibo_reembolso": "A recepção anotou pedido de recibo para reembolso do plano. Se o paciente pagou a sessão como particular, não enviar ao convênio.",
    "nova_validade_longa": "A validade anotada para a autorização nova ({nova}) passa dos {maximo} dias que o {convenio} costuma dar. Conferir a data no documento.",
}
