import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useUsuario } from "@/hooks/useUsuario";

function Icone({ nome }: { nome: "menu" | "chat" | "rotinas" | "plus" | "login" }) {
  const caminhos = {
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    chat: <path d="M20 11.5a7.5 7.5 0 0 1-8 7.48 8.6 8.6 0 0 1-3.5-.92L4 20l1.42-4A7.5 7.5 0 1 1 20 11.5Z" />,
    rotinas: <><path d="M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" /><path d="m9 14 2 2 4-4" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    login: <><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" /></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{caminhos[nome]}</svg>;
}

export function Layout({ children }: { children: ReactNode }) {
  const [aberto, setAberto] = useState(false);
  const { usuario } = useUsuario();

  function entrar() { window.location.assign("/api/auth/login"); }

  return (
    <div className="app-shell">
      <aside className={aberto ? "sidebar sidebar--open" : "sidebar"}>
        <div className="brand-row">
          <button className="icon-button mobile-only" aria-label="Fechar menu" onClick={() => setAberto(false)}><Icone nome="menu" /></button>
          <span className="brand-mark">✦</span><strong>Prata Agent</strong>
        </div>
        <NavLink className="new-chat" to="/" onClick={() => setAberto(false)}><Icone nome="plus" /> Nova conversa</NavLink>
        <p className="nav-label">Navegação</p>
        <nav aria-label="Navegação principal" className="nav-list">
          <NavLink to="/" end onClick={() => setAberto(false)}><Icone nome="chat" /><span>Página principal</span></NavLink>
          <NavLink to="/rotinas" onClick={() => setAberto(false)}><Icone nome="rotinas" /><span>Rotinas</span></NavLink>
        </nav>
        <div className="sidebar-spacer" />
        {usuario ? (
          <div className="profile-card"><span className="avatar">{usuario.nome.slice(0, 2).toUpperCase()}</span><span><strong>{usuario.nome}</strong><small>{usuario.email ?? usuario.perfil}</small></span></div>
        ) : (
          <button className="microsoft-login" type="button" onClick={entrar}><span className="ms-grid"><i /><i /><i /><i /></span><span><strong>Entrar com Microsoft</strong><small>Acessar com conta corporativa</small></span><Icone nome="login" /></button>
        )}
      </aside>
      {aberto ? <button className="sidebar-backdrop" aria-label="Fechar menu" onClick={() => setAberto(false)} /> : null}
      <section className="app-content"><button className="floating-menu mobile-only" aria-label="Abrir menu" onClick={() => setAberto(true)}><Icone nome="menu" /></button>{children}</section>
    </div>
  );
}
