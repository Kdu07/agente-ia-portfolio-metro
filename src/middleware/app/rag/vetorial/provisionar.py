"""Provisionamento e verificação do índice vetorial no Pinecone.

O adaptador de `pinecone.py` sabe conversar com um índice; ninguém sabia
**criá-lo**. Enquanto isso morar no console do provedor, reproduzir o
ambiente é seguir um passo a passo de memória, e a issue #285 pede o
contrário: configuração versionada, reproduzível em outro ambiente.

Três verbos, do mais barato ao mais caro:

- sem argumento, **verifica**: descreve o índice e não escreve nada;
- `--criar`, **idempotente**: cria só o que falta;
- `--validar`: exercita `upsert`, `buscar` e `remover_documentos` contra
  o serviço real, num namespace descartável.

**Por que `--criar` confere antes de criar.** A dimensão é fixada na
criação e não pode ser alterada depois — mudá-la exige recriar o índice
e reindexar o corpus inteiro. O engano provável não é esquecer de criar
o índice: é criá-lo com a dimensão que o console sugere. Um índice de
1536 aceita a criação sem reclamar e só falha no primeiro `upsert`, com
`ErroDimensao`, possivelmente dias depois e longe da causa. Conferir
aqui custa uma chamada e transforma isso em erro imediato e nomeado.

**Por que `--validar` passa pelo `RepositorioPinecone`.** O que precisa
de validação é o adaptador que a aplicação usa, não o provedor. Um
script que falasse com o SDK direto provaria que o Pinecone funciona —
o que ninguém duvida — e não que o nosso `filtro_de_escopo` traduz o
escopo do jeito que o índice entende. A montagem por
`de_configuracao()` é exercitada à parte, porque é ela que falha quando
a chave ou o extra `rag` faltam; as operações rodam num repositório de
namespace descartável para nunca escrever onde o trabalho vive.

O roteiro da validação afirma as duas dimensões do filtro de permissão
(invariante 2 de `base.py`) **contra o serviço**, e não contra o dublê
do teste unitário: o dublê responde o que combinamos com ele, e o que
está em dúvida aqui é justamente se o Pinecone concorda.
"""

import argparse
import asyncio
import sys
from typing import Any

from app.config import settings
from app.rag.vetorial.base import (
    DIMENSAO,
    Escopo,
    MetadadosTrecho,
    TrechoVetorizado,
    compor_id,
)
from app.rag.vetorial.pinecone import RepositorioPinecone
from app.schemas.usuario import Perfil

# Métrica do índice. Cosseno porque é o que `Acerto.score` documenta
# (0,0 a 1,0) e porque o e5 entrega vetores normalizados — com norma
# unitária, cosseno e produto interno coincidem, e cosseno é o que não
# depende disso continuar verdadeiro.
METRICA = "cosine"

# Denso: não há busca híbrida (esparso + denso) no MVP.
TIPO_VETOR = "dense"

# Única combinação oferecida pelo plano gratuito (Starter). Registrar
# aqui, e não só na documentação, é o que faz o provisionamento ser
# reproduzível sem consultar o console.
CLOUD = "aws"
REGIAO = "us-east-1"

# Namespace do `--validar`. Descartável por construção: a validação
# escreve, confere e apaga, e nunca deve tocar o namespace de trabalho.
NAMESPACE_VALIDACAO = "_validacao"

# Teto da espera até o índice ficar pronto depois da criação.
SEGUNDOS_ESPERA_PRONTO = 120

# O índice serverless é **eventualmente consistente**: o que acabou de
# ser escrito pode não aparecer na busca seguinte. Sem esta espera a
# validação falharia de forma intermitente, que é o pior tipo de teste —
# o que ensina a equipe a rodar de novo em vez de investigar.
TENTATIVAS_VISIBILIDADE = 15
INTERVALO_VISIBILIDADE = 2.0

