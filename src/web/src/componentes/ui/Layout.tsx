/**
 * Moldura da aplicacao: barra lateral, navegacao e identidade da sessao.
 *
 * Renderiza `Outlet` em vez de `children` porque e rota-pai em
 * `rotas.tsx`. Isso permite que a tela de entrada exista fora da moldura.
 *
 * O item de Intencoes so aparece para quem tem `ver_intencoes`, e o de
 * Rotinas para quem tem `gerir_rotinas`. Esconder o item e conveniencia:
 * quem digitar a rota na barra de endereco chega na `RotaProtegida`, e
 * quem chamar a API direto encontra a verificacao do servidor.
 */

import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useUsuario } from "@/hooks/useUsuario";

type NomeIcone = "menu" | "chat" | "rotinas" | "historico" | "intencoes" | "plus" | "login";

function Icone({ nome }: { nome: NomeIcone }) {
  const caminhos: Record<NomeIcone, JSX.Element> = {
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    chat: <path d="M20 11.5a7.5 7.5 0 0 1-8 7.48 8.6 8.6 0 0 1-3.5-.92L4 20l1.42-4A7.5 7.5 0 1 1 20 11.5Z" />,
    rotinas: <><path d="M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" /><path d="m9 14 2 2 4-4" /></>,
    historico: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    intencoes: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    login: <><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" /></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{caminhos[nome]}</svg>;
}

export function Layout() {
  const [aberto, setAberto] = useState(false);
  const { usuario } = useUsuario();

  const fechar = () => setAberto(false);
  const podeVerIntencoes = usuario?.permissoes.includes("ver_intencoes") ?? false;
  const podeGerirRotinas = usuario?.permissoes.includes("gerir_rotinas") ?? false;

  return (
    <div className="app-shell">
      <aside className={aberto ? "sidebar sidebar--open" : "sidebar"}>
        <div className="brand-row">
          <button className="icon-button mobile-only" aria-label="Fechar menu" onClick={fechar}><Icone nome="menu" /></button>
          <img className="brand-logo" src="/logo-prata.png" alt="Prata Agent" />
        </div>

        <NavLink className="new-chat" to="/" onClick={fechar}><Icone nome="plus" /> Nova conversa</NavLink>

        <p className="nav-label">Navegação</p>
        <nav aria-label="Navegação principal" className="nav-list">
          <NavLink to="/" end onClick={fechar}><Icone nome="chat" /><span>Página principal</span></NavLink>
          <NavLink to="/historico" onClick={fechar}><Icone nome="historico" /><span>Histórico</span></NavLink>
          {podeVerIntencoes ? (
            <NavLink to="/intencoes" onClick={fechar}><Icone nome="intencoes" /><span>Intenções</span></NavLink>
          ) : null}
          {podeGerirRotinas ? (
            <NavLink to="/rotinas" onClick={fechar}><Icone nome="rotinas" /><span>Rotinas</span></NavLink>
          ) : null}
        </nav>

        <section className="history-section" aria-labelledby="historico-titulo">
          <div className="history-heading">
            <p className="nav-label" id="historico-titulo">Recentes</p>
            <NavLink className="text-button" to="/historico" onClick={fechar}>ver todas</NavLink>
          </div>
          {/* TODO (bloco de historico): substituir por GET /conversas. */}
          <NavLink to="/conversas/projeto-x" onClick={fechar}>
            <span className="history-icon">↺</span>
            <span><strong>Status do Projeto X</strong><small>Hoje</small></span>
          </NavLink>
          <NavLink to="/conversas/riscos-linha-6" onClick={fechar}>
            <span className="history-icon">↺</span>
            <span><strong>Riscos da Linha 6</strong><small>Ontem</small></span>
          </NavLink>
        </section>

        <div className="sidebar-spacer" />

        {usuario ? (
          <div className="profile-card"><span className="avatar">{usuario.nome.slice(0, 2).toUpperCase()}</span><span><strong>{usuario.nome}</strong><small>{usuario.email ?? usuario.perfil}</small></span></div>
        ) : (
          <NavLink className="microsoft-login" to="/entrar" onClick={fechar}><span className="ms-grid"><i /><i /><i /><i /></span><span><strong>Entrar com Microsoft</strong><small>Acessar com conta corporativa</small></span><Icone nome="login" /></NavLink>
        )}
      </aside>

      {aberto ? <button className="sidebar-backdrop" aria-label="Fechar menu" onClick={fechar} /> : null}

      <section className="app-content">
        <button className="floating-menu mobile-only" aria-label="Abrir menu" onClick={() => setAberto(true)}><Icone nome="menu" /></button>
        <Outlet />
      </section>
    </div>
  );
}
