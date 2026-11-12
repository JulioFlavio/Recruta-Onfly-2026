# README-ENTREGA — Consolidador de reservas Onfly

Resumo: o CLI tinha **5 defeitos** que distorciam o relatório. Quatro foram detectados pelos testes fornecidos e um
(o limite silencioso de 200 linhas) não era coberto por nenhum teste. Todos foram corrigidos. Depois disso, numa
revisão além do escopo, o código ganhou validação de entrada, processamento em streaming e **28 testes novos**.

| Verificação | Resultado |
|-|-|
| `pytest -q` | **33 passed** (5 fornecidos + 28 novos), sem alterar os testes fornecidos |
| Amostra `data/exemplo-validacao.csv` | Idêntica à tabela do README, campo a campo |
| Dataset completo `data/reservas_hoteis.csv` | Conferido contra um recálculo independente (`summary`, `by_month` e `top_hotels`) |
| `ruff check` / `ruff format --check` | Sem apontamentos |

---

## 1. Defeitos identificados e soluções

| # | Defeito (sintoma) | Causa raiz | Correção | Arquivo |
|-|-|-|-|-|
| 1 | Valores em moeda estrangeira muito abaixo do real (100 USD viravam 18.45 BRL) | A conversão **dividia** o valor pela taxa em vez de multiplicar, e ainda passava por `float`, que o README proíbe para dinheiro. | `amount * rates[currency]`, inteiramente em `Decimal` | `services/currency_converter.py` |
| 2 | Noites negativas na virada de mês (30/01 → 02/02 resultava em −28) | O cálculo subtraía só o **dia do mês** (`checkout.day - checkin.day`), em vez da diferença entre as datas. | `(checkout - checkin).days * rooms` | `services/stay_calculator.py` |
| 3 | `NO_SHOW` entrava em valores, noites, `by_month` e `top_hotels` | A política de faturamento excluía só `CANCELLED` (`status != "CANCELLED"`), então todo o resto passava. | `status == "CONFIRMED"`: uma lista de permissão em vez de exclusão | `services/status_policy.py` |
| 4 | `top_hotels` mostrava primeiro os hotéis de **menor** valor | A ordenação usava `(amount, hotel_id)` em ordem crescente. | `key=(-amount, hotel_id)`: valor decrescente com desempate por `hotel_id` crescente, como manda o README. Usar `reverse=True` inverteria também o desempate. | `services/report_builder.py` |
| 5 | Relatório do dataset real com só 200 das 300 reservas, sem nenhum aviso | O repositório tinha um `break` ao chegar em 200 linhas lidas. | Remoção do limite | `repositories/csv_reservation_repository.py` |

O teste `test_regression_report_on_sample` falhava só por causa do defeito 1. Ele não tem `NO_SHOW` nem virada de
mês.

O defeito 5 **não é coberto por nenhum teste fornecido**: com os quatro primeiros corrigidos, os 5 testes passam e o
relatório real continua errado. Ele foi encontrado lendo o código e comparando com o tamanho do dataset (300 linhas).

---

## 2. Como investiguei

1. **Leitura do README e do contrato**, para registrar as regras de status, de noites, de câmbio, de exatidão e de
   ordenação, além do que não pode mudar.
2. **Ambiente e linha de base:** criei a `.venv` (Python 3.14.4, compatível com o requisito 3.11+), instalei
   `requirements-dev.txt` e rodei `pytest`. Os 5 testes falharam, como o README previa.
3. **Do sintoma à causa:** para cada falha, comparei o valor obtido com o esperado e voltei até a função
   responsável. Por exemplo, `118.45` em vez de `642.00` significa 100 + 100 / 5.42, ou seja, uma divisão no lugar de
   uma multiplicação.
4. **Leitura integral do código**, procurando defeitos sem teste, que foi como apareceu o limite de 200 linhas.
5. **Correção um defeito por vez**, com um commit por correção e os testes rodados a cada passo (veja o histórico
   do git).
6. **Validação final** pela amostra do README, por um recálculo independente do dataset completo, pelo perfil dos
   dados (duplicatas, espaços, datas invertidas, moedas e status) e por testes de casos de borda no CLI.

---

## 3. Sugestões da IA e o que foi aceito

