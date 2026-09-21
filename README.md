# Vitalis · conferência de guias de convênio antes do envio

Etapa técnica do processo da Expert Integrado. Caso fictício da Clínica Vitalis: a recepção lança cerca de 900 guias por mês, o financeiro confere no fim do mês e o erro só aparece quando o convênio glosa, 60 dias depois. Aqui a conferência acontece no lançamento, antes do envio, e o Dr. Renato vê o resultado toda terça.

- **No ar:** https://vitalis-guias.vercel.app
- **Resultado no lote de agosto:** 80 guias conferidas, 41 prontas para enviar, 39 com problema, R$ 2.836,00 em risco de R$ 5.694,00.

## O que tem aqui

| Pasta | O que é |
|---|---|
| `motor/` | O motor de regras, em Python puro, sem dependência. É ele que decide. |
| `dados/` | `guias.csv` e `regras_convenio.json` da prova, sem alteração, mais `regras_extras.json` (ver decisão 3). |
| `api/` e `web/` | A API publicada na Vercel. `web/rotas.py` tem a lógica; `api/*.py` só recebe o pedido. |
| `public/index.html` | A página: guias conferidas, conferir guia nova, relatório de terça. |
| `mcp_server/` | O MCP, com quatro ferramentas. |
| `skills/conferir-guia/` | A Skill para quem opera a clínica. |
| `tests/` | 67 testes do motor. |

## Como uma guia entra e como a decisão sai

1. **Entra** por um de três caminhos, todos no mesmo motor:
   - `POST /api/verificar` com os campos da guia, que é o que o sistema de gestão ou um fluxo no n8n chama a cada guia lançada. É isso que faz a conferência não depender de alguém lembrar;
   - a página, colando a guia do jeito que a recepção escreveu. Linha do sistema e "campo: valor" são lidos direto. Texto corrido é leitura, não é dado: a página mostra os campos que leu, a pessoa confere e só então a guia é conferida;
   - o MCP, pela Skill, dentro do Claude.
2. O motor **lê** a guia como ela veio: data em dia/mês/ano, valor com vírgula, convênio sem acento. "Aguardando", "-" e "N/A" contam como campo vazio. Número que não é claramente um número ("1 1", "11 ou 12") não é adivinhado: a guia fica retida.
3. A **observação da recepção vira fatos** (quer particular, autorização por telefone, código errado), por palavras-chave, trecho a trecho. Um trecho só é dado como entendido se for exatamente uma frase comum ("chegou 10 min atrasado") ou se virar um fato, e todo fato vira pendência. O que sobrar segura a guia para uma pessoa ler. Com chave de IA, o modelo lê a observação e pode acrescentar fatos que geram pendência. Ele nunca consegue liberar uma guia.
4. As **regras decidem**: campo obrigatório por convênio, paciente, sessão e valor preenchidos, validade da autorização contra a data do atendimento, limite de sessões, cobertura do procedimento, registro do profissional, prazo de envio contado do atendimento e duplicidade dentro do lote (mesma guia repetida, ou mesma autorização com o mesmo número de sessão).
5. **Sai** `OK` ou `PENDENTE`, com motivo e o que corrigir. Pendente tem três níveis:
   - `vai_glosar`: fere regra escrita do convênio;
   - `corrigir`: falta ou está errado um dado que a recepção resolve;
   - `conferir`: a regra escrita não proíbe, mas tem cara de erro.

```bash
curl -X POST https://vitalis-guias.vercel.app/api/verificar \
  -H "Content-Type: application/json" \
  -d '{"guia": {"convenio": "Vitalcard", "procedimento_codigo": "50000470", "data_atendimento": "2026-09-02",
       "numero_autorizacao": "AUT1", "autorizacao_validade": "2026-09-20", "sessao_numero_na_autorizacao": "11",
       "carteirinha": "111222333", "cid": "M54.5", "profissional_registro": "CREFITO-3 204411-F", "valor": "62.00"}}'
```

## O MCP

Fica em `mcp_server/server.py`. Lê `dados/regras_convenio.json` e `dados/guias.csv` direto do disco e usa o mesmo motor da página.

| Ferramenta | O que faz |
|---|---|
| `consultar_regra(convenio, procedimento)` | Se o convênio cobre o procedimento, valor de referência, campos obrigatórios, limite de sessões, prazo de envio. |
| `verificar_guia(id_guia ou os campos)` | Confere uma guia do lote ou uma guia nova. Devolve decisão, motivo e o que corrigir. |
| `listar_pendentes(convenio, unidade)` | As guias do lote que não podem ser enviadas ainda. |
| `relatorio_de_terca()` | O resumo do Dr. Renato. |