# Documentos sintéticos da validação. Prefixados para que uma limpeza
# manual, se um dia for preciso, saiba o que é lixo de validação.
DOC_PROJETO = "_validacao-termo-abertura"
DOC_TRANSVERSAL = "_validacao-normativo"
PROJETO = "PRJ-2024-018"
OUTRO_PROJETO = "PRJ-2024-099"


class ErroProvisionamento(RuntimeError):
    """Falha de configuração ou de compatibilidade do índice."""


def _cliente() -> Any:
    """Monta o cliente do Pinecone, conferindo a configuração antes.

    Mesma disciplina de `RepositorioPinecone.de_configuracao`: as duas
    falhas prováveis — chave ausente e extra `rag` não instalado — são
    nomeadas aqui, e não numa chamada de rede sem contexto.
    """
    if not settings.pinecone_api_key:
        raise ErroProvisionamento(
            "PINECONE_API_KEY ausente. Defina-a no .env (nunca no repositório); "
            "ver o bloco do banco vetorial em .env.example"
        )
    if not settings.pinecone_index:
        raise ErroProvisionamento("PINECONE_INDEX ausente. Defina-a no .env")

    try:
        from pinecone import Pinecone
    except ModuleNotFoundError as erro:  # pragma: no cover - depende do ambiente
        raise ErroProvisionamento(
            "o SDK do Pinecone não está instalado: pip install -e '.[rag]'"
        ) from erro

    return Pinecone(api_key=settings.pinecone_api_key)


def descrever(cliente: Any) -> Any | None:
    """Descrição do índice configurado, ou `None` se ele não existir."""
    if not cliente.has_index(settings.pinecone_index):
        return None
    return cliente.describe_index(settings.pinecone_index)


def conferir_compatibilidade(descricao: Any) -> None:
    """Recusa um índice cujos parâmetros imutáveis divergem dos nossos.

    Levanta em vez de avisar: seguir adiante com um índice incompatível
    produz um `ErroDimensao` no primeiro `upsert` real, que é tarde e
    longe daqui. A mensagem diz o que fazer, porque a saída não é óbvia
    — não existe "alterar a dimensão".
    """
    divergencias = []
    if int(descricao.dimension) != DIMENSAO:
        divergencias.append(f"dimensão {descricao.dimension}, esperada {DIMENSAO}")
    if str(descricao.metric) != METRICA:
        divergencias.append(f"métrica {descricao.metric!r}, esperada {METRICA!r}")

    if divergencias:
        raise ErroProvisionamento(
            f"o índice {settings.pinecone_index!r} já existe com "
            + " e ".join(divergencias)
            + ". Dimensão e métrica são fixadas na criação e não podem ser alteradas: "
            "apague o índice e recrie, lembrando que isso obriga a reindexar o corpus inteiro."
        )


def comando_verificar() -> int:
    """Imprime os parâmetros do índice e o que há em cada namespace."""
    cliente = _cliente()
    descricao = descrever(cliente)

    if descricao is None:
        print(f"índice {settings.pinecone_index!r}: NÃO EXISTE")
        print("crie com: python -m app.rag.vetorial.provisionar --criar")
        return 1

    print(f"índice          {descricao.name}")
    print(f"dimensão        {descricao.dimension}")
    print(f"métrica         {descricao.metric}")
    print(f"host            {descricao.host}")
    print(f"pronto          {descricao.status['ready']}")

    estatisticas = cliente.Index(settings.pinecone_index).describe_index_stats()
    namespaces = estatisticas.get("namespaces") or {}
    print(f"vetores         {estatisticas.get('total_vector_count', 0)}")
    if namespaces:
        print("namespaces:")
        for nome, dados in sorted(namespaces.items()):
            print(f"  {nome or '(padrão)':<24} {dados.get('vector_count', 0)} vetores")
    else:
        print("namespaces:     nenhum (índice vazio)")

    conferir_compatibilidade(descricao)
    print("\ncompatível com app/rag/vetorial/base.py")
    return 0


