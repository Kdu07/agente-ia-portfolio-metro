# Glossário de Domínio do Canal de Voz

Documento de apoio à seção 5.7 do `Projeto.md`. Consolida o vocabulário próprio da gestão de portfólio do Metrô de São Paulo cuja transcrição correta é condição para que o pipeline de PLN identifique a intenção e as entidades do enunciado falado.

## 1. Finalidade

Este documento não é um dicionário para leitura humana. É um artefato de engenharia com duas funções determinadas: alimentar o mecanismo de vocabulário customizado do serviço de reconhecimento de fala selecionado na seção 5.7.2.5 e servir de conjunto de referência para o cálculo do indicador de acurácia de termos de domínio definido na seção 3.1.5.2. Sua existência é a mitigação declarada do risco **R03** — baixa acurácia no jargão da companhia, severidade 9, registrado como aberto —, e é também a condição de possibilidade do critério C1 da seleção de serviços, ao qual foi atribuído o peso máximo justamente porque o suporte a vocabulário customizado era a única alternativa técnica de tratamento daquele risco.

A razão de existirem dois indicadores distintos para o canal de voz, e não apenas o *Word Error Rate*, está na distribuição desigual da carga informacional do enunciado. O WER trata todos os tokens como equivalentes, o que é apropriado para transcrição de propósito geral e inadequado para este domínio. Considere-se o enunciado "qual a aderência do PRJ-2024-018 à NOR-00-223", com oito tokens, dos quais dois — o código do projeto e o código do normativo — concentram toda a informação discriminante: os seis restantes indicam apenas que se trata de uma consulta de aderência normativa, o que a intenção já resolve. Transcrever corretamente os seis e errar os dois produz um WER de vinte e cinco por cento, e uma consulta que aponta para nenhum objeto existente. Transcrever corretamente os sete primeiros e errar apenas o normativo produz um WER de doze e meio por cento, dentro da meta de quinze por cento estabelecida em 3.1.5.2, e uma resposta confiante sobre a norma errada — o pior desfecho possível, porque é indistinguível de uma resposta correta para quem a recebe. O indicador de acurácia de termos de domínio existe para tornar visível exatamente esse erro, e este glossário é a lista sobre a qual ele é computado.

## 2. Como o glossário é consumido

### 2.1 Injeção no reconhecimento

O serviço adotado admite o fornecimento de uma lista de frases na própria requisição de reconhecimento, aplicada em tempo de execução sobre o modelo base, sem etapa de treinamento e sem endpoint dedicado. Os termos deste glossário são enviados por esse mecanismo a cada sessão de reconhecimento, elevando a probabilidade a priori das sequências listadas sem impedir o reconhecimento de qualquer outra.

O mecanismo tem um teto documentado: **uma lista de frases não deve conter mais de quinhentas entradas**. Acima desse volume, a documentação do fornecedor orienta a migração para modelo customizado, com treinamento próprio, custo de assinatura e ciclo de publicação — alternativa fora do recorte do MVP tanto pelo enquadramento de custo da seção 5.7.2.7 quanto pelo prazo do módulo. O teto é, portanto, uma restrição de projeto e não um detalhe de implementação: ele obriga o glossário a ser seletivo, e é a razão de cada verbete registrar uma criticidade. A política de seleção está na seção 6.

### 2.2 Medição do indicador

O indicador de acurácia de termos de domínio de 3.1.5.2 é a razão entre os termos do glossário transcritos corretamente e o total de ocorrências desses termos. O denominador não é arbitrário: é o número de ocorrências dos verbetes deste documento nas transcrições de referência do corpus de áudio descrito em 5.7.6. Cada verbete é, nesse sentido, uma unidade de medida — o glossário define o que conta como acerto antes de haver o que medir, e não depois, o que preserva a validade do indicador contra ajuste retroativo do conjunto de referência.

A meta declarada é de noventa por cento. Ela só é perseguível porque o serviço escolhido admite o mecanismo descrito em 2.1; sob qualquer das alternativas eliminadas em 5.7.2.3, a meta seria inatingível por ausência de mecanismo, e não por insuficiência de qualidade do reconhecimento.

