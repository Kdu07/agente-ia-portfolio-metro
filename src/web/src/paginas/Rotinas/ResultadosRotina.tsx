/**
 * Resultados de uma rotina: as execuções, da mais recente para a mais
 * antiga, e "Executar agora" para testar sem esperar o horário.
 *
 * O status sai em frase, com ícone ("Concluída", "Falhou"), e o desfecho
 * pela mesma etiqueta do chat, vaga nos bloqueios: antes a tela mostrava
 * "EM EXECUCAO" e "Desfecho: bloqueada_injecao_regra".
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { APARENCIA } from "@/componentes/chat/desfechos";
import { Button } from "@/componentes/ui/button";
import { DialogoResponsivo } from "@/componentes/ui/DialogoResponsivo";
import { IconeAviso, IconeExecutar } from "@/componentes/ui/icones";
import { Skeleton } from "@/componentes/ui/skeleton";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";
import { cn } from "@/utilitarios/cn";
import type { Execucao, Rotina } from "@/tipos";
import { formatarData } from "./agenda";
import { STATUS_DE_EXECUCAO } from "./execucoes";

function mensagemDoErro(erro: unknown, alternativa: string) {
  if (erro instanceof ErroApi) return erro.detalhe;
  if (erro instanceof Error && erro.message) return erro.message;
  return alternativa;
}

export function ResultadosRotina({ rotina, onFechar }: { rotina: Rotina | null; onFechar: () => void }) {
  const clienteQuery = useQueryClient();
  const [erro, setErro] = useState("");
  // Guarda a última rotina aberta para o título não sumir enquanto o
  // diálogo fecha.
  const [exibida, setExibida] = useState(rotina);
  if (rotina && rotina !== exibida) setExibida(rotina);

  const execucoes = useQuery<Execucao[]>({
    queryKey: rotina ? chaves.execucoesDaRotina(rotina.id) : ["rotinas", "sem-selecao", "execucoes"],
    queryFn: () => api.get<Execucao[]>(`/rotinas/${rotina!.id}/execucoes`),
    enabled: Boolean(rotina),
  });

  const executar = useMutation({
    mutationFn: (id: string) => api.post<Execucao>(`/rotinas/${id}/executar`),
    onSuccess: async (_execucao, id) => {
      await clienteQuery.invalidateQueries({ queryKey: chaves.execucoesDaRotina(id) });
    },
  });

  async function executarAgora() {
    if (!rotina) return;
    setErro("");
    try {
      await executar.mutateAsync(rotina.id);
      toast.success("Rotina executada. O resultado foi adicionado ao histórico.");
    } catch (falha) {
      setErro(mensagemDoErro(falha, "Não foi possível executar a rotina."));
    }
  }

  function fechar() {
    setErro("");
    onFechar();
  }

  return (
    <DialogoResponsivo
      aberto={Boolean(rotina)}
      onFechar={fechar}
      titulo={exibida?.nome ?? "Resultados"}
      descricao="Execuções desta rotina, da mais recente para a mais antiga."
      larga
    >
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <small className="text-[12.5px] text-muted-foreground">
          {exibida?.ativa ? `Próxima execução: ${formatarData(exibida.proximo_disparo)}` : "Rotina pausada"}
        </small>
        <Button type="button" onClick={executarAgora} disabled={executar.isPending}>
          <IconeExecutar aria-hidden="true" />
          {executar.isPending ? "Executando..." : "Executar agora"}
        </Button>
      </div>

      {erro ? (
        <p role="alert" className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2.5 text-[13px] text-foreground">
          <IconeAviso aria-hidden="true" className="mt-px size-4 shrink-0 text-destructive" />
          {erro}
        </p>
      ) : null}

      {execucoes.isLoading ? (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Carregando execuções...</span>
          <Skeleton className="h-18 rounded-lg bg-muted" />
          <Skeleton className="h-18 rounded-lg bg-muted" />
        </div>
      ) : execucoes.isError ? (
        <p role="alert" className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2.5 text-[13px] text-foreground">
          <IconeAviso aria-hidden="true" className="mt-px size-4 shrink-0 text-destructive" />
          {mensagemDoErro(execucoes.error, "Não foi possível carregar as execuções.")}
        </p>
      ) : !execucoes.data?.length ? (
        <p className="rounded-lg border border-dashed border-borda-forte px-4 py-6 text-center text-sm text-muted-foreground">
          Esta rotina ainda não tem execuções. Use Executar agora para ver a primeira.
        </p>
      ) : (
        <ol className="grid gap-2">
          {execucoes.data.map((execucao) => {
            const status = STATUS_DE_EXECUCAO[execucao.status];
            const Status = status.icone;
            const aparencia = execucao.desfecho ? APARENCIA[execucao.desfecho] : undefined;
            const Etiqueta = aparencia?.icone;
            return (
              <li key={execucao.id} className="grid gap-1.5 rounded-lg border bg-card px-3.5 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2.5">
                  <time dateTime={execucao.iniciada_em} className="text-[13px] font-semibold text-foreground tabular-nums">
                    {formatarData(execucao.iniciada_em)}
                  </time>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.25 rounded-full py-px pr-2.25 pl-1.75 text-xs font-[550] [&_svg]:size-3.5",
                      status.classe,
                    )}
                  >
                    <Status aria-hidden="true" />
                    {status.rotulo}
                  </span>
                </div>
                <p className="text-[13.5px] text-texto">
                  {execucao.resposta ?? execucao.erro ?? "Execução encerrada sem resposta."}
                </p>
                {aparencia?.rotulo && Etiqueta ? (
                  <div>
                    <span className={aparencia.etiqueta}>
                      <Etiqueta aria-hidden="true" />
                      {aparencia.rotulo}
                    </span>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
      )}

      <div className="flex justify-end">
        <Button type="button" variant="outline" onClick={fechar} className="bg-card">
          Fechar
        </Button>
      </div>
    </DialogoResponsivo>
  );
}
