# Conectores e permissões do Copilot Studio

Registro de governança: quais conectores o agente do Copilot Studio tem
habilitados e com que escopo de permissão. Princípio aplicado: **menor
privilégio** — cada conector recebe apenas o acesso necessário às ações
mapeadas em [topicos.md](topicos.md). Essa limitação por design é parte da
defesa contra prompt injection: mesmo que uma injeção alcance o Copilot, o
raio de dano fica restrito às ações aqui listadas.

| Conector | Escopo/Recurso | Permissão | Justificativa |
|---|---|---|---|
| SharePoint | _site do portfólio (a definir)_ | Leitura/escrita em listas e documentos do portfólio | Consulta e atualização de projetos |
| Power BI | _workspace do portfólio (a definir)_ | Leitura de datasets/relatórios | Análises comparativas e prévias de relatórios |
| Power Automate | _fluxos de pendências (a definir)_ | Execução de fluxos específicos | Alertas e apoio proativo a pendências |

> Preencher os recursos concretos quando o ambiente for provisionado.
> Qualquer novo conector exige atualização deste documento antes da habilitação.