### 2.3 Uso subsidiário na extração de entidades

O mesmo vocabulário serve à normalização das entidades extraídas do enunciado, já transcrito, pelo pipeline de PLN. O uso é subsidiário e está registrado aqui para que a equipe não mantenha duas listas divergentes do mesmo domínio: o glossário é a fonte única, e eventual necessidade específica da extração deve ser resolvida por acréscimo de campo ao verbete, não por lista paralela.

## 3. Critério de inclusão e de exclusão

Um termo entra no glossário quando satisfaz as três condições cumulativamente.

A primeira é **pertencer ao domínio**: o termo aparece em documento do parceiro — o TAPI ou seus anexos —, no catálogo de intenções da seção 5.4.4 ou no corpus de treino do classificador. Termo que não tem origem verificável em nenhuma dessas fontes não entra, ainda que plausível.

A segunda é ser **foneticamente frágil em português brasileiro**: sigla soletrada, código alfanumérico, estrangeirismo, nome próprio de baixa frequência no português geral ou expressão cuja pronúncia admite mais de uma grafia razoável. Um termo que o modelo base já reconhece com segurança não se beneficia da injeção e apenas consome uma das quinhentas posições disponíveis.

A terceira é a **consequência do erro**: sua transcrição incorreta precisa alterar a intenção classificada ou a entidade extraída. Erro que o contexto da frase corrige, ou que afeta apenas a fluência da transcrição, não justifica ocupar o orçamento da lista.

Ficam explicitamente **excluídos** três conjuntos.

Os termos de português geral, ainda que muito frequentes no corpus — "projeto", "prazo", "relatório", "avanço" —, porque o modelo base os reconhece sem auxílio e porque cada um deles deslocaria um termo que efetivamente precisa da ajuda.

Os marcadores de redação `XPTO` e `123XXX`, que aparecem vinte e duas e nove vezes no corpus de treino respectivamente. Não são vocabulário: são espaços reservados usados na redação dos exemplos do catálogo em lugar de nomes e códigos reais. Injetá-los na lista de frases enviesaria o reconhecedor a favor de sequências que nenhum usuário pronuncia, degradando o reconhecimento de nomes de projeto legítimos — o efeito oposto ao pretendido. O registro desta exclusão é deliberado, porque a extração automática de candidatos a partir do corpus os traria para cá sem que nada, no dado, sinalizasse que não pertencem.

Os dados classificados como Corporativo nos anexos do parceiro — valores financeiros, percentuais de desempenho físico e econômico, nomes de pessoas e de fornecedores. O glossário admite dos anexos apenas a terminologia metodológica e o vocabulário público da rede metroviária, que é informação de domínio público divulgada pela própria companhia. A regra decorre das restrições de confidencialidade do TAPI e do RNF01, e vale independentemente de o repositório ser privado.

## 4. Estrutura do registro

Cada verbete é registrado com cinco campos.

| Campo | Conteúdo |
|---|---|
| **Termo** | Forma canônica, tal como deve aparecer na transcrição e tal como é enviada à lista de frases. |
| **Variantes faladas** | O que o microfone efetivamente recebe. Registra a leitura oral do termo escrito e as formas alternativas de pronúncia observadas ou previstas. |
| **Categoria** | Agrupamento do termo, correspondente às subseções da seção 5. |
| **Origem** | Fonte que autoriza a inclusão, conforme a primeira condição da seção 3. Permite auditar o glossário contra as fontes e remover verbetes quando a fonte muda. |
| **Criticidade** | Grau de consequência do erro de transcrição, conforme a escala abaixo. Governa a seleção quando o teto de quinhentas entradas apertar. |

O campo **variantes faladas** merece explicação, por não ser evidente. O termo `PRJ-2024-018` é uma forma escrita; ninguém a pronuncia. O usuário diz "pê érre jota dois mil e vinte e quatro dezoito", ou "projeto dois mil e vinte e quatro traço zero dezoito", ou ainda "pê érre jota vinte e quatro zero dezoito". A lista de frases recebe a forma escrita, que é o alvo do reconhecimento; a regra de aceitação do indicador, porém, precisa considerar que mais de uma superfície pode corresponder à mesma transcrição correta, sob pena de contabilizar como erro uma normalização legítima. O campo existe para tornar essa distinção explícita antes da medição, e não durante a análise dos resultados.

