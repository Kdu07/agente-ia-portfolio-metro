# Mapeamento intenção → tópico/ação do Copilot Studio

Este arquivo é o **contrato entre o middleware e o Copilot Studio**: cada intenção
do catálogo (`src/middleware/app/pipeline/intent/catalog.py`) corresponde a um
tópico/ação configurado no Copilot. Toda alteração no catálogo ou nos tópicos deve
ser refletida aqui, na mesma mudança.

| Intenção (catálogo) | Tópico no Copilot Studio | Ação executada | Conectores usados |
|---|---|---|---|
| `consultar_projeto` | _a configurar_ | Buscar documentos e status do projeto | SharePoint |
| `atualizar_projeto` | _a configurar_ | Criar/atualizar registros do projeto | SharePoint, Power Automate |
| `listar_pendencias` | _a configurar_ | Levantar pendências e disparar alertas | Power Automate |
| `comparar_portfolio` | _a configurar_ | Consolidar dados comparativos do portfólio | Power BI |
| `gerar_relatorio` | _a configurar_ | Gerar prévia de relatório gerencial | Power BI, SharePoint |

> Os nomes dos tópicos serão preenchidos quando o ambiente Copilot Studio for
> provisionado no tenant do parceiro (sprints técnicas).
