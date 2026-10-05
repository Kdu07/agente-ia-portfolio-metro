# Guia de padrões de desenvolvimento

Este guia registra os padrões praticados no middleware e na interface do
Agente de Portfólio do Metrô SP (grupo g02). O objetivo é manter o código
legível em português, verificável por ferramentas automatizadas e sujeito a
revisão antes da integração. As convenções de nomenclatura da interface
complementam a seção 9.2.4 do [Projeto](Projeto.md); o fluxo de revisão segue a
[Gestão de Configuração](GestaoConfiguracao.md).

## 1. Estrutura do código

O repositório separa a interface (`src/web`) do middleware (`src/middleware`).
Cada parte mantém seu código de produção e seus testes próximos, organizados
por responsabilidade:

| Área | Organização | Exemplo |
| --- | --- | --- |
| Middleware | `app/` é dividido por domínio e camada: `api/routes/`, `auth/`, `persistence/`, `pipeline/`, `schemas/` e outros módulos especializados. | `app/api/routes/rotinas.py` concentra endpoints de rotinas; `app/persistence/repository.py` trata persistência. |
| Testes do middleware | `tests/` separa `unit/`, `integration/`, `funcionais/`, `rnf/`, `desempenho/` e `perimetro/`. | `tests/unit/test_validacao_rotina.py` e `tests/integration/test_api_rotinas.py`. |
| Interface | `src/` separa `componentes/`, `paginas/`, `hooks/`, `servicos/`, `tipos/`, `utilitarios/` e `tema/`. | `src/componentes/chat/Composer.tsx` e `src/servicos/api.ts`. |
| Testes da interface | `src/testes/` reúne testes Vitest, Testing Library e MSW. | `src/testes/componentes-chat.test.tsx` e `src/testes/middleware.test.tsx`. |

Novas funcionalidades devem ficar no módulo que corresponde à sua
responsabilidade, reutilizando os serviços, tipos e componentes existentes em
vez de duplicar lógica em páginas ou rotas. Os contratos públicos da interface
devem acompanhar os schemas do middleware na mesma mudança; por exemplo, ao
alterar um schema em `app/schemas/`, atualizar o tipo correspondente em
`src/tipos/`.

## 2. Nomenclatura e estilo

### 2.1 Convenções compartilhadas

- Usar português nos nomes de arquivos, funções, variáveis e tipos de domínio,
  seguindo o glossário do projeto. Termos técnicos consagrados, como `hook`,
  `build` e `token`, permanecem em inglês quando a tradução reduzir a clareza.
- Preferir nomes que expressem o domínio e a responsabilidade, como
  `validar_agenda`, `RotinaRequest` e `ConversaVazia`.
- Manter comentários para explicar decisões e suas consequências, não para
  repetir literalmente o que o código já faz.

### 2.2 Middleware (Python)

- Módulos, funções e variáveis usam `snake_case`; classes e tipos usam
  `PascalCase`. Exemplos: `app/api/routes/rotinas.py`, `_validar_pedido`,
  `RotinaRepository` e `RotinaResposta`.
- Usar anotações de tipo nas interfaces das funções. Preferir as dependências
  tipadas do FastAPI já usadas pelo projeto, como `Annotated` e `Depends`.
- Agrupar imports no início do módulo e separar biblioteca padrão,
  dependências externas e módulos da aplicação, conforme os arquivos
  existentes.
- Manter linhas com até 100 caracteres, conforme `tool.ruff.line-length` em
  `src/middleware/pyproject.toml`.

Exemplo em `src/middleware/app/api/routes/rotinas.py`:

```python
async def listar(
    usuario: UsuarioAtual,
    rotinas: Annotated[RotinaRepository, Depends(obter_rotinas)],
) -> list[RotinaResposta]:
    """Rotinas do usuário, com o próximo disparo calculado."""
    return [_resposta_rotina(rotina) for rotina in await rotinas.listar_por_dono(usuario.id)]
```

### 2.3 Interface (TypeScript e React)

- Usar nomes de domínio em português. Componentes React e tipos usam
  `PascalCase`, como `ConversaVazia` e `ChatRequest`; funções e variáveis usam
  `camelCase`, como `detalheLegivel` e `tempoLimiteMs`.
- Nomear os arquivos de componentes pelo componente (`Composer.tsx`) e os
  módulos auxiliares conforme seu papel (`api.ts`, `formato.ts`).
