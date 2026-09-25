/**
 * Destino de qualquer rota que nao existe.
 *
 * Nao redireciona sozinha para a pagina principal: um redirecionamento
 * silencioso faz a pessoa achar que clicou errado, e esconde link
 * quebrado de quem esta desenvolvendo. A tela diz o que aconteceu e
 * oferece a saida.
 */

import { Link } from "react-router-dom";

import { Button } from "@/componentes/ui/button";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { IconeCaminho } from "@/componentes/ui/icones";

export function NaoEncontrada() {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <CabecalhoPagina titulo="Página não encontrada" subtitulo="O endereço acessado não corresponde a nenhuma tela" />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-245 px-3.5 pt-8 pb-10 md:px-6">
          <EstadoVazio
            icone={IconeCaminho}
            titulo="Este endereço não existe"
            descricao="Verifique o endereço digitado ou volte para a página principal do agente."
            acao={
              <Button asChild>
                <Link to="/">Voltar para a página principal</Link>
              </Button>
            }
          />
        </div>
      </div>
    </div>
  );
}
