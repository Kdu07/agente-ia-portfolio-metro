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
 */

export function Login() {
  function entrar() {
    window.location.assign("/api/auth/login");
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-white px-6 py-12">
      <div className="w-full max-w-sm text-center">
        <img className="mx-auto h-16 w-auto" src="/logo-prata.png" alt="Prata Agent" />

        <h1 className="mt-8 text-xl font-semibold text-slate-900">
          Agente de Portfólio
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Acesse com a sua conta corporativa para consultar o portfólio,
          acompanhar marcos e registrar atualizações.
        </p>

        <button
          type="button"
          onClick={entrar}
          className="mt-8 flex w-full items-center justify-center gap-3 rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-900 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-700"
        >
          <span className="ms-grid" aria-hidden="true"><i /><i /><i /><i /></span>
          Entrar com Microsoft
        </button>

        <p className="mt-6 text-xs leading-relaxed text-slate-600">
          O acesso é controlado pelo diretório corporativo. O seu perfil define
          quais informações do portfólio o agente pode apresentar.
        </p>
      </div>
    </main>
  );
}