- Usar o alias `@/` para imports de `src/`. Sua resolução deve continuar
  configurada tanto em `tsconfig.json` quanto em `vite.config.ts`.
- Declarar tipos explícitos nos contratos e manter os tipos em
  `src/tipos/` alinhados aos schemas do middleware.
- Escrever por extenso as classes Tailwind que precisam ser detectadas na
  compilação. Para classes dinâmicas de desfecho, centralizá-las em
  `src/componentes/chat/desfechos.ts`, não montar nomes como
  `text-desfecho-${cor}`.
- Restringir imports de ícones ao módulo
  `@/componentes/ui/icones`, conforme a regra ESLint existente.

Exemplo em `src/servicos/api.ts`:

```typescript
export type TipoFalha = "rede" | "tempo" | "servidor" | "pedido";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly detalhe: string,
    readonly tipo: TipoFalha = status >= 500 ? "servidor" : "pedido",
  ) {
    super(detalhe);
    this.name = "ErroApi";
  }
}
```

## 3. Análise estática e verificações

Executar as verificações da área alterada antes de solicitar revisão:

| Área | Verificações |
| --- | --- |
| Middleware | `python -m ruff check app tests` e `python -m pytest -q`, a partir de `src/middleware`. |
| Interface | `npm run lint`, `npm run typecheck` e `npm test`, a partir de `src/web`. |
| Build da interface | `npm run build`, que verifica os tipos e gera o build de produção. |

O Ruff está configurado em `src/middleware/pyproject.toml`, com limite de linha
de 100 caracteres e versão restrita ao intervalo `>=0.16,<0.17` no extra de
desenvolvimento. O ESLint está configurado em `src/web/.eslintrc.cjs` e cobre
regras recomendadas, TypeScript, hooks do React, variáveis não utilizadas e
imports de ícones fora do módulo central. A configuração inclui exceções
específicas para os componentes gerados de `src/componentes/ui/`.

O TypeScript é verificado para a aplicação e para a configuração Node do Vite.
Os dois `tsconfig` fazem parte das verificações de tipo e do build.

## 4. Testes

Os testes devem validar comportamento observável e regressões da mudança,
organizados de acordo com a camada:

- **Middleware:** pytest. Testes unitários ficam em `tests/unit/`; testes de
  integração, em `tests/integration/`; testes funcionais e de requisitos não
  funcionais ficam em seus diretórios correspondentes. Por exemplo,
  `tests/unit/test_validacao_rotina.py` testa validação isolada, enquanto
  `tests/integration/test_api_rotinas.py` exercita endpoints.
- **Interface:** Vitest com Testing Library para comportamento de componentes
  e páginas, e MSW para simular respostas HTTP. Os arquivos de teste seguem o
  padrão `*.test.ts` ou `*.test.tsx` dentro de `src/testes/`. Exemplos:
  `componentes-chat.test.tsx` e `middleware.test.tsx`.
- **Integrações externas:** os testes devem usar as fitas VHS existentes
  quando aplicável, para reproduzir respostas gravadas e manter a execução
  previsível e offline.
- **Cobertura:** no middleware, `python -m pytest --cov=app
  --cov-report=term-missing` mostra as linhas não exercitadas e mede cobertura
  de ramos. Cobertura é uma ferramenta complementar; os casos devem verificar
  os comportamentos e limites relevantes da mudança.

Uma alteração de contrato entre interface e middleware deve incluir testes nos
dois lados, quando aplicável. Os testes da interface devem cobrir também
estados de erro e carregamento, além do caminho de sucesso, como ocorre nos
testes de `src/testes/middleware.test.tsx`.

## 5. Revisão e integração

Toda contribuição segue a política de [integração e revisão da Gestão de
Configuração](GestaoConfiguracao.md#integração-e-revisão):

1. Não fazer commits diretamente em `main` ou `develop`; submeter a mudança por
   merge request no GitLab.
2. Solicitar revisão de pelo menos uma pessoa diferente da autora.
3. Na revisão, conferir atendimento ao card, escopo, preservação da
   documentação e do comportamento existente, além da execução das verificações
   automatizadas disponíveis.
4. Após aprovação, integrar branches de trabalho à `develop` conforme o fluxo
   documentado e remover branches já integradas do remoto.

O merge request deve facilitar a revisão: descrever o objetivo e as mudanças,
relacioná-las ao card e informar verificações executadas. Mudanças em
comportamento, contratos ou decisões técnicas devem atualizar a documentação
diretamente relacionada.
