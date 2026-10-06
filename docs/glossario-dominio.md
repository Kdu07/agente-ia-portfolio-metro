# Glossário de Domínio do Canal de Voz

Documento de apoio à seção 5.7 do `Projeto.md`. Consolida o vocabulário próprio da gestão de portfólio do Metrô de São Paulo cuja transcrição correta é condição para que o pipeline de PLN identifique a intenção e as entidades do enunciado falado.

## Sumário

- [1. Finalidade](#1-finalidade)
- [2. Como o glossário é consumido](#2-como-o-glossário-é-consumido)
- [3. Critério de inclusão e de exclusão](#3-critério-de-inclusão-e-de-exclusão)
- [4. Estrutura do registro](#4-estrutura-do-registro)
- [5. Termos](#5-termos)
- [6. Restrições operacionais](#6-restrições-operacionais)
- [7. Manutenção e rastreabilidade](#7-manutenção-e-rastreabilidade)
- [8. Verificação empírica do mecanismo](#8-verificação-empírica-do-mecanismo)

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

### 5.4 Vocabulário público da rede metroviária

Os termos desta subseção são informação de domínio público, divulgada pela própria companhia em seus canais e sinalização. Entram no glossário por serem os topônimos e designações que o usuário efetivamente pronuncia ao se referir a um projeto, e não por qualquer conteúdo dos anexos classificados.

| Termo | Variantes faladas | Origem | Criticidade |
|---|---|---|---|
| `Linha 2-Verde` | "linha dois verde"; "linha dois" | Anexo 3 | Alta |
| `Linha 4-Amarela` | "linha quatro amarela"; "linha quatro" | Anexo 3; corpus | Alta |
| `Linha 15-Prata` | "linha quinze prata"; "linha quinze" | Anexo 3 | Alta |
| `Linha 17-Ouro` | "linha dezessete ouro"; "linha dezessete" | Anexo 3; corpus | Alta |
| `Linha 19-Celeste` | "linha dezenove celeste" | Anexo 3 | Alta |
| `Linha 22-Marrom` | "linha vinte e dois marrom" | Anexo 3 | Alta |
| `Estação Vila Prudente` | "estação vila prudente" | Anexo 3 | Média |
| `Estação São Joaquim` | "estação são joaquim" | Anexo 3 | Média |
| `Estação Morumbi` | "estação morumbi" | Corpus (28) | Média |
| `Estação Brooklin` | "estação bruclim"; "estação brooklin" | Corpus (24) | Alta |
| `Sé` | "sé"; "estação sé" | Corpus (24) | Alta |
| `Vila Sônia` | "vila sônia" | Corpus (25) | Média |
| `Jabaquara` | "jabaquara" | Corpus (28) | Média |
| `Itaquera` | "itaquera" | Corpus (26) | Média |
| `Água Espraiada` | "água espraiada" | Corpus (25); Anexo 3 | Média |
| `Pátio Oratório` | "pátio oratório" | Anexo 3 | Média |
| `Pátio Vila Medeiros` | "pátio vila medeiros" | Anexo 3 | Média |

Duas observações.

A designação das linhas segue o padrão **número mais cor**, e essa composição é redundante por construção: o número identifica a linha sozinho, e a cor também. A redundância é uma vantagem para o reconhecimento, e o glossário a preserva injetando **a forma composta inteira** — `Linha 15-Prata` — em vez do número e da cor separadamente. O motivo é prático: se o reconhecedor errar o numeral, transcrevendo "linha cinquenta" onde se disse "linha quinze", a cor remanescente ainda identifica o objeto e permite que a extração de entidades reconcilie. Injetar as partes isoladas destruiria essa propriedade, porque o reconhecedor deixaria de tratar o par como unidade.

`Sé` e `Estação Brooklin` recebem criticidade alta por razões opostas e igualmente instrutivas. `Sé` é um monossílabo homófono do verbo *sê* e próximo de *se*, a conjunção mais frequente do português — o pior cenário possível para um reconhecedor, porque a alternativa errada é ao mesmo tempo curta e altíssima em frequência. `Brooklin` é estrangeirismo com grafia que não corresponde à pronúncia brasileira corrente e que colide com o topônimo internacional *Brooklyn*, grafado com *y*; o campo de variantes registra as duas leituras para que a regra de aceitação não penalize a correta.

### 5.5 Vocabulário de engenharia e sistemas

| Termo | Variantes faladas | Origem | Criticidade |
|---|---|---|---|
| `via permanente` | "via permanente" | Corpus (26); Anexo 3 | Alta |
| `material rodante` | "material rodante" | Corpus; Anexo 3 | Alta |
| `portas de plataforma` | "portas de plataforma" | Anexo 3 | Média |
| `monotrilho` | "monotrilho" | Corpus (26) | Média |
| `subestação` | "subestação" | Corpus (25) | Média |
| `bilhetagem` | "bilhetagem" | Corpus (3) | Média |
| `sinalização` | "sinalização" | Corpus (30) | Baixa |
| `comissionamento` | "comissionamento" | Corpus (4) | Alta |
| `desapropriação` | "desapropriação" | Anexo 3 | Média |
| `licenciamento ambiental` | "licenciamento ambiental" | Corpus (8) | Média |
| `obras civis` | "obras civis" | Corpus (8) | Baixa |
| `interligação` | "interligação" | Anexo 3 | Baixa |

`via permanente` e `material rodante` são os dois casos de criticidade alta desta tabela, e pela mesma razão: **são termos técnicos compostos por palavras comuns do português**. Cada um dos quatro vocábulos — via, permanente, material, rodante — é reconhecido sem dificuldade isoladamente, e é justamente por isso que o modelo base tende a transcrevê-los como sequência de palavras avulsas em vez de unidade terminológica. O erro não aparece na transcrição, que sai correta caractere a caractere; aparece adiante, quando a extração de entidades procura um termo do domínio e encontra dois adjetivos. É a falha mais difícil de diagnosticar de todas as descritas neste documento, porque não há nada de errado no texto produzido.

### 5.6 Nomes de projeto do ambiente de teste

Os nomes desta subseção **não correspondem a projetos reais do parceiro**. São designações sintéticas, construídas para o ambiente de teste combinando topônimos públicos da rede com verbos de ação de projeto, e é a elas que os enunciados do corpus de treino e do corpus de avaliação de áudio se referem.

| Nome | Ocorrências no corpus | Criticidade |
|---|---|---|
| `Modernização do Trecho Sul` | 32 | Alta |
| `Terminal Jabaquara` | 28 | Alta |
| `Acessibilidade Linha 4` | 27 | Alta |
| `Monotrilho Ouro` | 26 | Alta |
| `Reforma do Pátio Itaquera` | 26 | Alta |
| `Via Permanente Trecho Norte` | 26 | Alta |
| `Sistema de Sinalização` | 30 | Alta |
| `Estação Morumbi` | 28 | Alta |
| `Estação Brooklin` | 24 | Alta |
| `Pátio Água Espraiada` | 25 | Alta |
| `Subestação Vila Sônia` | 25 | Alta |
| `Requalificação da Sé` | 24 | Alta |
| `Expansão Leste` | 23 | Alta |
| `Ampliação do Terminal Norte` | 5 | Média |
| `Duplicação do Trecho Oeste` | 3 | Média |
| `Reforma da Estação Central` | 3 | Média |
| `Projeto Piloto de Bilhetagem` | 3 | Média |
| `Implantação de CFTV` | 3 | Média |

Todos recebem criticidade alta ou média pela mesma razão estrutural: são **valores da entidade `projeto`**, que é a entidade mais frequente do catálogo, esperada por vinte e uma das vinte e oito intenções e presente em 1.326 dos 1.779 enunciados do corpus. Errar o nome do projeto não degrada a resposta — inutiliza a consulta inteira, porque não há sobre o que responder.

Registram-se aqui também os subportfólios mencionados nos enunciados: `obras civis`, `sistemas`, `expansão`, `manutenção` e `material rodante`. São designações genéricas do ambiente de teste. As denominações oficiais dos subportfólios do parceiro **não foram incorporadas ao glossário** nesta versão: constam de anexos classificados como Corporativo, e sua inclusão será submetida à validação do parceiro antes de entrar, conforme a terceira exclusão da seção 3. A decisão é conservadora por escolha — o custo de omitir um termo é uma acurácia menor no indicador, mensurável e corrigível; o custo de publicar uma designação interna indevidamente não é reversível.

Esta subseção inteira tem **prazo de validade**. Ela existe porque o ambiente de teste é sintético e porque os indicadores de 3.1.5.2 precisam ser calculáveis sobre ele. No momento em que a solução passar a operar sobre o portfólio real do parceiro, estes dezoito nomes deixam de descrever qualquer objeto existente e a subseção deve ser **substituída, não estendida** — mantê-los ao lado dos nomes reais gastaria orçamento da lista de frases favorecendo sequências que ninguém mais pronuncia, que é exatamente o defeito apontado na exclusão de `XPTO` na seção 3. O procedimento de substituição está na seção 7.

## 6. Restrições operacionais

### 6.1 Orçamento atual

A tabela abaixo consolida o estado do glossário nesta versão e o compara ao teto de quinhentas entradas do mecanismo descrito em 2.1.

| Subseção | Verbetes | Frases geradas | Alta | Média | Baixa |
|---|---|---|---|---|---|
| 5.1 — Siglas institucionais e de gestão | 15 | 15 | 7 | 8 | 0 |
| 5.2 — Padrões de código e identificadores | 3 | 14 | 14 | 0 | 0 |
| 5.3 — Vocabulário de gestão de portfólio | 20 | 20 | 4 | 15 | 1 |
| 5.4 — Vocabulário público da rede metroviária | 17 | 17 | 8 | 9 | 0 |
| 5.5 — Vocabulário de engenharia e sistemas | 12 | 12 | 3 | 6 | 3 |
| 5.6 — Nomes de projeto do ambiente de teste | 18 | 23 | 13 | 10 | 0 |
| **Total** | **85** | **101** | **49** | **48** | **4** |

A coluna **verbetes** conta as linhas das tabelas da seção 5; a coluna **frases geradas** conta o que efetivamente é enviado ao serviço. As duas divergem em dois pontos. Em 5.2, cada padrão gera o prefixo isolado mais os códigos concretos listados na coluna de exemplos, conforme a estratégia em duas camadas ali descrita: três padrões produzem três prefixos e onze códigos. Em 5.6, os cinco subportfólios registrados em prosa ao final da subseção somam-se aos dezoito nomes tabelados.

O glossário ocupa, portanto, **101 das 500 posições disponíveis**, ou pouco mais de um quinto do teto. A folga é deliberada e tem duas destinações previstas: o corpus de áudio de referência da subseção 5.7.6, cuja gravação pode revelar termos que a análise textual não antecipou, e a eventual substituição dos nomes sintéticos de 5.6 por nomes reais, que tende a ser mais numerosa do que o conjunto atual.

### 6.2 Política de seleção

Se uma versão futura ultrapassar o teto, a redução obedece a esta ordem, e não ao julgamento pontual de quem estiver editando:

1. Removem-se primeiro os verbetes de **criticidade baixa**, na ordem inversa de frequência de ocorrência. São quatro nesta versão, e por definição seu erro não altera intenção nem entidade.
2. Removem-se em seguida os verbetes de **criticidade média** cuja origem seja exclusivamente o corpus de treino, preservando os que têm origem em documento do parceiro. O critério é a evidência de uso real: um termo que só existe no corpus sintético tem menos garantia de ser efetivamente pronunciado.
3. Consolidam-se os verbetes de 5.6 que compartilham topônimo, mantendo o nome completo do projeto e dispensando a forma curta.
4. Só então se avalia a migração para modelo customizado, que é decisão de custo e de prazo, e não de redação deste documento.

Os verbetes de **criticidade alta nunca são removidos** para caber no teto. Se a lista de alta criticidade sozinha ultrapassar quinhentas entradas, o mecanismo deixou de ser adequado ao problema, e a resposta correta é o modelo customizado — não uma seleção arbitrária entre termos que, por definição, produzem resposta errada quando mal transcritos.

### 6.3 O que o mecanismo não faz

Três limitações precisam estar registradas, porque a ausência delas produziria expectativa equivocada sobre o indicador.

**A lista de frases não garante o reconhecimento.** Ela eleva a probabilidade a priori das sequências listadas; não as impõe. Um termo do glossário pronunciado de forma muito distante da esperada continuará sendo transcrito errado, e a meta de noventa por cento de acurácia — e não de cem — reflete exatamente isso.

**A lista não aceita padrões.** O ponto está desenvolvido em 5.2 e é repetido aqui porque é a limitação com maior consequência prática: nenhum conjunto aberto de identificadores pode ser coberto por este mecanismo.

**A lista corrige erros de segmentação, e não de substituição.** A documentação do fornecedor descreve o recurso e seu teto sem enumerar os idiomas em que ele opera, o que deixou em aberto, até a verificação registrada na seção 8, se o mecanismo sequer operava em português brasileiro. Opera. A limitação que restou, porém, é mais específica e mais consequente do que a dúvida original: quando o reconhecimento produz os fonemas corretos e erra apenas onde traçar a fronteira de palavra, a lista corrige; quando ele escolhe outra palavra que não a dita, a lista não corrige. A evidência está em 8.4 e o efeito sobre o alcance deste glossário, em 8.5.

## 7. Manutenção e rastreabilidade

### 7.1 Gatilhos de revisão

O glossário é revisado quando ocorre qualquer um destes eventos, e não em cadência de calendário:

| Evento | Efeito sobre o glossário |
|---|---|
| Alteração no catálogo de intenções (5.4.4) | Revisar as entidades esperadas; termo de entidade nova pode exigir verbete |
| Ampliação do corpus de treino | Reexecutar a extração de candidatos e avaliar os termos novos pelos critérios da seção 3 |
| Gravação do corpus de áudio (5.7.6) | Incorporar termos cuja fragilidade só se revele na fala |
| Medição do indicador abaixo da meta | Analisar quais verbetes falharam e se a falha é de cobertura ou de mecanismo |
| Migração para dados reais do parceiro | Substituir integralmente a subseção 5.6, conforme 7.2 |
| Novo documento normativo do parceiro | Avaliar siglas e códigos introduzidos |

### 7.2 Procedimento de substituição da subseção 5.6

Quando a solução passar a operar sobre o portfólio real, a subseção 5.6 é **substituída, e não estendida**. O procedimento tem quatro passos.

Primeiro, extrair da base de projetos do parceiro os nomes e códigos vigentes. Segundo, aplicar a eles os critérios da seção 3 — em especial o terceiro, de consequência do erro, que os classifica todos como criticidade alta por serem valores da entidade `projeto`. Terceiro, remover integralmente os dezoito nomes sintéticos e os cinco subportfólios genéricos da versão atual. Quarto, verificar o orçamento contra o teto de 6.1 e, se ultrapassado, aplicar a política de 6.2 ou decidir pela migração ao modelo customizado.

O terceiro passo é o que exige disciplina, porque é o único que não acrescenta nada e por isso é o que se esquece. Manter os nomes sintéticos ao lado dos reais não é conservadorismo inofensivo: é gastar orçamento elevando a probabilidade de sequências que nenhum usuário pronunciará, exatamente o defeito que motivou a exclusão de `XPTO` na seção 3.

Se o volume de códigos reais exceder o que cabe na lista, a geração deixa de ser manual: a lista de frases passa a ser montada por consulta à base de projetos no momento da emissão do token de voz, restringindo-se aos projetos sob a permissão do usuário da sessão. Esta alternativa tem a vantagem de reduzir a lista ao subconjunto relevante para cada usuário, mas **acopla a emissão do token a uma consulta de dados**, com efeito sobre a latência descrita em 5.7.3 e sobre o que o token revela — a própria lista de frases informaria ao navegador quais projetos existem. A decisão não pertence a este documento e fica registrada como alternativa avaliada, não adotada.

### 7.3 Versionamento e vínculo com a medição

O glossário é versionado junto com o repositório, e cada medição do indicador de acurácia de termos de domínio deve registrar **contra qual estado do glossário foi computada**, identificado pelo commit.

A exigência não é burocrática. O glossário define o denominador do indicador: acrescentar verbetes aumenta o número de ocorrências contabilizadas, e removê-los o reduz. Duas medições feitas contra glossários diferentes **não são comparáveis**, e uma série histórica que ignore isso registraria como melhora ou piora do reconhecimento aquilo que foi apenas mudança do que se decidiu medir. Registrar o commit junto do resultado é o que permite distinguir as duas coisas depois.

Pela mesma razão, **o glossário não deve ser alterado entre a gravação do corpus de áudio e a medição sobre ele**. Alterá-lo nesse intervalo permitiria ajustar o conjunto de referência à vista dos resultados, o que invalidaria o indicador — é o ponto já registrado em 2.2, aqui convertido em regra de procedimento.

### 7.4 Pendências abertas

| Pendência | O que falta | Bloqueia |
|---|---|---|
| Expansão da sigla `GPM` | Confirmar o nome por extenso com o parceiro; o Anexo 1 usa a sigla sem defini-la | Nada; o verbete opera sem a expansão |
| Denominações oficiais dos subportfólios | Submeter à validação do parceiro, por constarem de anexo classificado como Corporativo | Cobertura do glossário para consultas agregadas |
| Tratamento do ruído ambiente e da fala de terceiros | Especificar qualidade mínima do áudio e comportamento diante de fala não pertencente ao usuário | Confiabilidade da transcrição fora de ambiente controlado |
| Ordem de pronúncia dos códigos de projeto | Observar como o usuário efetivamente enuncia um código, no corpus de 5.7.6 e junto ao parceiro | Validade da estratégia de 5.2 |
| Magnitude do efeito da lista de frases | Medição sobre o corpus de áudio de 5.7.6, com amostra suficiente | Estimativa do indicador de 3.1.5.2 |
| Substituição da subseção 5.6 | Disponibilidade de dados reais do parceiro | Uso do glossário fora do ambiente de teste |
| Geração dinâmica dos códigos de projeto | Decisão sobre acoplar a emissão do token a consulta de dados | Escala do glossário para a base real |

A pendência sobre o suporte da lista de frases ao português brasileiro, registrada na versão anterior desta tabela, **está encerrada** pela verificação da seção 8. Em seu lugar entram três pendências mais precisas, que só puderam ser formuladas depois de haver observação.

Duas delas — a ordem de pronúncia dos códigos e a magnitude do efeito — condicionam afirmações que este documento já faz. A primeira sustenta a estratégia de 5.2; a segunda, a expectativa de que o mecanismo baste como mitigação do R03. Nenhuma das duas se resolve por leitura de documentação: ambas exigem observar fala real, o que é a função do corpus da subseção 5.7.6.

## 8. Verificação empírica do mecanismo

A seção 6.3 registrou que o suporte da lista de frases ao português brasileiro não está declarado na documentação do fornecedor, e que enquanto essa lacuna persistisse todo o efeito atribuído a este glossário seria hipótese. Esta seção registra a verificação que fecha aquela pendência e delimita, com honestidade, o que ela estabelece e o que não estabelece.

### 8.1 Procedimento

Foram construídos cinco enunciados, cada um exercitando um caso de criticidade alta declarado nas subseções da seção 5: os códigos de projeto e normativo de 5.2, a proximidade entre `marco` e *março* e o monossílabo `Sé` de 5.3 e 5.4, o prefixo átono de `subportfólio` de 5.3, o termo composto `via permanente` de 5.5 e a sigla `ART` de 5.1, homófona de palavra comum. Os enunciados não são amostra aleatória do domínio: são os casos que este documento afirma serem difíceis, escolhidos justamente para que a verificação pudesse contrariá-lo.

Cada enunciado foi gravado uma vez, por um único falante, em WAV de 16 kHz, 16 bits e canal único. Cada arquivo foi então transcrito **duas vezes, com a mesma configuração de serviço, região e idioma, diferindo apenas pela presença da lista de frases**. Como o áudio é bit a bit idêntico nas duas passagens, qualquer divergência entre as transcrições é atribuível ao mecanismo, e não à variação da fala — é essa a propriedade que torna o procedimento um teste, e não uma demonstração.

A comparação por termo aplicou as regras já fixadas neste documento: para códigos, a normalização de caixa, hífens, barras e espaços declarada em 5.2; para termos de texto, comparação de palavra inteira com **acentos preservados**, porque distinguir `marco` de *março* é precisamente o que se pretendia medir e uma normalização que dobrasse acentos aprovaria o erro.

Cabe registrar que o instrumento de medição precisou ele próprio ser corrigido durante a execução, e que os dois defeitos encontrados são instrutivos. O primeiro comparava códigos por subcadeia após remover os caracteres não alfanuméricos, de modo que a palavra *arte* satisfazia a busca pela sigla `ART` — o comparador reproduzia exatamente o erro que o documento existe para detectar, e classificava como acerto a falha que pretendia medir. O segundo usava reconhecimento de disparo único, que encerra no primeiro silêncio e descartava o restante do enunciado quando o falante pausava no meio da frase. Nenhum dos dois se manifestava como erro visível: ambos produziam números plausíveis. A lição, que vale para os indicadores de 3.1.5.2 em geral, é que um instrumento de medição também precisa ser verificado antes de se acreditar no que ele informa.

O script de verificação e a evidência bruta não são versionados. O script é ferramenta descartável, e a evidência é reproduzível a partir do procedimento aqui descrito.

### 8.2 O que ficou estabelecido

**A lista de frases opera em português brasileiro.** A evidência é direta e não depende de contagem: sobre o mesmo arquivo de áudio, a transcrição sem a lista produziu `sub portfólio`, em duas palavras, e a transcrição com a lista produziu `subportfólio`, na forma canônica registrada em 5.3. O resultado se reproduziu em duas execuções independentes. Efeito acessório na mesma direção: termos que o modelo base já reconhecia passaram a ser grafados na forma exata da lista, com a caixa alta dos verbetes.

Com isso, a terceira limitação registrada em 6.3 deixa de ser uma incógnita e passa a ser uma limitação de grau, não de existência: o mecanismo funciona no idioma do projeto, e a questão pertinente passa a ser **quanto** ele corrige, tratada na subseção seguinte.

### 8.3 Limitações da verificação

Três limitações delimitam o alcance do que foi verificado.

A primeira é o **tamanho da amostra**. Cada termo foi observado em uma única gravação, de um único falante, com fraseado controlado. Isso é suficiente para estabelecer que o efeito existe — um caso basta para refutar a hipótese de que o mecanismo não opera no idioma — e é insuficiente para estimar sua magnitude. Nenhuma taxa de acerto derivada deste procedimento deve ser lida como estimativa da acurácia esperada em operação; a estimativa é o que o corpus de áudio da subseção 5.7.6 existe para produzir.

A segunda é o **ruído ambiente**. Uma das gravações captou fala de terceiro no ambiente, que o serviço transcreveu como conteúdo do enunciado, acrescentando à transcrição frases que o usuário não disse. A observação extrapola o escopo deste glossário e revela uma lacuna na especificação do canal: nem a topologia de 5.7.1 nem os formatos e limites de 5.7.3 tratam de ruído ambiente, de fala de terceiros ou de qualidade mínima do áudio submetido. O ponto está registrado aqui por ter sido observado aqui, e pertence àquelas seções.

A terceira é uma **hipótese não verificada que este documento assume sem declarar**. A estratégia de 5.2 pressupõe que o usuário pronuncia os códigos na ordem escrita, soletrando o prefixo — *pê-érre-jota dois mil e vinte e quatro zero dezoito*. Se o uso corrente na companhia for outro, como *projeto dezoito de dois mil e vinte e quatro*, nenhuma lista de frases resolve, porque o problema deixa de ser reconhecimento e passa a ser interpretação: o serviço transcreve o que foi dito, na ordem em que foi dito, e não reordena. Como a verificação foi conduzida sob a pronúncia que o documento assume, ela não testou a suposição — apenas a tornou visível. Responder a isso exige observar como as pessoas do Metrô efetivamente falam, o que cabe ao corpus da subseção 5.7.6 e à validação com o parceiro.

### 8.4 Resultados

A tabela registra as nove observações. As transcrições são literais; a coluna de efeito classifica o que a presença da lista alterou.

| Termo | Sem lista | Com lista | Efeito da lista |
|---|---|---|---|
| `PRJ-2024-018` | `prj? 2024 zero 18` | `PRJ 2024 zero 18` | Grafia canônica |
| `NOR-00-223` | `ANOR 00223` | `a NOR 00223` | **Corrigido** |
| `marco` | `Marco` | `Marco` | Falha prevista não ocorreu |
| `Requalificação da Sé` | `da se` | `da se` | Nenhum |
| `subportfólio` | `sub portfólio` | `subportfólio` | **Corrigido** |
| `Via Permanente` | `Vila permanente` | `Vila permanente` | Nenhum |
| `Via Permanente Trecho Norte` | `trefunorte` | `trefro norte` | Alterou sem corrigir |
| `ART` | `arte` | `arte` | Nenhum |
| `Monotrilho Ouro` | `monotrilho ouro` | `Monotrilho Ouro` | Grafia canônica |

Dos nove termos, três foram transcritos corretamente sem a lista e cinco com ela. A leitura útil, porém, não está no placar, e sim no que distingue os dois termos corrigidos dos três que não foram.

**O que organiza os resultados é o tipo de erro que o reconhecimento cometeu**, e não a frequência do termo nem sua criticidade. Os erros observados se separam em duas classes.

Na primeira, o reconhecimento produziu os fonemas corretos e errou apenas **onde traçar a fronteira de palavra**: `sub portfólio` em duas palavras onde havia uma, e `ANOR` numa palavra onde havia a preposição seguida da sigla. São erros de **segmentação**. A lista corrigiu os dois.

Na segunda, o reconhecimento **escolheu outra palavra** que não a dita: *arte* por `ART`, *Vila* por `Via`, *se* por `Sé`. São erros de **substituição**. A lista não corrigiu nenhum dos três — no caso de `Via Permanente Trecho Norte` chegou a alterar a saída, de `trefunorte` para `trefro norte`, sem se aproximar da forma correta.

A explicação é compatível com o que 6.3 já afirmava sobre o mecanismo. A lista eleva a probabilidade a priori de uma sequência. Quando a evidência acústica já sustenta os fonemas e o que está em disputa é apenas sua decomposição em palavras, um acréscimo pequeno de probabilidade decide a questão. Quando a evidência acústica aponta para outra palavra, o mesmo acréscimo precisa superar a verossimilhança acústica, e em geral não supera.

Duas ressalvas. A primeira é o tamanho da amostra, já registrado em 8.3: são duas observações de segmentação e três de substituição, o que torna o padrão uma **hipótese consistente com todos os cinco enunciados**, e não uma lei estabelecida. A confirmação cabe ao corpus da subseção 5.7.6. A segunda é que a falha prevista para `marco` não ocorreu: o modelo base o transcreveu corretamente sem auxílio, o que sugere que sua classificação em criticidade alta na seção 5.3 pode estar superestimada, ao menos sob contexto sintático forte.

### 8.5 Consequências para este documento

A distinção entre segmentação e substituição, se confirmada, tem três efeitos sobre o que este glossário afirma.

O primeiro recai sobre a **escala de criticidade da seção 4**, que hoje mede apenas a consequência do erro. A verificação mostra que essa escala é insuficiente sozinha, porque não informa se o mecanismo alcança o erro em questão. `ART`, `Sé` e `via permanente` são criticidade alta e, pelos dados desta verificação, **não são tratados pela injeção no reconhecimento**. Continuam sendo verbetes legítimos — o erro é real e consequente —, mas a mitigação declarada para eles não é a lista de frases.

O segundo recai sobre a **relação entre 2.1 e 2.3**. A subseção 2.3 registra a normalização de entidades como "uso subsidiário" do glossário. A evidência não sustenta essa hierarquia: se a transcrição vai produzir `Vila permanente` de qualquer modo, o que salva a consulta é a camada de extração reconhecer que aquela cadeia deve ser reconciliada com `via permanente` — ou seja, o glossário operando como dicionário de normalização **a jusante**, e não como lista de injeção a montante. Os dois usos não são principal e acessório: são **complementares e cobrem classes de erro distintas**. A injeção cobre segmentação; a normalização precisa cobrir substituição. Esta versão registra a observação; a reescrita de 2.1 e 2.3 sob esse enquadramento fica para revisão posterior, por alterar uma tese do documento e não apenas sua redação.

O terceiro recai sobre a **avaliação do modelo customizado em 6.2**, hoje tratada como decisão de volume — o que fazer quando o glossário ultrapassar quinhentas entradas. A verificação acrescenta um segundo motivo, independente do volume: se os erros de substituição forem frequentes no uso real, o teto de entradas deixa de ser o critério relevante, porque acrescentar verbetes a uma lista que não trata essa classe de erro não melhora o resultado. O critério passaria a ser a distribuição das classes de erro no corpus, e não o tamanho do glossário.

Nenhum desses três efeitos invalida o que está escrito. Os dois primeiros ajustam o alcance atribuído ao mecanismo; o terceiro acrescenta um critério que faltava. E vale registrar o que a verificação **confirmou**: das seis falhas que este documento previu, cinco ocorreram exatamente como descritas. O diagnóstico do glossário sobre o que quebra no reconhecimento resistiu ao teste. O que o teste corrigiu foi a expectativa sobre o remédio.
