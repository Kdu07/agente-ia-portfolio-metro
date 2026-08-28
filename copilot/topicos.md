# Mapeamento intenção → tópico/ação do Copilot Studio

Este arquivo é o **contrato entre o middleware e o Copilot Studio**: cada intenção
do catálogo (`src/middleware/app/pipeline/intencao/catalogo.py`) corresponde a um
tópico/ação configurado no Copilot. Toda alteração no catálogo ou nos tópicos deve
ser refletida aqui, na mesma mudança.

O catálogo tem 26 intenções mais as classes negativas `fora_de_escopo` e
`tentativa_injecao` (28 classes, conforme a seção 5.4.8 de
[Projeto.md](../documentos/Projeto.md)). Todas as 28 passaram a ter exemplos no
corpus de treino, mas as intenções marcadas como _documentado, não treinado_ e
_pendente de validação_ seguem fora do escopo de execução do MVP e, portanto, não
precisam de tópico configurado nesta etapa.

Nenhuma das duas classes negativas aciona o Copilot, e por isso nenhuma tem
tópico. A diferença entre elas está no desfecho registrado, não no destino.

## Categoria consulta — família consulta pontual

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `consultar_status_projeto` | Treinado no MVP | _a configurar_ | Consolidar situação e fase atual do projeto | SharePoint |
| `consultar_avanco` | Treinado no MVP | _a configurar_ | Ler avanço realizado x planejado | SharePoint |
| `consultar_cronograma` | Treinado no MVP | _a configurar_ | Ler datas, fases e término previsto | SharePoint |
| `consultar_marcos` | Treinado no MVP | _a configurar_ | Listar marcos e entregas por situação | SharePoint |
| `consultar_riscos` | Treinado no MVP | _a configurar_ | Listar riscos com severidade e tratamento | SharePoint |
| `consultar_problemas` | Treinado no MVP | _a configurar_ | Listar problemas materializados e encaminhamento | SharePoint |
| `consultar_aderencia_normativa` | Treinado no MVP | _a configurar_ | Verificar conformidade com normativos | SharePoint |
| `consultar_documento_projeto` | Treinado no MVP | _a configurar_ | Busca semântica em documentos do projeto (bloco C5) | SharePoint |
| `consultar_conceito_gestao` | Treinado no MVP | _a configurar_ | Responder sobre conceitos e normativos da metodologia | SharePoint |
| `consultar_faturas_vencidas` | Pendente de validação | _não configurar_ | Listar faturas e pagamentos em atraso | _a definir_ |

## Categoria consulta — família análise comparativa

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `comparar_projetos` | Documentado, não treinado | _a configurar_ | Comparar projetos/subportfólios por dimensão | Power BI |
| `consultar_indicadores_portfolio` | Documentado, não treinado | _a configurar_ | Ler indicadores agregados do portfólio | Power BI |

## Categoria consulta — família geração de material

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `gerar_relatorio_status` | Documentado, não treinado | _a configurar_ | Montar prévia do relatório de status | Power BI, SharePoint |
| `gerar_previa_diretoria` | Documentado, não treinado | _a configurar_ | Montar prévia da apresentação para a diretoria | Power BI, SharePoint |
| `gerar_relatorio_encerramento` | Documentado, não treinado | _a configurar_ | Montar prévia do relatório de fechamento | Power BI, SharePoint |

## Categoria transação

Todas as intenções desta categoria exigem confirmação prévia do usuário antes da
efetivação e registro de origem, autoria e momento (RF05, RNF02) — modelado em DS03.
No middleware, a marcação é a propriedade `Intencao.exige_confirmacao`.

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `criar_projeto` | Treinado no MVP | _a configurar_ | Abrir projeto no portfólio (preenchimento em múltiplos turnos) | SharePoint, Power Automate |
| `atualizar_avanco` | Treinado no MVP | _a configurar_ | Registrar percentual de avanço | SharePoint, Power Automate |
| `atualizar_cronograma` | Treinado no MVP | _a configurar_ | Alterar datas, fases ou prazos | SharePoint, Power Automate |
| `registrar_risco` | Treinado no MVP | _a configurar_ | Incluir/atualizar risco | SharePoint, Power Automate |
| `registrar_problema` | Treinado no MVP | _a configurar_ | Incluir/atualizar problema | SharePoint, Power Automate |
| `atualizar_termo_abertura` | Treinado no MVP | _a configurar_ | Preencher ou revisar o termo de abertura | SharePoint, Power Automate |
| `registrar_entrega_marco` | Documentado, não treinado | _a configurar_ | Incluir ou concluir entregas e marcos | SharePoint, Power Automate |
| `atualizar_mapa_beneficios` | Documentado, não treinado | _a configurar_ | Atualizar o mapa de benefícios | SharePoint, Power Automate |
| `registrar_mudanca` | Documentado, não treinado | _a configurar_ | Registrar solicitação/aprovação de mudança | SharePoint, Power Automate |
| `encerrar_projeto` | Documentado, não treinado | _a configurar_ | Encerrar formalmente o projeto | SharePoint, Power Automate |

## Categoria alerta

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `consultar_pendencias` | Treinado no MVP | _a configurar_ | Levantar dados ausentes, desatualizados ou inconsistentes | Power Automate |

## Classe negativa

| Intenção (catálogo) | Status no MVP | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|---|
| `fora_de_escopo` | Treinado no MVP | _não se aplica_ | Recusa orientativa produzida pelo bloco C6, sem acionar o Copilot | Nenhum |
| `tentativa_injecao` | Treinado no MVP | _não se aplica_ | Bloqueio seco com alerta de segurança (`BLOQUEADA_INJECAO_MODELO`), sem acionar o Copilot e sem revelar o motivo ao usuário | Nenhum |

> Os nomes dos tópicos serão preenchidos quando o ambiente Copilot Studio for
> provisionado no tenant do parceiro (sprints técnicas).
