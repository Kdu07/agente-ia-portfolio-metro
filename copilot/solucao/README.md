# Sem exports da solution do Copilot Studio

Esta pasta **não** versiona o export da *solution* do Copilot Studio e deve
permanecer vazia. Ela existe só para registrar a proibição no lugar em que
alguém procuraria o export.

## A restrição

Na liberação do ambiente, em 04/09/2026, o parceiro determinou que os agentes
criados **não sejam exportados nem publicados em repositórios**. O arquivo
exportado contém links para o SharePoint e conexões com outros serviços do
ambiente restrito, e o repositório não é lugar para nenhum dos dois. O risco
correspondente é o `R23`, na seção 4 de
[GestaoProjeto.md](../../docs/GestaoProjeto.md#4-gestão-de-riscos-e-oportunidades).

## O que não entra no repositório

- o `.zip` exportado da *solution*, em qualquer nome ou versão;
- a *solution* descompactada (XML, JSON ou YAML de tópicos, fluxos e conexões);
- links e URLs do ambiente do parceiro: site do SharePoint, Copilot Studio,
  Power Platform;
- identificadores de ambiente, de tenant ou de conexão;
- credenciais, tokens ou segredos do Direct Line.

## Onde fica a configuração do agente

Só como **descrição**, sem links nem conexões do ambiente:

- [../topicos.md](../topicos.md) — qual intenção do catálogo aciona qual
  tópico ou ação;
- [../conectores.md](../conectores.md) — conectores habilitados e escopo de
  permissão.

Backup, restauração e migração da configuração ficam no próprio ambiente do
parceiro, sob a governança dele. A demonstração final acontece lá.

## Barreiras

- O `.gitignore` ignora tudo nesta pasta além deste README. Um export colocado
  aqui por engano não aparece no `git status`.
- A revisão de merge request recusa qualquer arquivo de *solution*, inclusive
  um adicionado à força (`git add -f`) ou fora desta pasta.

## Se um export chegar ao repositório

Seguir a contingência do `R23`: remover o arquivo, reescrever o histórico da
branch afetada antes do merge, comunicar à orientadora e ao parceiro e pedir a
rotação dos links e das credenciais expostos. Remover o arquivo não basta,
porque o conteúdo continua no histórico.
