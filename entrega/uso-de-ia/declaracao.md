# Declaração de uso de IA

## Ferramenta e modelo

| | |
|-|-|
| Ferramenta | Claude Code (extensão do VS Code), da Anthropic |
| LLM / modelo | Claude Opus 5.5, id `claude-opus-5-5` |
| Sessões | Uma única sessão em 12/11/2026; o log consolidado está em [`sessao.md`](sessao.md) |

## O que a IA fez

- **Leitura e ambiente:** leu o README e o código, criou a `.venv`, instalou as dependências de desenvolvimento e
  rodou a suíte de testes inicial (5 falhas).
- **Diagnóstico:** para cada teste que falhava, apontou a causa raiz no código e a solução. Também encontrou, lendo o
  código, um defeito que nenhum teste fornecido cobria: o limite silencioso de 200 linhas na leitura do CSV.
- **Validação independente:** comparou a saída do CLI com a amostra do README, recalculou o relatório do dataset
  completo num script separado e analisou o perfil dos dados (duplicatas, formatos, datas e moedas).
- **Testes de borda no CLI:** encontrou 6 comportamentos incorretos com entradas inválidas, como moeda sem taxa
  terminando com o código errado, noites negativas e CSV com BOM rejeitado.
- **Implementação da revisão além do escopo**, depois de eu pedir e de conferir no README o que podia ser alterado:
  - validação de entrada com código de saída `2` e o número da linha na mensagem;
  - leitura em streaming com agregação numa única passada;
  - refatoração do `ReportBuilder`;
  - suporte a BOM;
  - log em UTF-8.
- **Testes:** escreveu os 28 testes novos (`test_csv_reservation_repository.py`, `test_report_rules.py` e
  `test_input_validation.py`).
- **Commit e push:** fez o commit e o push da revisão, depois da minha autorização.
- **Documentação:** rascunhou o `README-ENTREGA.md`, esta declaração e o `sessao.md`, gerado a partir do transcript
  nativo da sessão.

## O que eu fiz

- Conduzi a sessão e defini o escopo e a ordem de cada etapa: diagnóstico sem alterar o repositório, depois
  correção, depois revisão.
- Apliquei e commitei eu mesmo as correções dos 5 defeitos, um commit por defeito, rodando os testes a cada passo.
- Apliquei a limpeza do `Decimal` redundante sugerida na revisão.
- Pedi a revisão além do escopo e a conferência contra o README antes de qualquer alteração.
- Revisei as mudanças propostas pela IA e as decisões de interpretação (status em minúsculas aceito, check-out no
  mesmo dia rejeitado). Também decidi restaurar o lint antes do commit.
- Revisei e aprovei o commit e o push e os documentos da entrega.

## Observações

- Nenhum teste fornecido foi alterado. Os dados em `data/` não foram alterados.
- Sugestões da IA foram validadas pela suíte de testes (33 passando) e pela comparação com a amostra do README antes
  de ser aceita.
