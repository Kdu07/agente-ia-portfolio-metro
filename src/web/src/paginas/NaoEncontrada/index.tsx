/**
 * Destino de qualquer rota que nao existe.
 *
 * Nao redireciona sozinha para a pagina principal: um redirecionamento
 * silencioso faz a pessoa achar que clicou errado, e esconde link
 * quebrado de quem esta desenvolvendo. A tela diz o que aconteceu e
 * oferece a saida.
 */

import { Link } from "react-router-dom";

import { EstadoVazio } from "@/componentes/ui/EstadoVazio";

export function NaoEncontrada() {
  return (
    <div className="page">
      <header className="topbar">
        <div className="assistant-title">
          <span>
            <strong>Página não encontrada</strong>
            <small>O endereço acessado não corresponde a nenhuma tela</small>
          </span>
        </div>
      </header>

      <div className="mx-auto w-[min(720px,calc(100%-48px))] py-9">
        <EstadoVazio
          titulo="Este endereço não existe"
          descricao="Verifique o endereço digitado ou volte para a página principal do agente."
          acao={
            <Link className="primary-button" to="/">
              Voltar para a página principal
            </Link>
          }
        />
      </div>
    </div>
  );
}
