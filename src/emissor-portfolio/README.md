# Emissor do portfólio (WH-02)

Script Google Apps Script que observa uma planilha nativa do Google Sheets e
envia ao middleware, assinados com HMAC-SHA256, os eventos de alteração de
status de projeto, de marcos e de riscos. O contrato está na seção 9.1.2.7.2
do [Projeto.md](../../docs/Projeto.md); o receptor é
`POST /webhooks/portfolio`, em [src/middleware](../middleware/README.md).

| Arquivo | Para quê |
|---|---|
| `Codigo.gs` | Captura, diário de eventos, entrega com novas tentativas e assinatura |
| `appsscript.json` | Manifesto: fuso, runtime V8 e as três permissões necessárias |

O script é **independente** (não fica dentro da planilha): quem edita a
planilha de negócio não edita o script nem o diário de eventos, que vive nas
propriedades do script. O segredo HMAC também fica ali, nunca numa célula.

## Planilha

Três abas, com os nomes das colunas na primeira linha (a ordem é livre). Os
identificadores são os mesmos do banco do middleware.

| Aba | Colunas | Valores de `status` |
|---|---|---|
| `Projetos` | `codigo`, `status` | `planejado`, `em_andamento`, `suspenso`, `concluido`, `cancelado` |
| `Marcos` | `id`, `projeto_codigo`, `status`, `data_prevista`, `data_real` | `nao_iniciado`, `em_andamento`, `concluido`, `atrasado`, `cancelado` |
| `Riscos` | `id`, `projeto_codigo`, `status`, `probabilidade`, `impacto` | `identificado`, `monitorado`, `mitigado`, `materializado` |

Datas podem ser células de data ou texto `AAAA-MM-DD`; `data_real` vazia vira
`null`. `probabilidade` e `impacto` são inteiros de 1 a 5. Linha inválida não
gera evento: fica registrada em `erros` para revisão (ver `statusFila`).

## Instalação

1. **Chave.** Gere 32 bytes aleatórios em Base64, num terminal seguro:

   ```bash
   python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
   ```

2. **Middleware.** Coloque a chave no cadastro apontado por
   `WEBHOOK_PORTFOLIO_CHAVES_ARQUIVO` (formato no `.env.example`) e cadastre a
   fonte com os projetos e tipos que ela pode alterar:

   ```bash
   python -m app.webhooks.portfolio cadastrar portfolio_sintetico \
       --planilha <ID da planilha> --projetos demo-PRJ-2024-001 --tipos todos
   ```

3. **Script.** Em [script.google.com](https://script.google.com), crie um
   projeto novo (independente). Em *Configurações do projeto*, marque
   *Mostrar o arquivo de manifesto "appsscript.json"*. Cole o conteúdo de
   `appsscript.json` e de `Codigo.gs`.

4. **Propriedades do script** (*Configurações do projeto → Propriedades do
   script*):

   | Propriedade | Valor |
   |---|---|
   | `PLANILHA_ID` | ID da planilha, o trecho entre `/d/` e `/edit` da URL |
   | `URL_WEBHOOK` | `https://<host>/api/webhooks/portfolio` no Azure; num túnel direto para o middleware, `https://<túnel>/webhooks/portfolio` |
   | `SOURCE_ID` | O mesmo `source_id` cadastrado no passo 2 |
   | `KEY_ID` | O mesmo `key_id` do cadastro de chaves |
   | `SEGREDO_BASE64` | A chave do passo 1 |

5. **Execute, nesta ordem**, pelo editor do Apps Script (autorize as
   permissões na primeira execução):
   1. `testarAssinatura` — confere a assinatura contra o vetor compartilhado
      com o middleware; se falhar, não siga;
   2. `registrarLinhaDeBase` — grava o estado atual como versão 0, sem enviar
      nada. Rode só depois de conferir que a planilha bate com o banco;
   3. `instalar` — cria o gatilho de edição, a reconciliação a cada 15 minutos
      e a entrega de pendentes a cada 5 minutos.

Se `instalar` recusar o gatilho de edição por permissão, troque no manifesto
`spreadsheets.readonly` por `spreadsheets` e autorize de novo.

## Operação

- `statusFila` — quantos eventos estão pendentes, em `intervencao` ou em
  `erro`, e as linhas recusadas na captura.
- `reenfileirarParados` — depois de corrigir a causa (URL, chave, cadastro da
  fonte), devolve à fila os eventos parados, com o mesmo UUID e o mesmo corpo.
  Um evento parado segura os posteriores da mesma entidade, para que a versão
  3 nunca chegue antes da 2.

Novas tentativas: após timeout, `429` ou `5xx`, em 1, 5, 15 e 60 minutos (ou
o `Retry-After`, se maior); na quinta falha o evento fica em `intervencao`.
Outro `4xx` fica em `erro`. Os gatilhos rodam com a conta de quem os instalou,
e alterações feitas por API ou outro script só são vistas pela reconciliação.

## Teste local

Com o middleware em `http://127.0.0.1:8000`, abra um túnel e use a URL dele em
`URL_WEBHOOK`, seguida de `/webhooks/portfolio`:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Edite uma célula de status: o middleware responde `202` e o evento
`webhook.received` aparece na fila `prata.webhooks.incoming`.