Instalar. O SDK de MCP pede Python 3.10 ou mais novo. No macOS o `python3` do sistema costuma ser 3.9: confira com `python3 --version` e, se for o caso, use `python3.13` (ou outro que você tenha) na linha do venv.

```bash
git clone https://github.com/gbfelipe7/vitalis-guias.git
cd vitalis-guias
python3 -m venv .venv            # com Python 3.10 ou mais novo
.venv/bin/pip install -r mcp_server/requirements.txt
.venv/bin/python mcp_server/conferir_servidor.py     # sobe o servidor e chama as ferramentas, para ver funcionando
```

Ligar no Claude Code:

```bash
claude mcp add vitalis-guias -- "$(pwd)/.venv/bin/python" "$(pwd)/mcp_server/server.py"
```

No Claude Desktop, em `claude_desktop_config.json`:

```json
{ "mcpServers": { "vitalis-guias": {
    "command": "/caminho/para/vitalis-guias/.venv/bin/python",
    "args": ["/caminho/para/vitalis-guias/mcp_server/server.py"] } } }
```

## A Skill

Fica em `skills/conferir-guia/SKILL.md`. Para usar, copie a pasta `conferir-guia` para `~/.claude/skills/` (ou para `.claude/skills/` do projeto) com o MCP ligado. A pessoa cola a guia do jeito que a recepção escreveu. A Skill separa os campos, chama `verificar_guia` e responde OK ou PENDENTE, o motivo e o que corrigir. Ela não decide nada sozinha.

## Rodar na sua máquina

```bash
python3 servidor_local.py      # página e API em http://localhost:8000, sem instalar nada
python3 -m unittest            # os 67 testes do motor
```

A chave de IA é opcional. Sem ela tudo funciona: a observação é lida por palavras-chave e o texto corrido por expressão regular. Com `GEMINI_API_KEY` no ambiente (veja `.env.example`), o que eles não alcançam é lido pelo Gemini no nível gratuito. Na Vercel a chave fica nas variáveis de ambiente do projeto. Não existe chave nem senha neste repositório.

## Como fiz

### Ferramentas e por quê

- **Python puro no motor.** Regra de convênio é comparação de data, número e lista. Não precisa de biblioteca, roda igual na Vercel, no MCP e na minha máquina, e qualquer pessoa lê.
- **Vercel** para publicar: grátis, aceita função em Python e eu já uso.
- **SDK oficial de MCP em Python**, porque o MCP reaproveita o motor sem reescrever nada.
- **Gemini no nível gratuito** só para ler texto livre. Custo zero.
- **Claude Code** para escrever o código comigo.

### O que a IA gerou e o que foi decisão minha

O código foi escrito com o Claude Code. Eu li os dados antes, defini a arquitetura e os critérios, e revisei o que saiu. As decisões abaixo são minhas e eu sei defender cada uma.

1. **Regra decide, IA só lê texto.** Conferir guia é comparar data, limite e cobertura: tem resposta certa e ela precisa ser a mesma toda vez. Então a decisão é um motor de regras, sem IA. A IA entra só para ler texto livre, em dois pontos: separar os campos de uma guia colada em texto corrido e ler a observação da recepção. As travas que eu coloquei: na observação a IA só pode endurecer (acrescenta fato que gera pendência, e não consegue apagar o "texto que ninguém entendeu" nem devolver fato que amolece a decisão); no texto corrido todo valor que a IA devolve tem que existir no texto colado, senão é descartado, e a pessoa confirma os campos antes de a guia ser conferida; e o lote de agosto roda sem IA, para dar sempre o mesmo resultado.
2. **Na dúvida, segura.** Segurar uma guia boa custa um dia. Enviar uma ruim custa 60 dias e o valor da guia. Por isso existe o nível `conferir`: reavaliação de fisioterapia lançada por médico no Plano Bem, mesmo paciente em duas unidades no mesmo dia, sessão remarcada com autorização da data original. A regra escrita não proíbe, mas eu não enviaria sem alguém olhar. O relatório separa isso do que é glosa certa, para o Dr. Renato não achar que tudo é perdido.
3. **As frases dos convênios viraram regra estruturada.** O `regras_convenio.json` traz parte das regras em texto livre ("aceita autorização verbal com protocolo por até 5 dias úteis"). Em vez de pedir para uma IA interpretar isso a cada guia, eu li uma vez e escrevi em `dados/regras_extras.json`, citando a frase de origem. O arquivo da Carla fica intacto.
4. **A guia nova entra por página e por endereço de API.** A página serve para a recepção e para a demonstração. O endereço é o que resolve o problema de verdade: o sistema de gestão chama a cada lançamento e ninguém precisa lembrar de conferir.
5. **Duplicidade só aparece depois de normalizar a data.** Duas guias do lote são a mesma, mas uma tem a data como 26/08/2026 e a outra como 2026-08-26. Comparando texto, passa. Por isso a guia é normalizada antes de qualquer comparação, e a duplicada é sempre a que foi lançada depois.
6. **Dinheiro em risco é o valor da guia pendente, contado uma vez.** Guia com dois problemas entra no tipo do problema mais grave. Assim a soma por tipo bate com o total e ninguém conta o mesmo dinheiro duas vezes.