A escala de criticidade tem três níveis.

**Alta** — o erro faz a consulta apontar para outro objeto do portfólio ou para nenhum, e a resposta produzida é indistinguível de uma resposta correta. É o caso dos códigos, dos normativos e dos nomes próprios de projeto.

**Média** — o erro degrada a extração de entidades, mas o contexto do enunciado ou a confirmação prévia da transação permitem recuperação. É o caso do vocabulário metodológico de gestão.

**Baixa** — o erro afeta a fluência da transcrição sem alterar intenção nem entidade. Verbetes de criticidade baixa são registrados por completude do vocabulário, mas são os primeiros a sair da lista de frases quando o teto for atingido.

## 5. Termos

As subseções seguintes organizam os verbetes por natureza do termo, e não por intenção ou por área do portfólio. A escolha é deliberada: o que determina se um termo precisa de auxílio no reconhecimento é a sua forma — sigla, código, expressão composta, nome próprio —, não o assunto de que trata. Um agrupamento por intenção repetiria o mesmo termo em várias listas e dificultaria a verificação do teto de quinhentas entradas.

As contagens de ocorrência citadas referem-se ao corpus de treino do classificador, `src/middleware/dados/treino-intencoes.csv`, com 1.779 enunciados, e somam as variações de caixa alta e baixa do mesmo termo.

### 5.1 Siglas institucionais e de gestão

| Termo | Variantes faladas | Origem | Criticidade |
|---|---|---|---|
| `CCO` | "cê cê ó" | Corpus (37 ocorrências); Anexo 3 | Alta |
| `CBTC` | "cê bê tê cê"; "cibitici" | Corpus (31) | Alta |
| `TAP` | "tap"; "tê a pê" | Corpus (13); Anexo 1; catálogo 5.4.4 (`atualizar_termo_abertura`) | Alta |
| `CFTV` | "cê éfe tê vê" | Corpus (4) | Alta |
| `EAP` | "e a pê"; "eap" | Corpus (6) | Média |
| `CPI` | "cê pê i" | Corpus (5) | Alta |
| `SPI` | "esse pê i" | Corpus (2) | Alta |
| `KPI` | "cá pê i"; "kei pi ai" | Corpus (2) | Média |
| `PMO` | "pê ême ó" | Corpus (1); catálogo 5.4.4 (`consultar_conceito_gestao`) | Média |
| `GPM` | "gê pê ême" | Anexo 1 | Média |
| `CETESB` | "cetésbi" | Corpus (1) | Média |
| `ART` | "a érre tê"; "arte" | Corpus (1) | Alta |
| `GoA3` | "gô a três"; "gôa três" | Anexo 3 | Média |
| `HIS` | "agá i esse"; "is" | Anexo 3 | Média |
| `DUP` | "dupi"; "dê u pê" | Anexo 3 | Média |

Três observações sobre esta tabela.

`ART` recebe criticidade alta por um motivo que não é a sua frequência, que é mínima, mas a sua **colisão com uma palavra comum**. A leitura soletrada "a érre tê" e a leitura silábica "arte" são ambas plausíveis para o falante, e a segunda é homófona de um substantivo corrente do português. O modelo base, sem auxílio, tenderá sempre à palavra comum, porque é ela que tem probabilidade a priori mais alta. É exatamente o caso em que a injeção do termo muda o resultado, e é o caso que a segunda condição da seção 3 pretende capturar.

`CBTC` admite duas leituras igualmente correntes entre profissionais do setor — a soletrada e a aglutinada —, e o campo de variantes registra ambas para que a regra de aceitação do indicador não penalize a transcrição que corresponde à pronúncia efetivamente usada.

