# Prompt mestre

Este não é o texto literal da conversa com o Claude Code. A solução foi construída em várias rodadas, entre 21 e 24/09, com pedidos, revisões e pedidos para refazer. Este prompt junta tudo isso num pedido só, escrito depois, para quem quiser entender o que foi pedido ou reconstruir a solução do zero.

---

Você vai construir comigo a solução da prova técnica da Expert Integrado: a conferência das guias de convênio da Clínica Vitalis antes do envio.

## Contexto

A Vitalis é uma rede de fisioterapia e ortopedia com três unidades. Fatura cerca de 900 guias de convênio por mês. A recepção preenche a guia no sistema de gestão enquanto atende balcão, telefone e WhatsApp. O financeiro confere no fim do mês, em planilha, e o erro só aparece quando o convênio glosa, uns 60 dias depois. O sistema de gestão não vai ser trocado (o contrato foi renovado por dois anos), mas tem API e exporta relatórios. O Dr. Renato, dono, acompanha o projeto toda terça, às 7h30.

Materiais: `dados/guias.csv` (80 guias de agosto, fictícias) e `dados/regras_convenio.json` (o que cada convênio exige e cobre).

Esclarecimentos da recrutadora, que valem como regra:
- A validade da autorização é conferida contra a data do atendimento. O CSV só tem a data final.
- O lote de agosto é conferido na data de lançamento: a guia acabou de ser lançada e ainda não foi enviada. O prazo de envio conta da data do atendimento.
- As 80 guias são um recorte. Confira o que a guia declara, sem tentar reconstruir o histórico da autorização.

## Decisões que são minhas e não mudam

1. **A regra decide, a IA só lê.** Conferir guia é comparar data, limite e cobertura, e a resposta tem que ser a mesma toda vez. Resolva em código tudo o que der. A IA entra só onde é necessária: separar os campos de uma guia colada como texto corrido e ler a observação da recepção quando as palavras-chave não bastarem. Todo valor que a IA devolver tem que estar escrito no texto, e ela só pode segurar a guia, nunca liberar.
2. **Na dúvida, segura.** Segurar uma guia boa custa um dia. Enviar uma ruim custa 60 dias e o valor da guia. Quando a regra escrita não proíbe mas algo está estranho, a guia fica para alguém conferir.
3. **A conferência acontece no lançamento**, antes de a guia ir para o convênio, sem depender de alguém lembrar.
4. **As decisões têm nome pelo que fazer:** Pode enviar, Não enviar assim, Corrigir antes de enviar e Conferir antes de enviar. Cada guia retida sai também com o próximo passo, ou seja, quem resolve: o convênio, a recepção, o paciente como particular, o financeiro, uma confirmação, ou descartar a cópia. Cada regra leva a uma decisão só.
5. **Guia retida gera um aviso pronto** para quem resolve, sem nome de paciente nem CID.

## O que construir

1. **O conferente, em Python puro** (`motor/`). Regras: campos exigidos pelo convênio, cobertura do procedimento, validade da autorização na data do atendimento, sessão dentro do limite da autorização, autorização por telefone quando o convênio aceita, valor, profissional compatível com o procedimento, prazo de envio, a observação da recepção e guia repetida. Arrume as datas antes de comparar. Guia repetida: se tudo bate, a lançada depois é a cópia; se só parte bate, fica para conferir. Uma guia corrigida é conferida de novo e entra no lugar da original.
2. **A API na Vercel** (`api/`): `POST /api/verificar` recebe uma guia no formato do CSV e responde em JSON com a decisão, o motivo, o que fazer e quem resolve. `GET /api/regra` responde a regra de um convênio para um procedimento. `GET` e `POST /api/relatorio` montam o relatório de terça. Erro tratado em tudo: nenhuma entrada estranha pode derrubar a rota.
3. **O relatório de terça**: a semana anterior, de segunda a domingo, pela data de lançamento. Quantas guias foram conferidas, quantas ficaram retidas, de que tipo, quanto dinheiro está em risco e quem resolve. Cada guia retida conta uma vez, no problema mais grave. Traga também como as guias foram lançadas (no mesmo dia, no fim de semana) e o que fazer na semana: conferir antes da sessão, pedir as autorizações que vão vencer ou esgotar, e confirmar as guias com pedido de recibo. Gere uma imagem e um texto curto para o WhatsApp.
4. **Um MCP** (`mcp_server/`) em cima dos arquivos da prova, com quatro ferramentas: `consultar_regra`, `verificar_guia`, `listar_pendentes` e `relatorio_de_terca`. Ele usa o mesmo conferente da API.
5. **Uma Skill** (`skills/conferir-guia/`) para quem opera a clínica: a pessoa cola a guia do jeito que a recepção escreveu, e a Skill separa os campos, pergunta o que falta, chama o MCP e responde a decisão, o motivo e o que corrigir. Ela nunca decide sozinha.
6. **A página** (`public/index.html`), para a banca abrir e usar com as 80 guias. Abas de apresentação: o que foi construído, dados e problemas, soluções e entregáveis. Abas do sistema: visão geral com gráficos que ajudem a decidir, guias de agosto com filtro e o botão de corrigir, lançar guia (um formulário igual ao do sistema, que simula a tela deles e confere enquanto a pessoa preenche), relatório de terça com a escolha da semana, e como funciona, com as regras agrupadas pela decisão que dão. Tema claro como padrão e tema escuro. Tem que funcionar no celular.
7. **Testes automáticos** (`tests/`) para as guias do lote com pegadinha, para guias novas chegando tortas e para cada furo que aparecer.
8. **O README "Como fiz"**: ferramentas e por quê, o que a IA gerou e o que foi decisão minha, o que ficou de fora e por quê, como testei, quanto tempo levou, como fica em produção e os próximos passos.

## Regras de entrega

- Custo zero para a Expert. Nenhuma chave ou senha no repositório.
- Texto da página e do README em português simples, com pouco texto, sem travessão, sem seta e sem emoji. Nunca invente número: todo número sai dos dados.
- Diga com honestidade o que é plano de produção e ainda não está montado: o fluxo no n8n que lê a API do sistema de gestão e o envio pelo WhatsApp.

## Como testar

Rode os testes a cada mudança. Depois, peça a agentes que julguem as 80 guias sem ver o código e compare com o conferente. Por último, tente fazer uma guia errada passar. Cada furo achado vira teste.
