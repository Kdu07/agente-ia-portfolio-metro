/**
 * Gestão de rotinas: consultas recorrentes que a Prata executa sozinha.
 *
 * A tela junta as peças da pasta: `agenda.ts` converte a frequência em
 * cron, `LinhaRotina` mostra cada rotina, e os três diálogos (formulário,
 * resultados e exclusão) prendem o foco e fecham com Esc. As mensagens de
 * sucesso saem em aviso (toast); os erros ficam na página ou no diálogo
 * aberto, como `role="alert"`, porque pedem ação.
 */

import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Button } from "@/componentes/ui/button";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/componentes/ui/dropdown-menu";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { IconeAdicionar, IconeAviso, IconeBuscar, IconeOrdenar, IconeRotinas } from "@/componentes/ui/icones";
import { Input } from "@/componentes/ui/input";
import { Skeleton } from "@/componentes/ui/skeleton";
import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";
import type { Rotina, ValidacaoRotina } from "@/tipos";
import {
  dadosParaApi,
  FORMULARIO_VAZIO,
  type FormularioRotina as Formulario,
  formularioDaRotina,
  rotuloDaIntencao,
} from "./agenda";
import { ConfirmarExclusao } from "./ConfirmarExclusao";
import { type FiltroStatus, FiltroSituacao } from "./FiltroSituacao";
import { FormularioRotina } from "./FormularioRotina";
import { LinhaRotina } from "./LinhaRotina";
import { ResultadosRotina } from "./ResultadosRotina";

type Ordenacao = "proximo" | "nome" | "atualizacao";

const ORDENACOES: { valor: Ordenacao; rotulo: string }[] = [
  { valor: "proximo", rotulo: "Próxima execução" },
  { valor: "nome", rotulo: "Nome" },
  { valor: "atualizacao", rotulo: "Atualização recente" },
];

function mensagemDoErro(erro: unknown, alternativa: string) {
  if (erro instanceof ErroApi) return erro.detalhe;
  if (erro instanceof Error && erro.message) return erro.message;
  return alternativa;
}

