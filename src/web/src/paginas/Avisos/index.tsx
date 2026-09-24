/**
 * Avisos do portfolio: o que o usuario escolheu acompanhar.
 *
 * Os avisos sao privados e so aparecem dentro da aplicacao; nao ha envio
 * por Teams ou e-mail (F57 fica fora do escopo). Tudo comeca desativado,
 * e ativar um tipo nao gera aviso retroativo (Projeto.md 9.1.2.7.2).
 */

import { ListaAvisos } from "@/componentes/avisos/ListaAvisos";
import { PreferenciasAviso } from "@/componentes/avisos/PreferenciasAviso";

export function Avisos() {
  return (
    <div className="page">
      <header className="topbar">
        <div className="assistant-title">
          <span>
            <strong>Avisos do portfólio</strong>
            <small>Acompanhe as alterações que escolheu nos seus projetos</small>
          </span>
        </div>
      </header>

      <div className="mx-auto grid w-[min(1180px,calc(100%-48px))] gap-10 py-9">
        <section aria-labelledby="avisos-titulo" className="grid gap-3">
          <div>
            <h2 id="avisos-titulo" className="text-lg font-semibold text-slate-900">
              Avisos recebidos
            </h2>
            <p className="text-sm text-slate-600">
              Só aparecem avisos dos projetos a que você tem acesso agora, retidos por 30 dias.
            </p>
          </div>
          <ListaAvisos />
        </section>

        <section aria-labelledby="preferencias-titulo" className="grid gap-3">
          <div>
            <h2 id="preferencias-titulo" className="text-lg font-semibold text-slate-900">
              Preferências
            </h2>
            <p className="text-sm text-slate-600">
              Tudo começa desativado. Ativar um tipo não gera avisos de alterações anteriores. Para
              riscos, a severidade é probabilidade × impacto; com um mínimo, o aviso chega quando o
              estado anterior ou o novo alcança esse valor.
            </p>
          </div>
          <PreferenciasAviso />
        </section>
      </div>
    </div>
  );
}
