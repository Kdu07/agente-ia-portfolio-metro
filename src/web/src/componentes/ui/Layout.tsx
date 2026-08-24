/**
 * Moldura do app: navegacao + area de conteudo.
 *
 * Responsivo por construcao — a navegacao vira barra inferior no mobile
 * e lateral no desktop, porque no celular o polegar alcanca a base da
 * tela e nao o topo.
 *
 * As abas restritas so aparecem para quem tem a permissao. Isso e
 * conveniencia de navegacao: quem barra e o backend (ver rotas.tsx).
 */

import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useUsuario } from "@/hooks/useUsuario";
import type { Permissao } from "@/tipos";

interface Aba {
  para: string;
  rotulo: string;
  exige?: Permissao;
}

const ABAS: Aba[] = [
  { para: "/", rotulo: "Conversa" },
  { para: "/historico", rotulo: "Historico" },
  { para: "/intencoes", rotulo: "Intencoes", exige: "ver_intencoes" },
  { para: "/rotinas", rotulo: "Rotinas", exige: "gerir_rotinas" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { usuario } = useUsuario();
  const visiveis = ABAS.filter(
    (aba) => !aba.exige || usuario?.permissoes.includes(aba.exige),
  );

  return (
    <div className="flex h-full flex-col md:flex-row">
      <nav
        aria-label="Navegacao principal"
        className="order-last flex border-t md:order-first md:w-56 md:flex-col md:border-r md:border-t-0"
      >
        {visiveis.map((aba) => (
          <NavLink key={aba.para} to={aba.para} className="flex-1 p-4 text-center md:text-left">
            {aba.rotulo}
          </NavLink>
        ))}
      </nav>
      <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
