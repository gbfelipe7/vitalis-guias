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
| `index.html` | A página: guias conferidas, conferir guia nova, relatório de terça. |
| `mcp_server/` | O MCP, com quatro ferramentas. |
| `skills/conferir-guia/` | A Skill para quem opera a clínica. |
| `tests/` | 31 testes do motor. |

## Como uma guia entra e como a decisão sai

1. **Entra** por um de três caminhos, todos no mesmo motor:
   - a página, colando a guia do jeito que a recepção escreveu (linha do sistema, um campo por linha ou texto corrido);
   - `POST /api/verificar`, que é o que o sistema de gestão ou um fluxo no n8n chama a cada guia lançada. É isso que faz a conferência não depender de alguém lembrar;
   - o MCP, pela Skill, dentro do Claude.
2. O motor **lê** a guia como ela veio: data em dia/mês/ano, valor com vírgula, convênio sem acento.
3. A **observação da recepção vira fatos** (quer particular, autorização por telefone, código errado). Primeiro por palavras-chave. Se sobrar texto desconhecido e houver chave de IA, a IA lê. A IA nunca decide.
4. As **regras decidem**: campo obrigatório por convênio, validade da autorização contra a data do atendimento, limite de sessões, cobertura do procedimento, registro do profissional, prazo de envio contado do atendimento e duplicidade dentro do lote.
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

Instalar (precisa de Python 3.10 ou mais novo):

```bash
git clone https://github.com/gbfelipe7/vitalis-guias.git
cd vitalis-guias
python3 -m venv .venv
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
python3 -m unittest            # os 31 testes do motor
```

A chave de IA é opcional. Sem ela tudo funciona e a observação é lida por palavras-chave. Com `GEMINI_API_KEY` no ambiente (veja `.env.example`), texto que as palavras-chave não reconhecem é lido pelo Gemini no nível gratuito. Na Vercel a chave fica nas variáveis de ambiente do projeto. Não existe chave nem senha neste repositório.

## Como fiz

### Ferramentas e por quê

- **Python puro no motor.** Regra de convênio é comparação de data, número e lista. Não precisa de biblioteca, roda igual na Vercel, no MCP e na minha máquina, e qualquer pessoa lê.
- **Vercel** para publicar: grátis, aceita função em Python e eu já uso.
- **SDK oficial de MCP em Python**, porque o MCP reaproveita o motor sem reescrever nada.
- **Gemini no nível gratuito** só para ler texto livre. Custo zero.
- **Claude Code** para escrever o código comigo.

### O que a IA gerou e o que foi decisão minha

O código foi escrito com o Claude Code. Eu li os dados antes, defini a arquitetura e os critérios, e revisei o que saiu. As decisões abaixo são minhas e eu sei defender cada uma.

1. **Regra decide, IA só lê texto.** Conferir guia é comparar data, limite e cobertura: tem resposta certa e ela precisa ser a mesma toda vez. Então a decisão é um motor de regras, sem IA. A IA entra num lugar só, a observação que a recepção escreveu, e mesmo ali ela devolve fatos ("quer particular", "protocolo 771203") que o motor usa. Toda guia pendente tem um motivo que aponta para uma regra, e o lote de agosto dá sempre o mesmo resultado.
2. **Na dúvida, segura.** Segurar uma guia boa custa um dia. Enviar uma ruim custa 60 dias e o valor da guia. Por isso existe o nível `conferir`: reavaliação de fisioterapia lançada por médico no Plano Bem, mesmo paciente em duas unidades no mesmo dia, sessão remarcada com autorização da data original. A regra escrita não proíbe, mas eu não enviaria sem alguém olhar. O relatório separa isso do que é glosa certa, para o Dr. Renato não achar que tudo é perdido.
3. **As frases dos convênios viraram regra estruturada.** O `regras_convenio.json` traz parte das regras em texto livre ("aceita autorização verbal com protocolo por até 5 dias úteis"). Em vez de pedir para uma IA interpretar isso a cada guia, eu li uma vez e escrevi em `dados/regras_extras.json`, citando a frase de origem. O arquivo da Carla fica intacto.
4. **A guia nova entra por página e por endereço de API.** A página serve para a recepção e para a demonstração. O endereço é o que resolve o problema de verdade: o sistema de gestão chama a cada lançamento e ninguém precisa lembrar de conferir.
5. **Duplicidade só aparece depois de normalizar a data.** Duas guias do lote são a mesma, mas uma tem a data como 26/08/2026 e a outra como 2026-08-26. Comparando texto, passa. Por isso a guia é normalizada antes de qualquer comparação, e a duplicada é sempre a que foi lançada depois.
6. **Dinheiro em risco é o valor da guia pendente, contado uma vez.** Guia com dois problemas entra no tipo do problema mais grave. Assim a soma por tipo bate com o total e ninguém conta o mesmo dinheiro duas vezes.

### O que ficou de fora e por quê

- **Validade máxima da autorização** (30, 45 e 60 dias): o CSV só tem a data final, não a de concessão. Não dá para conferir sem inventar dado. A ferramenta `consultar_regra` mostra o número, o motor não usa.
- **Banco de dados.** As guias novas conferidas na página ficam só na sessão do navegador. Em produção eu gravaria cada conferência no Postgres, e o relatório de terça sairia de lá com histórico semana a semana.
- **Feriados** na conta de dias úteis da autorização verbal. A prova não traz calendário.
- **Ligação real com o sistema de gestão.** O endereço está pronto para ser chamado; a chamada em si depende da API do sistema da clínica.
- **Histórico de autorizações.** As 80 guias são o recorte de agosto, então o motor confere o que a guia declara e não tenta reconstruir a sequência de sessões de cada autorização.

### Como testei

- 31 testes automáticos em `tests/test_motor.py`: as guias do lote que têm pegadinha, uma a uma, e guias novas chegando tortas (vazia, com lixo nos campos, data em outro formato, convênio que não existe, repetida do lote).
- `mcp_server/conferir_servidor.py` sobe o MCP de verdade e chama as quatro ferramentas como um cliente faria.
- A página e os quatro endereços testados no ar, com guia certa, guia com problema, texto corrido e corpo inválido.
- Conferi na mão as cinco guias que só se entendem pela observação da recepção: G-2608-0030, 0034, 0039, 0041 e 0069.
