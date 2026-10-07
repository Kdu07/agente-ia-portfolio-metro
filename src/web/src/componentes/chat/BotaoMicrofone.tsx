/**
 * Acionamento da captura de voz.
 *
 * Precisa de estado visivel enquanto grava: sem retorno visual a pessoa
 * nao sabe se o microfone esta ativo, e fala para uma tela que nao
 * escuta. O `aria-pressed` carrega o mesmo estado para quem usa leitor
 * de tela, onde a mudanca de cor nao existe.
 *
 * Gravando, o botao fica vermelho, pulsa e troca o microfone pelo quadrado
 * de parar; processando, o icone gira. Sao os dois unicos movimentos em
 * loop da interface, junto com o indicador de digitacao.
 */

import { Button } from "@/componentes/ui/button";
import { IconeCarregando, IconeMicrofone, IconeParar } from "@/componentes/ui/icones";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/componentes/ui/tooltip";
import type { EstadoVoz } from "@/hooks/useMicrofone";
import { cn } from "@/utilitarios/cn";

interface Props {
  estado: EstadoVoz;
  onAlternar: () => void;
}

const ROTULO: Record<EstadoVoz, string> = {
  ocioso: "Iniciar entrada por voz",
  solicitando: "Cancelar entrada por voz",
  gravando: "Parar entrada por voz",
  processando: "Processando a transcrição",
  erro: "Iniciar entrada por voz",
};

export function BotaoMicrofone({ estado, onAlternar }: Props) {
  const ativo = estado === "gravando" || estado === "solicitando";
  const Desenho = estado === "gravando" ? IconeParar : estado === "processando" ? IconeCarregando : IconeMicrofone;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={ROTULO[estado]}
          aria-pressed={ativo}
          disabled={estado === "processando"}
          onClick={onAlternar}
          className={cn(
            "rounded-md bg-secondary text-muted-foreground hover:bg-secondary hover:text-foreground active:scale-95 disabled:opacity-100",
            ativo && "bg-gravacao text-texto-sobre-cor hover:bg-gravacao hover:text-texto-sobre-cor motion-safe:animate-pulso",
          )}
        >
          <Desenho aria-hidden="true" className={cn("size-5", estado === "processando" && "motion-safe:animate-spin")} />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={6}>
        {ROTULO[estado]}
      </TooltipContent>
    </Tooltip>
  );
}