export function Rotinas() {
  const clienteQuery = useQueryClient();
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<FiltroStatus>("todas");
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("proximo");

  const [formularioAberto, setFormularioAberto] = useState(false);
  const [modo, setModo] = useState<"criar" | "editar">("criar");
  const [rotinaEditada, setRotinaEditada] = useState<Rotina | null>(null);
  const [inicial, setInicial] = useState<Formulario>(FORMULARIO_VAZIO);
  // Remonta o formulário a cada abertura, para ele começar dos dados de
  // quem o abriu, e não do que sobrou da vez anterior.
  const [versaoFormulario, setVersaoFormulario] = useState(0);
  const [erroFormulario, setErroFormulario] = useState("");

  const [erroOperacao, setErroOperacao] = useState("");
  const [rotinaParaExcluir, setRotinaParaExcluir] = useState<Rotina | null>(null);
  const [rotinaResultados, setRotinaResultados] = useState<Rotina | null>(null);
  const botaoNovaRotina = useRef<HTMLButtonElement>(null);

  const consultaRotinas = useQuery<Rotina[]>({
    queryKey: chaves.rotinas,
    queryFn: () => api.get<Rotina[]>("/rotinas"),
  });
  const rotinas = useMemo(() => consultaRotinas.data ?? [], [consultaRotinas.data]);

  const salvarRotina = useMutation({
    mutationFn: async ({ id, formulario }: { id?: string; formulario: Formulario }) => {
      const dados = dadosParaApi(formulario);
      const validacao = await api.post<ValidacaoRotina>("/rotinas/validar", dados);
      if (!validacao.valida) throw new Error(validacao.erro ?? "A rotina não passou pela validação do backend.");
      return id ? api.put<Rotina>(`/rotinas/${id}`, dados) : api.post<Rotina>("/rotinas", dados);
    },
    onSuccess: async () => clienteQuery.invalidateQueries({ queryKey: chaves.rotinas }),
  });

  const alterarStatus = useMutation({
    mutationFn: ({ rotina, ativa }: { rotina: Rotina; ativa: boolean }) =>
      api.put<Rotina>(`/rotinas/${rotina.id}`, {
        nome: rotina.nome,
        prompt: rotina.prompt,
        agenda_cron: rotina.agenda_cron,
        timezone: rotina.timezone,
        ativa,
      }),
    onSuccess: async () => clienteQuery.invalidateQueries({ queryKey: chaves.rotinas }),
  });

  const removerRotina = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/rotinas/${id}`),
    onSuccess: async () => clienteQuery.invalidateQueries({ queryKey: chaves.rotinas }),
  });

  const rotinasVisiveis = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    return [...rotinas]
      .filter((rotina) => {
        const texto = `${rotina.nome} ${rotina.prompt} ${rotina.intencao_prevista ?? ""} ${rotuloDaIntencao(rotina)}`;
        const correspondeBusca = !termo || texto.toLocaleLowerCase("pt-BR").includes(termo);
        const correspondeStatus = filtro === "todas" || (filtro === "ativas" ? rotina.ativa : !rotina.ativa);
        return correspondeBusca && correspondeStatus;
      })
      .sort((a, b) => {
        if (ordenacao === "nome") return a.nome.localeCompare(b.nome, "pt-BR");
        if (ordenacao === "atualizacao") return b.atualizada_em.localeCompare(a.atualizada_em);
        if (!a.proximo_disparo) return 1;
        if (!b.proximo_disparo) return -1;
        return a.proximo_disparo.localeCompare(b.proximo_disparo);
      });
  }, [busca, filtro, ordenacao, rotinas]);

  const ativas = rotinas.filter((rotina) => rotina.ativa).length;
  const contagem = { todas: rotinas.length, ativas, pausadas: rotinas.length - ativas };
  const operacaoEmCurso = salvarRotina.isPending || alterarStatus.isPending || removerRotina.isPending;
  const rotuloDaOrdenacao = ORDENACOES.find((opcao) => opcao.valor === ordenacao)?.rotulo ?? "";

  function abrirFormulario(rotina: Rotina | null) {
    setModo(rotina ? "editar" : "criar");
    setRotinaEditada(rotina);
    setInicial(rotina ? formularioDaRotina(rotina) : FORMULARIO_VAZIO);
    setVersaoFormulario((versao) => versao + 1);
    setErroFormulario("");
    setErroOperacao("");
    setFormularioAberto(true);
  }

  async function salvar(formulario: Formulario) {
    setErroFormulario("");
    try {
      await salvarRotina.mutateAsync({ id: modo === "editar" ? rotinaEditada?.id : undefined, formulario });
      setFormularioAberto(false);
      toast.success(modo === "editar" ? "Rotina atualizada com sucesso." : "Rotina criada com sucesso.");
    } catch (erro) {
      setErroFormulario(mensagemDoErro(erro, "Não foi possível salvar a rotina."));
    }
  }

  async function alternarStatus(rotina: Rotina) {
    const ativa = !rotina.ativa;
    setErroOperacao("");
    try {
      await alterarStatus.mutateAsync({ rotina, ativa });
      toast.success(ativa ? "Rotina ativada." : "Rotina pausada.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível alterar o estado da rotina."));
    }
  }

  function pedirExclusao(rotina: Rotina) {
    setRotinaParaExcluir(rotina);
  }

  async function excluir() {
    if (!rotinaParaExcluir) return;
    setErroOperacao("");
    try {
      await removerRotina.mutateAsync(rotinaParaExcluir.id);
      setRotinaParaExcluir(null);
      toast.success("Rotina excluída com sucesso.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível excluir a rotina."));
      setRotinaParaExcluir(null);
    }
  }

  let lista;
  if (consultaRotinas.isLoading) {
    lista = (
      <div role="status" className="grid gap-px overflow-hidden rounded-xl border bg-border">
        <span className="sr-only">Carregando rotinas...</span>
        {[0, 1, 2].map((indice) => (
          <div key={indice} className="grid gap-2.5 bg-card px-4.5 py-4">
            <Skeleton className="h-4 w-1/3 bg-muted" />
            <Skeleton className="h-3 w-2/3 bg-muted" />
          </div>
        ))}
      </div>
    );
  } else if (consultaRotinas.isError) {
    lista = (
      <div role="alert" className="grid max-w-135 justify-items-start gap-2 rounded-xl border border-destructive/40 bg-card p-6">
        <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-destructive/10 text-destructive">
          <IconeAviso aria-hidden="true" />
        </span>
        <h2 className="text-base font-semibold">Não foi possível carregar as rotinas</h2>
        <p className="text-sm text-muted-foreground">{mensagemDoErro(consultaRotinas.error, "Tente novamente em instantes.")}</p>
        <Button type="button" variant="outline" className="mt-2" onClick={() => void consultaRotinas.refetch()}>
          Tentar novamente
        </Button>
      </div>
    );
  } else if (rotinasVisiveis.length) {
    lista = (
      <section aria-label="Rotinas cadastradas" className="divide-y overflow-hidden rounded-xl border bg-card">
        {rotinasVisiveis.map((rotina) => (
          <LinhaRotina
            key={rotina.id}
            rotina={rotina}
            operacaoEmCurso={operacaoEmCurso}
            onAlternar={alternarStatus}
            onResultados={setRotinaResultados}
            onEditar={abrirFormulario}
            onExcluir={pedirExclusao}
          />
        ))}
      </section>
    );
  } else {
    lista = rotinas.length ? (
      <EstadoVazio
        icone={IconeBuscar}
        titulo="Nenhuma rotina encontrada"
        descricao="Tente ajustar a busca ou o filtro de situação."
      />
    ) : (
      // Sem botão próprio: o "Nova rotina" do topo já é o primário da
      // página, e dois primários para a mesma ação dividem a atenção.
      <EstadoVazio
        icone={IconeRotinas}
        titulo="Crie sua primeira rotina"
        descricao="Automatize uma consulta recorrente para acompanhar o portfólio sem precisar pedir. Comece por Nova rotina."
      />
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <CabecalhoPagina titulo="Rotinas" />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-245 px-3.5 pt-6 pb-10 md:px-6">
          <div className="flex flex-wrap items-end justify-between gap-3.5">
            <div>
              <h1 className="font-display text-[26px]">Rotinas</h1>
              <p className="mt-1 text-muted-foreground">Consultas recorrentes que a Prata executa no horário marcado.</p>
            </div>
            <Button ref={botaoNovaRotina} type="button" onClick={() => abrirFormulario(null)}>
              <IconeAdicionar aria-hidden="true" />
              Nova rotina
            </Button>
          </div>

          <div className="mt-5 mb-3.5 flex flex-wrap items-center gap-2.5">
            <FiltroSituacao valor={filtro} contagem={contagem} onMudar={setFiltro} />
            <label className="relative min-w-50 flex-1">
              <IconeBuscar
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 left-3 size-4.5 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                value={busca}
                onChange={(evento) => setBusca(evento.target.value)}
                aria-label="Buscar rotinas"
                placeholder="Buscar por nome, ação ou intenção"
                className="h-9 bg-card pl-9"
              />
            </label>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="outline" aria-label={`Ordenar por ${rotuloDaOrdenacao.toLocaleLowerCase("pt-BR")}`}>
                  <IconeOrdenar aria-hidden="true" />
                  {rotuloDaOrdenacao}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-52 rounded-lg p-1.5 shadow-3">
                <DropdownMenuLabel className="px-2 pt-1 pb-1.5 text-xs font-normal text-muted-foreground">Ordenar por</DropdownMenuLabel>
                <DropdownMenuRadioGroup value={ordenacao} onValueChange={(valor) => setOrdenacao(valor as Ordenacao)}>
                  {ORDENACOES.map((opcao) => (
                    <DropdownMenuRadioItem key={opcao.valor} value={opcao.valor} className="rounded-md text-[13.5px]">
                      {opcao.rotulo}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {erroOperacao ? (
            <p role="alert" className="mb-3.5 flex gap-2 rounded-md border border-destructive/40 bg-card px-3.5 py-2.5 text-sm text-foreground">
              <IconeAviso aria-hidden="true" className="mt-px size-4.5 shrink-0 text-destructive" />
              {erroOperacao}
            </p>
          ) : null}

          {lista}
        </div>
      </div>

      <FormularioRotina
        key={versaoFormulario}
        aberto={formularioAberto}
        modo={modo}
        inicial={inicial}
        salvando={salvarRotina.isPending}
        erro={erroFormulario}
        onFechar={() => setFormularioAberto(false)}
        onSalvar={salvar}
      />
      <ResultadosRotina rotina={rotinaResultados} onFechar={() => setRotinaResultados(null)} />
      <ConfirmarExclusao
        rotina={rotinaParaExcluir}
        excluindo={removerRotina.isPending}
        onCancelar={() => setRotinaParaExcluir(null)}
        onConfirmar={() => void excluir()}
        focoAlternativo={botaoNovaRotina.current}
      />
    </div>
  );
}