def comando_criar() -> int:
    """Cria o índice se ele faltar; confere e não recria se já existir."""
    cliente = _cliente()
    descricao = descrever(cliente)

    if descricao is not None:
        conferir_compatibilidade(descricao)
        print(
            f"índice {settings.pinecone_index!r} já existe "
            f"(dimensão {descricao.dimension}, métrica {descricao.metric}) — nada a fazer"
        )
        return 0

    from pinecone import ServerlessSpec

    print(
        f"criando {settings.pinecone_index!r}: dimensão {DIMENSAO}, métrica {METRICA}, "
        f"{TIPO_VETOR}, {CLOUD}/{REGIAO}"
    )
    cliente.create_index(
        name=settings.pinecone_index,
        dimension=DIMENSAO,
        metric=METRICA,
        vector_type=TIPO_VETOR,
        spec=ServerlessSpec(cloud=CLOUD, region=REGIAO),
        timeout=SEGUNDOS_ESPERA_PRONTO,
    )
    descricao = cliente.describe_index(settings.pinecone_index)
    print(f"criado e pronto: {descricao.status['ready']} · host {descricao.host}")
    return 0


def _vetor_sintetico() -> tuple[float, ...]:
    """Vetor unitário usado pelos três trechos da validação.

    O **mesmo** vetor nos três de propósito. Com vetores idênticos os
    scores empatam em ~1,0, e então a única coisa capaz de mudar o
    conjunto devolvido é o filtro — que é exatamente o que se quer
    afirmar. Fosse cada trecho um vetor diferente, um filtro frouxo
    poderia passar despercebido atrás da ordenação.

    O score ~1,0 é, de quebra, a verificação da métrica: sob distância
    euclidiana o mesmo par de vetores devolveria ~0,0.
    """
    valores = [0.0] * DIMENSAO
    valores[0] = 1.0
    return tuple(valores)


def _trechos_de_validacao() -> list[TrechoVetorizado]:
    """Dois trechos de um projeto e um transversal, como no corpus real."""
    vetor = _vetor_sintetico()
    do_projeto = MetadadosTrecho(
        documento_id=DOC_PROJETO,
        projeto=PROJETO,
        perfis=frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO}),
    )
    transversal = MetadadosTrecho(
        documento_id=DOC_TRANSVERSAL,
        projeto=None,
        perfis=frozenset({Perfil.DIRETORIA, Perfil.LIDER_PROJETO, Perfil.MEMBRO_EQUIPE}),
    )
    return [
        TrechoVetorizado(compor_id(DOC_PROJETO, 1), vetor, do_projeto),
        TrechoVetorizado(compor_id(DOC_PROJETO, 2), vetor, do_projeto),
        TrechoVetorizado(compor_id(DOC_TRANSVERSAL, 1), vetor, transversal),
    ]


async def _esperar(
    repositorio: RepositorioPinecone,
    escopo: Escopo,
    quantidade: int,
) -> tuple[Any, ...]:
    """Repete a busca até o índice convergir para a quantidade esperada.

    Não é gentileza com um serviço lento: o índice serverless é
    eventualmente consistente, e sem a espera a validação falharia de
    forma intermitente — o tipo de teste que ensina a rodar de novo em
    vez de investigar.
    """
    vetor = _vetor_sintetico()
    for tentativa in range(TENTATIVAS_VISIBILIDADE):
        acertos = await repositorio.buscar(vetor, escopo=escopo, k=10)
        if len(acertos) == quantidade:
            return acertos
        # `asyncio.sleep`, não `time.sleep`: numa função assíncrona a
        # segunda congela o laço de eventos inteiro pelo intervalo, que
        # é a mesma falha que `pinecone.py` evita mandando o SDK
        # síncrono para uma thread.
        await asyncio.sleep(INTERVALO_VISIBILIDADE)
    raise ErroProvisionamento(
        f"o índice não convergiu para {quantidade} resultado(s) em "
        f"{TENTATIVAS_VISIBILIDADE * INTERVALO_VISIBILIDADE:.0f}s; "
        f"última busca devolveu {len(acertos)}"
    )