| Sugestão | Origem | Status | Mudança no código |
|-|-|-|-|
| Correções dos defeitos 1 a 4 | Diagnóstico da IA a partir das falhas e do código | **Aceita**, aplicada por mim, um commit por defeito | Ver seção 1 |
| Remover o limite de 200 linhas (defeito 5) | Encontrado pela IA lendo o código, sem teste que o cobrisse | **Aceita**, aplicada por mim | `csv_reservation_repository.py` |
| Remover o `Decimal(...)` redundante em volta do produto | Revisão de qualidade da IA | **Aceita**, aplicada por mim | `currency_converter.py` |
| Moeda sem taxa terminar com código `2` (antes: `KeyError`, código `1`) | Teste de borda da IA no CLI | **Aceita**, implementada pela IA | Nova exceção `UnknownCurrencyError`; o erro informa o número da linha |
| Moeda e status convertidos para maiúsculas | A tabela de câmbio já fazia isso e a reserva não | **Aceita**, implementada pela IA | `row_parser.py` |
| Rejeitar status desconhecido (antes contava no total sem entrar em nenhuma categoria) | Teste de borda da IA | **Aceita**, implementada pela IA | `row_parser.py` e `VALID_STATUSES` em `status_policy.py` |
| Rejeitar check-out igual ou anterior ao check-in, `rooms < 1`, `amount` negativo, `hotel_id` ou `currency` vazios | Teste de borda da IA (check-out invertido gerava −2 noites com código 0) | **Aceita**, implementada pela IA | `row_parser.py` |
| Aceitar CSV com BOM (exportações do Excel) | Teste de borda da IA | **Aceita**, implementada pela IA | `utf-8-sig` nos dois repositórios |
| Leitura em streaming e agregação numa única passada | Pedido de escalabilidade | **Aceita**, implementada pela IA | O repositório passou a devolver um `Iterator`; o `ReportBuilder` foi refatorado |
| Organizar o `ReportBuilder` em acumuladores tipados e métodos menores | Revisão de qualidade da IA | **Aceita**, implementada pela IA | `report_builder.py` |
| Forçar UTF-8 no log (acentos chegavam corrompidos no Windows) | Encontrado pelos testes novos | **Aceita**, implementada pela IA | `logging_config.py` |
| Linha de log com o resumo da leitura (no stderr; o stdout não mudou) | Sugestão da IA | **Aceita** | `report_builder.py` |
| Resolver o conflito de nome para o mesmo `hotel_id` | Avaliada | **Não aplicada**: o README garante dados consistentes e não define a regra | — |
| Fazer a soma de `by_month` bater com `total_amount_brl` | Avaliada | **Não aplicada**: a diferença é exigida pela regra de arredondar só na serialização | — |

### Decisões de interpretação (README omisso)
- **Status em minúsculas é aceito** e convertido para maiúsculas (`confirmed` → `CONFIRMED`), coerente com o que já
  acontecia com a moeda. Para ser estrito, basta retirar o `.upper()` do status em `row_parser.py`.
- **Check-out no mesmo dia do check-in é rejeitado**, porque produziria 0 noites com valor cobrado e inflaria a média.
- **Entrada inválida nunca é descartada em silêncio:** o CLI termina com código `2` e a linha do problema. Isso segue
  a própria docstring do `RowParser` e o contrato de códigos de saída.

Nada do que o README proíbe foi alterado: o comando e os argumentos, o schema e a semântica do relatório, os arquivos
`data/reservas_hoteis.csv` e `data/taxas_cambio.csv` e os testes fornecidos. Para os dados fornecidos, o relatório
gerado é **idêntico** antes e depois da revisão (comparado sem o `generated_at`).

---

## 4. Casos que não eram testados e foram validados

| Caso | Como foi validado | Resultado antes da revisão |
|-|-|-|
| Arquivo com mais de 200 linhas | Teste novo e o dataset real (300) | Truncava em 200 (defeito 5) |
| Amostra completa do README (EUR, USD, 3 status, virada de mês) | Execução do CLI comparada com a tabela | OK depois das correções |
| Dataset completo | Recálculo independente em script separado | OK depois das correções |
| Dados do dataset | Perfil: IDs e conteúdo duplicados, espaços, datas, moedas, status, nomes por `hotel_id` | Dados limpos |
| `--top 0`, `--top -1`, `--top abc`, arquivo ausente | CLI e testes novos | Já retornavam `2` |
| Moeda sem taxa (`GBP`) | CLI | `KeyError`, código `1` (corrigido para `2`) |
| Moeda em minúsculas (`usd`) | CLI | `KeyError`, código `1` (corrigido) |
| Status desconhecido (`PENDING`, `confirmed`) | CLI | Código `0`, com contagens inconsistentes (corrigido) |
| Check-out antes do check-in | CLI | **−2 noites**, código `0` (corrigido para `2`) |
| `rooms = 0` | CLI | Valor sem noites, código `0` (corrigido para `2`) |
| CSV com BOM | CLI | Rejeitado: "coluna `reservation_id` ausente" (corrigido) |
| Virada de ano, `rooms > 1`, desempate do ranking, half-up, média sem noites | Testes novos | OK |

---

## 5. Testes implementados

Todos ficam em `tests/` e nenhum teste fornecido foi alterado. Os testes de regra executam o CLI real num
subprocesso, pelo `helpers.run_cli` fornecido, então validam o comportamento ponta a ponta.

### `tests/test_csv_reservation_repository.py` (6 testes): leitura do CSV
| Teste | Garante |
|-|-|
| `test_reads_every_row_without_limit` | 300 linhas lidas, sem truncar (regressão do defeito 5) |
| `test_keeps_raw_values_and_physical_line_numbers` | Valores chegam como texto e `line_number` é a linha física, inclusive com vírgula dentro de aspas |
| `test_empty_file_with_header_returns_no_rows` | Arquivo só com cabeçalho devolve uma lista vazia |
| `test_missing_required_column_raises_input_error` | Uma coluna ausente gera `InputFileError` citando a coluna |
| `test_accepts_utf8_bom` | Arquivo com BOM é aceito |
| `test_missing_file_raises_input_error` | Arquivo inexistente gera `InputFileError` |