7. **O lote é conferido na data de lançamento; a guia nova, hoje.** O recrutador orientou simular a conferência do lote de agosto na data de lançamento, como se a guia tivesse acabado de ser lançada. Por isso nenhuma das 80 aparece com prazo de envio vencido. Já a guia que chega pela página, pela API ou pelo MCP é conferida com a data de hoje: uma guia de junho lançada agora sai com o prazo vencido.

### O que ficou de fora e por quê

- **Validade máxima da autorização** (30, 45 e 60 dias): o CSV só tem a data final, não a de concessão. Não dá para conferir sem inventar dado. A ferramenta `consultar_regra` mostra o número. O motor usa num caso só, como aviso e não como pendência: quando a recepção anota a validade de uma autorização nova e ela passa do máximo do convênio contado do atendimento (acontece na G-2608-0030).
- **Banco de dados.** As guias novas conferidas na página ficam só na sessão do navegador. Em produção eu gravaria cada conferência no Postgres, e o relatório de terça sairia de lá com histórico semana a semana.
- **Feriados** na conta de dias úteis da autorização verbal. A prova não traz calendário.
- **Proteção do endereço da API.** Está aberto, porque a banca precisa testar sem senha. Em produção ele ficaria atrás de um token do sistema de gestão. O custo de IA é zero de qualquer forma: a chave é do nível gratuito, sem cartão, e o texto mandado ao modelo é cortado em 2.000 caracteres.
- **Recibo para reembolso.** Oito guias têm a observação "Pediu recibo para reembolso do plano". Pode ser sinal de que o paciente pagou particular, e aí faturar o convênio seria cobrança em dobro. Os dados não confirmam, então o motor avisa e não segura. É pergunta para a Carla.
- **Ligação real com o sistema de gestão.** O endereço está pronto para ser chamado; a chamada em si depende da API do sistema da clínica.
- **Histórico de autorizações.** As 80 guias são o recorte de agosto, então o motor confere o que a guia declara e não tenta reconstruir a sequência de sessões de cada autorização.

### Como testei

- 67 testes automáticos em `tests/test_motor.py`. Quatro grupos: as guias do lote que têm pegadinha, uma a uma; guias novas chegando tortas (vazia, com lixo nos campos, data em outro formato, convênio que não existe, repetida do lote); e um teste para cada furo que as duas rodadas de auditoria abaixo encontraram.
- **Auditoria cega.** Pedi para cinco agentes de IA julgarem as 80 guias só com o CSV e as regras, sem ver o meu motor, e comparei. Deu 15 divergências em 80. Em nenhuma o motor tinha decidido errado: 12 eram diferença de vocabulário e 3 eram julgamento, como o recibo para reembolso.
- **Ataque à guia nova, em duas rodadas.** Outros agentes tentaram fazer uma guia errada sair como OK: campo com lista, `NaN`, sessão "11ª", data 31/02, observação com instrução escondida para a IA, texto corrido com uma "correção" embutida. A primeira rodada achou furos reais: guia repetida sem data de lançamento passava, uma frase comum escondia o resto da observação, sessão ilegível pulava a checagem de limite e a IA conseguia liberar uma guia ficando calada. Corrigi e mandei atacar de novo. A segunda rodada mostrou que a minha primeira correção era frouxa: bastava o trecho CONTER "atrasado" para ser ignorado, e a IA ainda conseguia amolecer uma decisão. Daí saíram as regras de hoje: o trecho tem que SER a frase comum, todo fato vira pendência, a IA só endurece e texto corrido passa por confirmação.
- `mcp_server/conferir_servidor.py` sobe o MCP de verdade e chama as quatro ferramentas como um cliente faria.
- A página e os quatro endereços testados no ar, com guia certa, guia com problema, texto corrido e corpo inválido.
- Conferi na mão as cinco guias que só se entendem pela observação da recepção: G-2608-0030, 0034, 0039, 0041 e 0069.