`GPM` entra pela origem verificável no Anexo 1, que a menciona como a equipe de apoio técnico e metodológico aos subportfólios, mas **sua expansão não está declarada em nenhum documento disponível à equipe**. O verbete é registrado com a sigla e sem expansão, e a confirmação do nome por extenso fica pendente de validação com o parceiro. Registrar a lacuna é preferível a preenchê-la por inferência: uma expansão inventada entraria na documentação com aparência de fato apurado.

Não entram nesta tabela as siglas que aparecem exclusivamente nos enunciados da classe `tentativa_injecao` — `SQL`, `DROP`, `TABLE`. São vocabulário de ataque, presentes no corpus porque o classificador precisa aprender a reconhecê-las como tal, e não terminologia do domínio. Injetá-las na lista de frases elevaria a probabilidade de o reconhecedor produzir justamente as sequências que o pipeline existe para barrar.

### 5.2 Padrões de código e identificadores

| Padrão | Exemplos observados | Como é falado | Criticidade |
|---|---|---|---|
| `PRJ-AAAA-NNN` — código de projeto | `PRJ-2024-018` (47 ocorrências); `PRJ-2025-042` (43); `PRJ-2026-001` (6); `PRJ-2026-077` (6); `PRJ-2025-190` (5) | "pê érre jota dois mil e vinte e quatro zero dezoito"; "projeto dois mil e vinte e quatro traço zero dezoito" | Alta |
| `NOR-NN-NNN` — normativo interno | `NOR-07-041` (3); `NOR-00-223` (3); `NOR-01-105` (3); `NOR-12-008` (1) | "nor zero sete zero quarenta e um"; "ene ó érre zero sete zero quatro um" | Alta |
| `IN-NN/AAAA` — instrução normativa | `IN-04/2023` (4); `IN-11/2024` (4) | "i ene zero quatro barra dois mil e vinte e três"; "instrução normativa zero quatro de dois mil e vinte e três" | Alta |

Estes três padrões exigem tratamento distinto do restante do glossário, por uma limitação do mecanismo descrito em 2.1: **a lista de frases aceita cadeias literais, não expressões regulares**. Não é possível injetar `PRJ-AAAA-NNN` como padrão e esperar que o reconhecedor generalize para qualquer ano e qualquer número sequencial. A parte variável do código pertence a um conjunto aberto que cresce a cada projeto aberto no portfólio.

A estratégia adotada é, portanto, em duas camadas. A primeira injeta **os prefixos isolados** — `PRJ`, `NOR`, `IN` —, que são a parte foneticamente frágil: são siglas soletradas de três letras ou menos, e é nelas que o modelo base erra, produzindo "por dois mil e vinte e quatro" ou "projeto dois mil e vinte e quatro" onde deveria haver `PRJ-2024`. A segunda injeta **o conjunto finito de códigos que existem no ambiente de teste**, listados na coluna de exemplos acima, que é pequeno o bastante para caber no orçamento e cobre integralmente os enunciados do corpus de avaliação. A parte numérica fica a cargo do modelo base, que reconhece dígitos e numerais em português brasileiro com qualidade suficiente e não se beneficia da injeção.

Esta estratégia tem uma consequência que precisa ficar registrada: **ela não escala para a base real de projetos do parceiro**. Quando a solução passar a operar sobre o portfólio efetivo, a lista de códigos concretos deixará de ser um conjunto fixo redigido à mão e precisará ser gerada a partir da base de projetos a cada sessão, ou substituída por modelo customizado, se o volume de códigos ultrapassar o teto. O ponto está registrado aqui e retomado na política de manutenção da seção 7.

Há ainda uma regra de comparação que decorre destes padrões. A mesma referência pode ser transcrita como `PRJ-2024-018`, `PRJ 2024 018`, `prj-2024-018` ou `PRJ2024018`, e todas as quatro correspondem ao mesmo objeto do portfólio. A regra de aceitação do indicador de 3.1.5.2 **normaliza caixa, hífens, barras e espaços antes de comparar**, contabilizando como erro apenas a divergência nos caracteres significativos. Sem essa normalização, o indicador mediria a formatação da transcrição e não o reconhecimento do código, que é o que ele existe para medir.

### 5.3 Vocabulário de gestão de portfólio

