/**
 * Campo de envio da mensagem.
 *
 * Enter envia e Shift+Enter quebra linha, que e a convencao de qualquer
 * interface de conversa. Sem isso a pessoa digita, aperta Enter, ganha
 * uma linha em branco e precisa procurar o botao com o mouse.
 *
 * Durante a gravacao o campo exibe a transcricao parcial e fica somente
 * leitura: editar um texto que o reconhecedor vai sobrescrever no
 * proximo evento produziria perda silenciosa do que a pessoa digitou.
 *
 * O campo cresce com o texto ate 168 px e passa a rolar dali em diante.
 * Ao receber o foco, um brilho prateado percorre a borda uma vez: e a
 * unica ousadia visual da interface, e nao se repete em loop.
 */

import { type FormEvent, type KeyboardEvent, type Ref, useLayoutEffect, useRef } from "react";

import { BotaoMicrofone } from "@/componentes/chat/BotaoMicrofone";
import { Button } from "@/componentes/ui/button";
import { IconeEnviar } from "@/componentes/ui/icones";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/componentes/ui/tooltip";
import type { EstadoVoz } from "@/hooks/useMicrofone";

interface Props {
  valor: string;
  estadoVoz: EstadoVoz;
  parcial: string;
  onAlterar: (valor: string) => void;
  onEnviar: () => void;
  onAlternarVoz: () => void;
  /** Permite a quem usa o campo devolver o foco a ele, depois de escolher uma sugestao. */
  refCampo?: Ref<HTMLTextAreaElement>;
}

const ESPERADO: Record<EstadoVoz, string> = {
  ocioso: "Pergunte sobre status, marcos ou riscos",
  solicitando: "Preparando o microfone...",
  gravando: "Ouvindo... fale agora",
  processando: "Transcrevendo...",
  erro: "Pergunte sobre status, marcos ou riscos",
};

const ALTURA_MAXIMA = 168;

export function Composer({ valor, estadoVoz, parcial, onAlterar, onEnviar, onAlternarVoz, refCampo }: Props) {
  const capturando = estadoVoz === "gravando" || estadoVoz === "processando";
  const texto = capturando ? parcial : valor;
  const caixa = useRef<HTMLFormElement>(null);
  const campo = useRef<HTMLTextAreaElement | null>(null);

  // `field-sizing: content` resolveria isto em CSS, mas ainda nao tem
  // suporte amplo; medir o `scrollHeight` funciona em todo navegador.
  useLayoutEffect(() => {
    const elemento = campo.current;
    if (!elemento) return;
    elemento.style.height = "auto";
    elemento.style.height = `${Math.min(elemento.scrollHeight, ALTURA_MAXIMA)}px`;
  }, [texto]);

  function ligarCampo(elemento: HTMLTextAreaElement | null) {
    campo.current = elemento;
    if (typeof refCampo === "function") refCampo(elemento);
    else if (refCampo) refCampo.current = elemento;
  }

  // O brilho reinicia a cada foco: tirar o atributo, forcar um reflow e
  // repor faz o navegador tratar a animacao como nova.
  function brilhar() {
    const elemento = caixa.current;
    if (!elemento) return;
    elemento.removeAttribute("data-brilho");
    void elemento.offsetWidth;
    elemento.setAttribute("data-brilho", "");
  }

  function submeter(evento: FormEvent) {
    evento.preventDefault();
    onEnviar();
  }

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key !== "Enter" || evento.shiftKey) return;
    // `isComposing` marca o texto intermediario de teclados com acento
    // morto e de idiomas com IME. Enviar nesse momento cortaria a
    // palavra no meio da composicao.
    if (evento.nativeEvent.isComposing) return;
    evento.preventDefault();
    onEnviar();
  }

  const podeEnviar = Boolean(valor.trim()) && !capturando;

  return (
    <form
      ref={caixa}
      onSubmit={submeter}
      data-voz={estadoVoz}
      className="caixa-mensagem group/caixa mx-auto w-full max-w-190 rounded-2xl border bg-card pt-3 pr-2.5 pb-2.5 pl-4 shadow-2 transition-[border-color,box-shadow,translate] duration-200 ease-padrao focus-within:border-primary/50 focus-within:shadow-3 focus-within:ring-4 focus-within:ring-primary/15 motion-safe:focus-within:-translate-y-0.5 data-[voz=gravando]:border-gravacao/55"
    >
      <label htmlFor="campo-mensagem" className="sr-only">
        Campo de mensagem
      </label>
      <textarea
        id="campo-mensagem"
        ref={ligarCampo}
        value={texto}
        onChange={(evento) => onAlterar(evento.target.value)}
        onKeyDown={aoTeclar}
        onFocus={brilhar}
        placeholder={ESPERADO[estadoVoz]}
        aria-label="Mensagem"
        aria-describedby="dica-envio"
        readOnly={capturando}
        rows={1}
        className="block max-h-42 min-h-6 w-full resize-none border-0 bg-transparent py-0.5 text-[15px] leading-normal text-foreground outline-none placeholder:text-muted-foreground focus-visible:outline-none"
      />
      <div className="mt-2 flex items-center justify-end gap-1.5">
        {/* Aqui ficavam tres icones sem rotulo nem acao, um falso seletor
            com uma seta que nao abria nada e o selo fixo do "Projeto X".
            Quando houver troca de projeto ou anexo de arquivo, eles entram
            como controles de verdade, com nome acessivel. */}
        <span
          aria-hidden="true"
          className="mr-auto hidden translate-y-0.5 text-xs text-muted-foreground opacity-0 transition-[opacity,translate] duration-200 group-focus-within/caixa:translate-y-0 group-focus-within/caixa:opacity-100 md:inline"
        >
          Enter envia, Shift+Enter quebra a linha
        </span>
        <BotaoMicrofone estado={estadoVoz} onAlternar={onAlternarVoz} />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="submit"
              size="icon"
              aria-label="Enviar mensagem"
              disabled={!podeEnviar}
              className="rounded-[11px] bg-primary text-primary-foreground transition-[background-color,color,scale,box-shadow] duration-280 ease-saida hover:bg-primario-hover active:scale-95 disabled:scale-[.92] disabled:bg-secondary disabled:text-muted-foreground disabled:opacity-100 [&_svg:not([class*='size-'])]:size-4.5"
            >
              <IconeEnviar aria-hidden="true" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" sideOffset={6}>
            Enviar mensagem
          </TooltipContent>
        </Tooltip>
      </div>
      <p id="dica-envio" className="sr-only">
        Pressione Enter para enviar e Shift mais Enter para quebrar linha.
      </p>
    </form>
  );
}
