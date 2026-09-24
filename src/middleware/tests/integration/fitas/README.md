# Fitas VHS

Uma fita é a resposta real de um serviço externo, gravada uma vez e
reproduzida em toda execução seguinte. É o que permite testar as
integrações do middleware sem alcançar nenhum serviço Microsoft e sem
repetir a mesma requisição a cada rodada da suíte.

O mecanismo está em [`../vhs.py`](../vhs.py), a fiação no pytest em
[`../conftest.py`](../conftest.py), e o plano completo na seção **10.5.4
de [Projeto.md](../../../../docs/Projeto.md)**.

## Organização

Uma pasta por serviço, uma fita por **cenário** — não por teste:

```text
fitas/
├── entra/              # troca de código, configuração OIDC
├── content_safety/     # Prompt Shields e categorias de conteúdo
├── directline/         # iniciar conversa, postar activity
├── speech/             # emissão de token
└── vhs/                # fita do autoteste do próprio módulo
```

Nome no formato `<operacao>_<cenario>.yaml`, em minúsculas, sem acento e
com `_` entre palavras. Fita nomeada pelo cenário sobrevive à renomeação
de testes e deixa visível o que ainda falta gravar.

Vários testes apontam para a mesma fita pelo marcador do
`pytest-recording`:

```python
@pytest.mark.vcr
@pytest.mark.default_cassette("content_safety/prompt_shield_limpo")
def test_mensagem_legitima_atravessa_a_guarda(): ...
```

Sem o marcador, a fita recebe o nome do teste.

## Segredo nenhum entra aqui

A sanitização é configurada uma vez em `vhs.py` e cobre cabeçalho de
requisição e de resposta, corpo `form-urlencoded`, corpo JSON e o id de
conversa do Direct Line que aparece na URL. Tudo o que é redigido vira a
marca `REDIGIDO-PELO-VHS`, que se acha com um `grep`.

Isso **não** dispensa a leitura do diff. Toda merge request que
adiciona ou altera fita tem o item próprio no checklist de
[GestaoConfiguracao.md](../../../../docs/GestaoConfiguracao.md) §4.1:
*"li o `git diff` da fita linha a linha"*. Fita é código.

## Fita provisória

Enquanto o tenant do parceiro não estiver disponível (risco R02), alguns
cenários são gravados contra dublê em vez do serviço real. Essas fitas
declaram procedência no topo do arquivo, e é isso que o caso IT-CTR-05
verifica:

```yaml
# origem: servidor local do proprio teste do modulo de VHS
# issue: #255
# Fita provisoria: substituir por gravacao contra o servico real
# quando a integracao correspondente existir.
```

Use `vhs.registrar_cabecalho_de_fita` ao fim da gravação — o VCR.py
reescreve o arquivo inteiro e apagaria um cabeçalho posto à mão.

## Gravar e regravar

```powershell
$env:VHS_GRAVANDO = "1"
python -m pytest -m externo --record-mode=all
Remove-Item Env:\VHS_GRAVANDO
```

Fora dessa sessão deliberada o modo é sempre `none`: toca a fita e falha
se faltar interação. É o que garante que nenhuma requisição escape por
engano de configuração.

Gravação e `--block-network` são modos opostos e não se combinam: o teste
que grava se pula sozinho quando a rede está bloqueada.

> **`--block-network` no Windows.** O laço de eventos do asyncio abre um
> socket local para o próprio *self-pipe*, e o bloqueador o interpreta
> como acesso à rede — o que derruba todo teste `async` no ambiente de
> desenvolvimento. Rode `--block-network --allowed-hosts=127.0.0.1`
> localmente. No CI, que é Linux, o `--block-network` sozinho basta.

**`--record-mode=all` acrescenta à fita existente.** Apague o arquivo
antes de regravar, ou a fita acumula interações duplicadas e deixa de
representar o cenário que diz representar.

Gatilhos de regravação, de §10.5.4.4: fechamento de sprint, antes de uma
`release/`, aviso de mudança do fornecedor, e falha em produção que a
suíte não reproduziu. **O diff da fita é o alerta** — quando ele muda, a
notícia é sobre o fornecedor, e vale mais que o teste ter passado.

## Regravação por serviço

### Content Safety

Fitas em `content_safety/` cobrem as operações de análise de categorias de conteúdo.
Para regravar:

```powershell
cd src\middleware
$env:VHS_GRAVANDO = "1"
python -m pytest tests/integration/externos/test_content_safety_real.py --record-mode=all
Remove-Item Env:\VHS_GRAVANDO
```

**Nota:** Prompt Shields (injeção direta e indireta) requerem configuração adicional
e ainda não foram gravados. As fitas atuais cobrem apenas a análise de categorias.

## Onde a fita não serve

Áudio do Speech (WebSocket), timeout, 429/503 e expiração de token não
têm resposta a gravar. Esses cenários são de `respx` e `time-machine`,
conforme §10.5.4.5 — o VHS responde *o que o serviço devolve*, não *o que
fazemos quando ele não devolve*.