| Termo | Variantes faladas | Origem | Criticidade |
|---|---|---|---|
| `subportfólio` | "subportifólio"; "sub portfólio"; "subiportifólio" | Catálogo 5.4.4 (entidade `subportfolio`, 246 ocorrências no corpus); Anexos 1 e 3 | Alta |
| `portfólio` | "portifólio"; "portifolio" | Catálogo 5.4.4; TAPI | Média |
| `marco` | "marco"; "marcos" | Catálogo 5.4.4 (entidade `marco`, 134 ocorrências); Anexo 1 | Alta |
| `entrega` | "entrega"; "entregas" | Catálogo 5.4.4 (entidade `entrega`, 120); Anexo 1 | Média |
| `mapa de benefícios` | "mapa de benefícios" | Catálogo 5.4.4 (`atualizar_mapa_beneficios`); Anexo 1 | Média |
| `termo de abertura` | "termo de abertura"; "termo de abertura do projeto" | Catálogo 5.4.4 (`atualizar_termo_abertura`); Anexo 1 | Média |
| `aderência normativa` | "aderência normativa"; "aderência às normas" | Catálogo 5.4.4 (`consultar_aderencia_normativa`) | Alta |
| `aderência física` | "aderência física" | Anexo 3 | Média |
| `aderência econômica` | "aderência econômica" | Anexo 3 | Média |
| `avanço físico` | "avanço físico" | Corpus; Anexo 1 | Média |
| `criticidade` | "criticidade" | Corpus; documento de histórias de usuário | Média |
| `severidade` | "severidade" | Catálogo 5.4.4 (entidade `severidade`, 60) | Média |
| `escalonamento` | "escalonamento"; "escalar para a diretoria" | Documento de histórias de usuário | Média |
| `plano de ação` | "plano de ação" | Documento de histórias de usuário | Baixa |
| `solução de contorno` | "solução de contorno" | Documento de histórias de usuário | Média |
| `partida do portfólio` | "partida do portfólio" | Anexo 1 | Média |
| `balanço do portfólio` | "balanço do portfólio" | Anexo 2 | Média |
| `fechamento do portfólio` | "fechamento do portfólio"; "relatório anual de fechamento" | Anexos 3 e 4; catálogo 5.4.4 (`gerar_relatorio_encerramento`) | Média |
| `fase de comissionamento` | "fase de comissionamento" | Corpus (4) | Alta |
| `fase de licenciamento` | "fase de licenciamento" | Corpus (8) | Média |

Dois verbetes desta tabela recebem criticidade alta por razões que merecem registro, porque nenhuma delas é a frequência.

`subportfólio` é a unidade de agregação do domínio, e sua distinção de `portfólio` repousa inteiramente sobre um prefixo de duas sílabas átonas, pronunciadas rapidamente e frequentemente elididas na fala corrente. Uma consulta como "como está o portfólio de expansão" e outra como "como está o subportfólio de expansão" referem-se a níveis diferentes de agregação e devem produzir respostas diferentes; perder o prefixo na transcrição não gera erro visível, gera uma resposta correta para a pergunta errada. É o mesmo padrão de falha descrito na seção 1 — o erro que não se anuncia.

`marco` é criticidade alta pela **proximidade fonética com "março"**. Em fala rápida, "o marco de conclusão" e "o março de conclusão" são difíceis de separar, e o domínio torna as duas leituras plausíveis: uma consulta de cronograma pode legitimamente mencionar tanto um marco quanto um mês. A ambiguidade não se resolve pelo contexto sintático, porque ambos ocupam a mesma posição na frase. É exatamente o tipo de caso em que elevar a probabilidade a priori do termo do domínio altera o desfecho.

`fase de comissionamento` entra com criticidade alta porque *comissionamento* é termo técnico de baixa frequência no português geral, e a transcrição incorreta desloca a entidade `fase` para um valor inexistente no catálogo, o que faz a consulta de cronograma retornar vazio em vez de retornar errado — falha menos perigosa que a de `marco`, mas ainda assim uma falha que o usuário não consegue diagnosticar.
