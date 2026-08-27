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