async def _validar() -> int:
    """Roteiro completo de escrita, filtro e limpeza contra o serviço."""
    # A montagem por configuração é exercitada aqui porque é ela que
    # falha quando a chave ou o extra faltam. As operações, logo abaixo,
    # rodam num namespace descartável.
    RepositorioPinecone.de_configuracao()
    print(f"montagem por de_configuracao(): ok (namespace de trabalho {settings.pinecone_namespace!r})")

    cliente = _cliente()
    repositorio = RepositorioPinecone(
        cliente.Index(settings.pinecone_index), NAMESPACE_VALIDACAO
    )
    trechos = _trechos_de_validacao()

    gravados = await repositorio.upsert(trechos)
    print(f"1. upsert de {gravados} trechos no namespace {NAMESPACE_VALIDACAO!r}")
    if gravados != len(trechos):
        raise ErroProvisionamento(f"upsert devolveu {gravados}, esperado {len(trechos)}")

    lider = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({PROJETO}))
    acertos = await _esperar(repositorio, lider, 3)
    print(f"2. líder de {PROJETO}: {len(acertos)} acertos, score máximo {acertos[0].score:.4f}")
    if acertos[0].score < 0.99:
        raise ErroProvisionamento(
            f"score {acertos[0].score:.4f} para vetores idênticos; "
            f"o índice não parece usar a métrica {METRICA!r}"
        )

    outro = Escopo(perfil=Perfil.LIDER_PROJETO, projetos=frozenset({OUTRO_PROJETO}))
    acertos = await _esperar(repositorio, outro, 1)
    recuperados = {acerto.trecho_id for acerto in acertos}
    print(f"3. líder de {OUTRO_PROJETO}: {len(acertos)} acerto — {sorted(recuperados)}")
    if any(id_.startswith(DOC_PROJETO) for id_ in recuperados):
        raise ErroProvisionamento(
            "o filtro de projeto NÃO barrou: trecho de outro projeto foi recuperado"
        )

    membro = Escopo(perfil=Perfil.MEMBRO_EQUIPE, projetos=frozenset({PROJETO}))
    acertos = await _esperar(repositorio, membro, 1)
    print(f"4. membro de equipe em {PROJETO}: {len(acertos)} acerto (só o transversal)")

    removidos = await repositorio.remover_documentos([DOC_PROJETO, DOC_TRANSVERSAL])
    print(f"5. remover_documentos: {removidos} trechos apagados")
    await _esperar(repositorio, lider, 0)
    print("6. namespace de validação vazio")

    print("\nupsert, busca com filtro e remoção validados contra o serviço.")
    return 0


def comando_validar() -> int:
    return asyncio.run(_validar())


def main(argv: list[str] | None = None) -> int:
    # O console do Windows abre em cp1252 e não codifica os acentos das
    # mensagens. Mesmo tratamento de `pipeline/intencao/avaliacao.py`:
    # sem ele o relatório sai ilegível ou morre no meio.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(
        prog="python -m app.rag.vetorial.provisionar",
        description="Provisiona e valida o índice vetorial do executor próprio.",
    )
    grupo = analisador.add_mutually_exclusive_group()
    grupo.add_argument("--criar", action="store_true", help="cria o índice se faltar (idempotente)")
    grupo.add_argument(
        "--validar",
        action="store_true",
        help="exercita upsert, busca e remoção num namespace descartável",
    )
    argumentos = analisador.parse_args(argv)

    try:
        if argumentos.criar:
            return comando_criar()
        if argumentos.validar:
            return comando_validar()
        return comando_verificar()
    except ErroProvisionamento as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