### `tests/test_report_rules.py` (7 testes): regras de negócio do README
| Teste | Garante |
|-|-|
| `test_nights_across_year_boundary_and_multiple_rooms` | 31/12 → 02/01 com 3 quartos dá 6 noites, no mês do check-in |
| `test_by_month_uses_checkin_month_and_ascending_order` | `by_month` usa o mês do check-in, em ordem crescente, e exclui NO_SHOW |
| `test_top_hotels_tie_breaks_by_hotel_id_and_respects_top` | Empate desfeito por `hotel_id` crescente e limite de `--top` respeitado |
| `test_top_hotels_aggregates_multiple_reservations_of_same_hotel` | Reservas do mesmo hotel somadas, em moedas diferentes |
| `test_money_rounds_half_up_only_at_serialization` | 0.005 + 0.005 = 0.01: soma exata e arredondamento só no fim |
| `test_average_nightly_rate_rounds_half_up` | A média usa half-up (2.01 / 2 = 1.005 vira 1.01) |
| `test_without_confirmed_reservations_totals_are_zero` | Sem reservas confirmadas: totais em `"0.00"` e listas vazias |

### `tests/test_input_validation.py` (15 casos): entradas inválidas e contrato do CLI
| Teste | Garante |
|-|-|
| `test_invalid_row_exits_with_code_2` (9 casos parametrizados) | Moeda sem taxa, status desconhecido, check-out antes ou no mesmo dia do check-in, `rooms = 0`, `amount` negativo ou não numérico, data fora de ISO e `hotel_id` vazio terminam com código **2**. A mensagem traz a **linha** e nenhum relatório é gravado. |
| `test_invalid_top_exits_with_code_2` (3 casos) | `--top` igual a `0`, `-1` ou `abc` termina com código **2** |
| `test_missing_input_file_exits_with_code_2` | Arquivo ausente termina com código **2** e uma mensagem clara |
| `test_lowercase_currency_and_status_are_normalized` | `usd` e `confirmed` são aceitos e convertidos corretamente |
| `test_output_is_valid_json_with_exact_schema` | Chaves do relatório na ordem do contrato, `report_version` igual a `"1.0"` e offset `-03:00` |

---

## 6. Revisão após o escopo inicial

Com os 5 testes fornecidos passando, fiz uma segunda rodada de revisão:

1. **Conferência do resultado:** amostra do README, recálculo independente do dataset completo e perfil dos dados.
2. **Busca de pontos fracos:** executei o CLI com entradas fora do padrão e encontrei os 6 comportamentos incorretos
   da tabela da seção 4.
3. **Conferência contra o README** do que podia ou não ser alterado antes de implementar (seção 3).
4. **Implementação:** validação de entrada, leitura em streaming (a memória não cresce mais com o tamanho do
   arquivo), refatoração do `ReportBuilder`, suporte a BOM e log em UTF-8.
5. **Testes novos (28)**, que também encontraram um problema real: acentos corrompidos no log no Windows.
6. **Regressão:** o relatório dos dados fornecidos ficou idêntico ao de antes da revisão.

---

## 7. Como validar

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

pytest -q                          # 33 passed

PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json     # compare com a tabela "Amostra de validação" do README

PYTHONPATH=src python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json
# Reservas: 300 | Confirmadas: 235 | Noites: 1347 | Total BRL: 396170.00
```

### Resultado do `pytest`
```
.................................                                        [100%]
33 passed in 4.22s
```

---

## 8. Uso de IA

- **Ferramenta:** Claude Code (extensão do VS Code).
- **LLM e modelo:** Claude Opus 5.5 (Anthropic), id `claude-opus-5-5`.
- **O que a IA fez:**
  - preparou o ambiente e rodou os testes;
  - diagnosticou a causa de cada falha;
  - encontrou o defeito sem teste (limite de 200 linhas);
  - validou o dataset e a amostra de forma independente;
  - testou casos de borda;
  - implementou a validação de entrada, o streaming, a refatoração e os 28 testes novos;
  - rascunhou este documento.
- **O que eu fiz:**
  - conduzi a investigação e decidi o escopo de cada etapa;
  - apliquei e commitei as correções dos 5 defeitos e a limpeza do `Decimal` redundante;
  - revisei as mudanças propostas pela IA e as decisões de interpretação;
  - aprovei o commit e o push da revisão.
- Exportação da sessão e declaração: `entrega/uso-de-ia/`.

---

## Tempo total

**≈ 2h30 de trabalho efetivo**, contado do início da sessão (14:42) até a conclusão deste rascunho (≈ 18:30), sem os
intervalos de pausa.

| Etapa | Período | Duração |
|-|-|-|
| Ambiente, diagnóstico, correção dos 5 defeitos e teste do repositório CSV | 14:42 – 16:07 | ≈ 1h25 |
| Revisão além do escopo, melhorias, testes novos, commit e documentação | 17:24 – 18:30 | ≈ 1h05 |
