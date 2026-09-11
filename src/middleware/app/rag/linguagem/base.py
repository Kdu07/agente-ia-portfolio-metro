"""Porta do modelo de linguagem.

Decisão D3 do plano do executor próprio: o Gemini gera a resposta, mas
fica atrás desta interface, pela mesma razão que o banco vetorial fica
atrás de `vetorial/base.py`. A alternativa descartada na decisão — Azure
OpenAI no tenant da equipe — continua possível, e se o acesso chegar a
troca tem de ser um adaptador novo e uma linha no `.env`, não uma
reescrita da geração.

**O que a porta recebe é o que separa instrução de dado.** São dois
argumentos, e não um prompt montado: `instrucoes` são as regras do
sistema, escritas pela equipe; `conteudo` é a pergunta do usuário e os
trechos recuperados, que são dado não confiável (seção 4.4 do plano).
Cada adaptador é obrigado a entregar os dois ao provedor pelos canais
distintos que ele oferece — instrução de sistema de um lado, mensagem
do usuário do outro —, e nunca concatená-los. Uma porta que aceitasse
uma string só deixaria essa fronteira a cargo de quem chama, e ela
deixaria de ser verificável por teste.

Nada aqui conhece recuperação, Pinecone ou PostgreSQL: trocar o modelo
não toca a camada vetorial, e vice-versa.
"""

from typing import Protocol, runtime_checkable


class ErroGeracao(RuntimeError):
    """O provedor não produziu resposta utilizável.

    Cobre indisponibilidade, cota esgotada depois das novas tentativas,
    tempo esgotado e resposta vazia (bloqueio de segurança do provedor).
    Quem chama trata como falha do executor, e não como abstenção: "o
    modelo não respondeu" e "os documentos não sustentam uma resposta"
    são desfechos diferentes, e confundi-los esconderia uma indisponibi-
    lidade atrás de uma recusa que parece legítima.

    A mensagem nunca carrega o conteúdo enviado — só o tipo e o código
    do erro —, pela mesma razão do log do orquestrador: o traço do
    provedor pode trazer o payload.
    """


@runtime_checkable
class ModeloLinguagem(Protocol):
    """Contrato dos adaptadores de modelo de geração."""

    @property
    def nome(self) -> str:
        """Provedor e modelo, como `gemini/gemini-3.5-flash`.

        Vai para o log de cada consulta: saber qual modelo produziu uma
        resposta é parte da rastreabilidade quando o modelo é trocado
        por configuração.
        """
        ...

    async def gerar(self, *, instrucoes: str, conteudo: str) -> str:
        """Devolve o texto gerado para o conteúdo, sob as instruções dadas.

        Levanta `ErroGeracao` quando não há texto a devolver. Nunca
        devolve string vazia: a ausência de resposta é erro, não dado.
        """
        ...
