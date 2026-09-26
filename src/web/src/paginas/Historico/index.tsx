/**
 * Lista de conversas anteriores, com retomada.
 *
 * Cada usuario ve apenas o proprio historico: o isolamento vem do filtro
 * por usuario no backend, nunca da obscuridade do identificador.
 *
 * Excluir da lista ARQUIVA. As interacoes sobrevivem, porque apagar o
 * registro quebraria a rastreabilidade exigida pelo pipeline. A tela diz
 * isso na confirmacao, para ninguem arquivar achando que apagou.
 *
 * As conversas vem agrupadas por data (Hoje, Ontem, Esta semana,
 * Anteriores), como nas Recentes da barra lateral, e a busca filtra pelo
 * titulo sem ir ao servidor.
 */

import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/componentes/ui/alert-dialog";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { Button } from "@/componentes/ui/button";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { IconeArquivar, IconeAviso, IconeBuscar, IconeConversa, IconeHistorico } from "@/componentes/ui/icones";
import { Input } from "@/componentes/ui/input";
import { Skeleton } from "@/componentes/ui/skeleton";
import { CHAVE_CONVERSA_ATIVA } from "@/hooks/useConversa";
import { useConversas } from "@/hooks/useConversas";
import { useFocoDeVolta } from "@/hooks/useFocoDeVolta";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";
import type { ConversaResumo } from "@/tipos";
import { agruparPorData, quandoFoi } from "@/utilitarios/formato";

function tituloDe(conversa: ConversaResumo) {
  return conversa.titulo ?? "Conversa sem título";
}

