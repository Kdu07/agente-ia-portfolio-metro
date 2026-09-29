/**
 * Tela de entrada.
 *
 * Renderiza FORA do Layout: quem ainda nao tem sessao nao deve ver a
 * navegacao de uma aplicacao a que nao tem acesso.
 *
 * O botao aponta para `/api/auth/login`, que inicia o fluxo Authorization
 * Code com PKCE no proprio FastAPI. A troca do codigo pelo token acontece
 * no servidor e a sessao volta em cookie httpOnly: o React nunca ve um
 * `access_token`. Se algum dia esta tela passar a receber ou guardar um
 * token, a decisao de arquitetura do BFF foi desfeita.
 *
 * `?erro=login` e o retorno do callback quando o Entra recusou o acesso
 * ou o token nao conferiu. A mensagem nao diz qual dos dois: o detalhe
 * fica no log do servidor, e a acao do usuario e a mesma nos dois casos.
 *
 * Duas colunas no desktop: o painel de marca, em marinho com o tracado das
 * linhas, diz que e um produto do Metro; o cartao de acesso fica ao lado.
 * No celular o painel vira uma faixa no topo.
 */

import { useSearchParams } from "react-router-dom";

import { BotaoMicrosoft } from "@/componentes/marca/BotaoMicrosoft";
import { LinhasMetro } from "@/componentes/marca/LinhasMetro";
import { LogoPrata } from "@/componentes/marca/LogoPrata";
import { SimboloPrata } from "@/componentes/marca/SimboloPrata";
import { IconeAviso, IconeCadeado } from "@/componentes/ui/icones";

export function Login() {
  const [parametros] = useSearchParams();
  const falhou = parametros.get("erro") === "login";

  function entrar() {
    window.location.assign("/api/auth/login");
  }

  return (
    <main className="grid min-h-dvh grid-rows-[auto_1fr] bg-background lg:grid-cols-[1.1fr_1fr] lg:grid-rows-1">
      <section aria-label="Marca do Metrô" className="marca-prata fundo-marca relative flex min-h-50 flex-col justify-between gap-6 overflow-hidden p-5.5 lg:p-8.5">
        {/* Na faixa estreita do celular o traçado passa atrás da frase: mais apagado ali. */}
        <LinhasMetro className="absolute inset-0 size-full opacity-55 lg:opacity-100" />
        <LogoPrata className="relative h-11 w-42.5 lg:h-13.5 lg:w-52.5" />
        <p className="font-display relative max-w-[26ch] text-lg leading-tight text-sidebar-accent-foreground lg:text-[23px]">
          O portfólio de projetos do Metrô, em conversa.
          <span className="mt-2.5 hidden max-w-[40ch] font-sans text-[13.5px] leading-normal font-normal tracking-normal text-sidebar-suave font-stretch-100% lg:block">
            Status, marcos, riscos e pendências de cada projeto, respondidos a partir dos documentos
            oficiais.
          </span>
        </p>
      </section>

      <div className="fundo-conversa grid place-items-center px-6 py-10 lg:p-8">
        <div className="grid w-full max-w-90 gap-3.5">
          <SimboloPrata decorativa className="h-9 w-10" />
          <h1 className="font-display text-[26px]">Entrar no Prata</h1>
          <p className="text-sm text-muted-foreground">
            Use a sua conta corporativa da Microsoft. O seu perfil define o que o agente pode mostrar.
          </p>

          {falhou ? (
            <p
              role="alert"
              className="flex gap-2.5 rounded-lg border border-destructive/40 bg-card px-4 py-3 text-sm text-foreground"
            >
              <IconeAviso aria-hidden="true" className="mt-px shrink-0 text-destructive" />
              <span>
                Não foi possível concluir o login. Tente de novo; se o problema continuar, peça ao
                administrador para confirmar o seu acesso ao aplicativo.
              </span>
            </p>
          ) : null}

          <BotaoMicrosoft onEntrar={entrar} />

          <p className="flex gap-2 text-[12.5px] text-muted-foreground">
            <IconeCadeado aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            O acesso é controlado pelo diretório corporativo. O seu perfil define quais informações do
            portfólio o agente pode apresentar.
          </p>
        </div>
      </div>
    </main>
  );
}