export function Historico() {
  const { conversas, carregando, erro, tentarNovamente } = useConversas();
  const clienteQuery = useQueryClient();
  const [busca, setBusca] = useState("");
  const [paraArquivar, setParaArquivar] = useState<ConversaResumo | null>(null);
  const [exibida, setExibida] = useState(paraArquivar);
  if (paraArquivar && paraArquivar !== exibida) setExibida(paraArquivar);
  const [erroArquivar, setErroArquivar] = useState("");
  const campoBusca = useRef<HTMLInputElement>(null);
  // Arquivada, a conversa sai da lista junto com o botao que abriu a
  // confirmacao; o foco vai para a busca.
  const devolverFoco = useFocoDeVolta(Boolean(paraArquivar));

  const arquivar = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/conversas/${id}`),
    onSuccess: async (_resposta, id) => {
      // A conversa arquivada nao pode continuar sendo a "ativa": voltar a
      // pagina principal tentaria reabri-la.
      if (sessionStorage.getItem(CHAVE_CONVERSA_ATIVA) === id) sessionStorage.removeItem(CHAVE_CONVERSA_ATIVA);
      await clienteQuery.invalidateQueries({ queryKey: chaves.conversas });
    },
  });

  async function confirmarArquivamento() {
    if (!paraArquivar) return;
    setErroArquivar("");
    try {
      await arquivar.mutateAsync(paraArquivar.id);
      setParaArquivar(null);
      toast.success("Conversa arquivada.");
    } catch (falha) {
      setErroArquivar(falha instanceof ErroApi ? falha.detalhe : "Não foi possível arquivar a conversa.");
      setParaArquivar(null);
    }
  }

  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  const filtradas = termo
    ? conversas.filter((conversa) => tituloDe(conversa).toLocaleLowerCase("pt-BR").includes(termo))
    : conversas;
  const grupos = agruparPorData(filtradas, (conversa) => conversa.atualizada_em);

  let conteudo;
  if (carregando) {
    conteudo = (
      <div role="status" className="grid gap-2">
        <span className="sr-only">Carregando histórico...</span>
        {[0, 1, 2].map((indice) => (
          <Skeleton key={indice} className="h-16 rounded-lg bg-muted" />
        ))}
      </div>
    );
  } else if (erro) {
    conteudo = (
      <div role="alert" className="grid max-w-135 justify-items-start gap-2 rounded-xl border border-destructive/40 bg-card p-6">
        <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-destructive/10 text-destructive">
          <IconeAviso aria-hidden="true" />
        </span>
        <h2 className="text-base font-semibold">Não foi possível carregar o histórico</h2>
        <p className="text-sm text-muted-foreground">{erro}</p>
        <Button type="button" variant="outline" className="mt-2 bg-card" onClick={() => void tentarNovamente()}>
          Tentar novamente
        </Button>
      </div>
    );
  } else if (conversas.length === 0) {
    conteudo = (
      <EstadoVazio
        icone={IconeHistorico}
        titulo="Nenhuma conversa registrada"
        descricao="As conversas que você tiver com o agente aparecerão aqui, da mais recente para a mais antiga, e poderão ser retomadas de onde pararam."
        acao={
          <Button asChild>
            <Link to="/">Iniciar uma conversa</Link>
          </Button>
        }
      />
    );
  } else {
    conteudo = (
      <>
        <label className="relative mb-2 block max-w-110">
          <IconeBuscar
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 size-4.5 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            ref={campoBusca}
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            aria-label="Buscar conversas"
            placeholder="Buscar pelo título"
            className="h-9 bg-card pl-9"
          />
        </label>

        {filtradas.length === 0 ? (
          <p className="py-6 text-sm text-muted-foreground">Nenhuma conversa com esse título.</p>
        ) : (
          <ul aria-label="Conversas anteriores" className="grid">
            {grupos.map(({ grupo, itens }) => (
              <li key={grupo}>
                <h2 className="mt-4.5 mb-2 px-1 text-[12.5px] font-[550] text-muted-foreground">{grupo}</h2>
                <ul className="grid gap-2">
                  {itens.map((conversa) => (
                    <li
                      key={conversa.id}
                      className="flex items-center gap-1 rounded-lg border bg-card transition-[border-color,box-shadow] hover:border-borda-forte hover:shadow-1"
                    >
                      <Link
                        to={`/conversas/${conversa.id}`}
                        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3.5 py-3"
                      >
                        <span className="grid size-9 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                          <IconeConversa aria-hidden="true" className="size-4.5" />
                        </span>
                        <span className="grid min-w-0">
                          <strong className="truncate text-sm font-semibold text-foreground">{tituloDe(conversa)}</strong>
                          <small className="text-[12.5px] text-muted-foreground tabular-nums">
                            {quandoFoi(conversa.atualizada_em)} · {conversa.total_turnos}{" "}
                            {conversa.total_turnos === 1 ? "turno" : "turnos"}
                          </small>
                        </span>
                      </Link>
                      <BotaoIcone
                        rotulo={`Arquivar ${tituloDe(conversa)}`}
                        icone={IconeArquivar}
                        onClick={() => setParaArquivar(conversa)}
                        className="mr-2 size-8.5 shrink-0"
                      />
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <CabecalhoPagina titulo="Histórico" />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-245 px-3.5 pt-6 pb-10 md:px-6">
          <h1 className="font-display text-[26px]">Histórico de conversas</h1>
          <p className="mt-1 mb-5 text-muted-foreground">
            Retome de onde parou. Arquivar tira a conversa da lista; o registro das interações continua guardado.
          </p>

          {erroArquivar ? (
            <p role="alert" className="mb-3.5 flex gap-2 rounded-md border border-destructive/40 bg-card px-3.5 py-2.5 text-sm text-foreground">
              <IconeAviso aria-hidden="true" className="mt-px size-4.5 shrink-0 text-destructive" />
              {erroArquivar}
            </p>
          ) : null}

          {conteudo}
        </div>
      </div>

      <AlertDialog
        open={Boolean(paraArquivar)}
        onOpenChange={(aberto) => {
          if (!aberto) setParaArquivar(null);
        }}
      >
        <AlertDialogContent
          className="rounded-2xl bg-card p-5.5 shadow-3 sm:max-w-115"
          onCloseAutoFocus={(evento) => devolverFoco(evento, campoBusca.current)}
        >
          <AlertDialogHeader className="items-start text-left">
            <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-primario-suave text-primario-texto">
              <IconeArquivar aria-hidden="true" />
            </span>
            <AlertDialogTitle className="text-[19px] font-[650] font-stretch-106%">Arquivar conversa?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong className="font-semibold text-foreground">{exibida ? tituloDe(exibida) : ""}</strong> sai do
              histórico e das recentes. O registro das interações continua guardado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-card">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={arquivar.isPending}
              onClick={(evento) => {
                evento.preventDefault();
                void confirmarArquivamento();
              }}
            >
              <IconeArquivar aria-hidden="true" />
              {arquivar.isPending ? "Arquivando..." : "Arquivar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
