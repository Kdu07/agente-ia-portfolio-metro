import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ErroApi } from "@/servicos/api";
import { chaves } from "@/servicos/chaves";
import type { Execucao, Rotina, ValidacaoRotina } from "@/tipos";

type FiltroStatus = "todas" | "ativas" | "pausadas";
type Ordenacao = "proximo" | "nome" | "atualizacao";
type ModoFormulario = "criar" | "editar";

interface FormularioRotina {
  nome: string;
  prompt: string;
  agenda_cron: string;
  timezone: string;
  ativa: boolean;
}

const FORMULARIO_VAZIO: FormularioRotina = {
  nome: "",
  prompt: "",
  agenda_cron: "0 8 * * 1-5",
  timezone: "America/Sao_Paulo",
  ativa: true,
};

function descreverAgenda(cron: string) {
  const conhecidas: Record<string, string> = {
    "0 8 * * 1-5": "Seg. a sex., às 08:00",
    "0 9 * * 1": "Toda segunda, às 09:00",
    "0 17 5 * *": "Todo dia 5, às 17:00",
  };
  return conhecidas[cron] ?? `Cron: ${cron}`;
}

function formatarData(valor: string | null) {
  if (!valor) return "Sem execução agendada";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(valor));
}

function validarFormulario(formulario: FormularioRotina) {
  const erros: Partial<Record<keyof FormularioRotina, string>> = {};
  if (formulario.nome.trim().length < 3) erros.nome = "Informe um nome com pelo menos 3 caracteres.";
  if (formulario.prompt.trim().length < 10) erros.prompt = "Descreva a ação da rotina com pelo menos 10 caracteres.";
  if (formulario.agenda_cron.trim().split(/\s+/).length !== 5) erros.agenda_cron = "Use uma expressão cron com cinco campos.";
  if (!formulario.timezone.trim()) erros.timezone = "Selecione um fuso horário.";
  return erros;
}

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
  const [modalAberto, setModalAberto] = useState(false);
  const [modoFormulario, setModoFormulario] = useState<ModoFormulario>("criar");
  const [formulario, setFormulario] = useState(FORMULARIO_VAZIO);
  const [erros, setErros] = useState<Partial<Record<keyof FormularioRotina, string>>>({});
  const [erroOperacao, setErroOperacao] = useState("");
  const [rotinaSelecionada, setRotinaSelecionada] = useState<Rotina | null>(null);
  const [rotinaParaExcluir, setRotinaParaExcluir] = useState<Rotina | null>(null);
  const [rotinaHistorico, setRotinaHistorico] = useState<Rotina | null>(null);
  const [toast, setToast] = useState("");

  const consultaRotinas = useQuery<Rotina[]>({
    queryKey: chaves.rotinas,
    queryFn: () => api.get<Rotina[]>("/rotinas"),
  });
  const rotinas = useMemo(() => consultaRotinas.data ?? [], [consultaRotinas.data]);

  const consultaExecucoes = useQuery<Execucao[]>({
    queryKey: rotinaHistorico ? chaves.execucoesDaRotina(rotinaHistorico.id) : ["rotinas", "sem-selecao", "execucoes"],
    queryFn: () => api.get<Execucao[]>(`/rotinas/${rotinaHistorico!.id}/execucoes`),
    enabled: Boolean(rotinaHistorico),
  });

  const salvarRotina = useMutation({
    mutationFn: async ({ id, dados }: { id?: string; dados: FormularioRotina }) => {
      const validacao = await api.post<ValidacaoRotina>("/rotinas/validar", dados);
      if (!validacao.valida) throw new Error(validacao.erro ?? "A rotina não passou pela validação do backend.");
      return id
        ? api.put<Rotina>(`/rotinas/${id}`, dados)
        : api.post<Rotina>("/rotinas", dados);
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

  const executarRotina = useMutation({
    mutationFn: (id: string) => api.post<Execucao>(`/rotinas/${id}/executar`),
    onSuccess: async (_execucao, id) => {
      await clienteQuery.invalidateQueries({ queryKey: chaves.execucoesDaRotina(id) });
    },
  });

  useEffect(() => {
    if (!toast) return;
    const temporizador = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(temporizador);
  }, [toast]);

  const rotinasVisiveis = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    return [...rotinas]
      .filter((rotina) => {
        const correspondeBusca = !termo || `${rotina.nome} ${rotina.prompt} ${rotina.intencao_prevista ?? ""}`.toLocaleLowerCase("pt-BR").includes(termo);
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

  function abrirCriacao() {
    setModoFormulario("criar");
    setRotinaSelecionada(null);
    setFormulario(FORMULARIO_VAZIO);
    setErros({});
    setErroOperacao("");
    setModalAberto(true);
  }

  function abrirEdicao(rotina: Rotina) {
    setModoFormulario("editar");
    setRotinaSelecionada(rotina);
    setFormulario({ nome: rotina.nome, prompt: rotina.prompt, agenda_cron: rotina.agenda_cron, timezone: rotina.timezone, ativa: rotina.ativa });
    setErros({});
    setErroOperacao("");
    setModalAberto(true);
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novosErros = validarFormulario(formulario);
    setErros(novosErros);
    if (Object.keys(novosErros).length) return;

    setErroOperacao("");
    try {
      await salvarRotina.mutateAsync({
        id: modoFormulario === "editar" ? rotinaSelecionada?.id : undefined,
        dados: formulario,
      });
      setModalAberto(false);
      setToast(modoFormulario === "editar" ? "Rotina atualizada com sucesso." : "Rotina criada com sucesso.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível salvar a rotina."));
    }
  }

  async function alternarStatus(rotina: Rotina) {
    const ativa = !rotina.ativa;
    setErroOperacao("");
    try {
      await alterarStatus.mutateAsync({ rotina, ativa });
      setToast(ativa ? "Rotina ativada." : "Rotina pausada.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível alterar o estado da rotina."));
    }
  }

  async function excluir() {
    if (!rotinaParaExcluir) return;
    setErroOperacao("");
    try {
      await removerRotina.mutateAsync(rotinaParaExcluir.id);
      setRotinaParaExcluir(null);
      setToast("Rotina excluída com sucesso.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível excluir a rotina."));
      setRotinaParaExcluir(null);
    }
  }

  async function executarAgora() {
    if (!rotinaHistorico) return;
    setErroOperacao("");
    try {
      await executarRotina.mutateAsync(rotinaHistorico.id);
      setToast("Rotina executada. O resultado foi adicionado ao histórico.");
    } catch (erro) {
      setErroOperacao(mensagemDoErro(erro, "Não foi possível executar a rotina."));
    }
  }

  const ativas = rotinas.filter((rotina) => rotina.ativa).length;
  const operacaoEmCurso = salvarRotina.isPending || alterarStatus.isPending || removerRotina.isPending;

  return (
    <div className="page routines-page">
      <header className="topbar routines-topbar">
        <div className="assistant-title"><span className="brand-mark brand-mark--letter" aria-hidden="true">R</span><span><strong>Rotinas</strong><small>Automatize acompanhamentos recorrentes</small></span></div>
        <button className="primary-button" type="button" onClick={abrirCriacao}>+ Nova rotina</button>
      </header>

      <main className="routines-content">
        <section className="routines-heading" aria-labelledby="rotinas-titulo">
          <div><p className="eyebrow">Automação do portfólio</p><h1 id="rotinas-titulo">Gerencie suas rotinas</h1><p>Configure consultas recorrentes e acompanhe quando cada rotina será executada.</p></div>
          <div className="routines-summary" aria-label="Resumo das rotinas"><span><strong>{rotinas.length}</strong><small>Total</small></span><span><strong>{ativas}</strong><small>Ativas</small></span><span><strong>{rotinas.length - ativas}</strong><small>Pausadas</small></span></div>
        </section>

        {erroOperacao && !modalAberto && !rotinaHistorico ? <div className="routines-error" role="alert">{erroOperacao}</div> : null}

        <section className="routines-toolbar" aria-label="Busca e filtros">
          <label className="search-field"><span aria-hidden="true">⌕</span><input value={busca} onChange={(evento) => setBusca(evento.target.value)} placeholder="Buscar por nome, ação ou intenção" aria-label="Buscar rotinas" /></label>
          <label><span>Status</span><select value={filtro} onChange={(evento) => setFiltro(evento.target.value as FiltroStatus)}><option value="todas">Todas</option><option value="ativas">Ativas</option><option value="pausadas">Pausadas</option></select></label>
          <label><span>Ordenar por</span><select value={ordenacao} onChange={(evento) => setOrdenacao(evento.target.value as Ordenacao)}><option value="proximo">Próxima execução</option><option value="nome">Nome</option><option value="atualizacao">Atualização recente</option></select></label>
        </section>

        {consultaRotinas.isLoading ? (
          <section className="routines-loading" aria-label="Carregando rotinas" aria-live="polite"><span /><span /><span /><p>Carregando rotinas...</p></section>
        ) : consultaRotinas.isError ? (
          <section className="routines-empty routines-empty--error" role="alert"><span aria-hidden="true">!</span><h2>Não foi possível carregar as rotinas</h2><p>{mensagemDoErro(consultaRotinas.error, "Tente novamente em instantes.")}</p><button className="primary-button" type="button" onClick={() => consultaRotinas.refetch()}>Tentar novamente</button></section>
        ) : rotinasVisiveis.length ? (
          <section className="routines-list" aria-label="Rotinas cadastradas">
            {rotinasVisiveis.map((rotina) => (
              <article className="routine-card" key={rotina.id}>
                <div className="routine-card-main">
                  <div className="routine-card-title"><span className={rotina.ativa ? "status-dot status-dot--active" : "status-dot"} /><div><h2>{rotina.nome}</h2><span className={rotina.ativa ? "status-badge status-badge--active" : "status-badge"}>{rotina.ativa ? "Ativa" : "Pausada"}</span></div></div>
                  <p>{rotina.prompt}</p>
                  <dl><div><dt>Frequência</dt><dd>{descreverAgenda(rotina.agenda_cron)}</dd></div><div><dt>Próxima execução</dt><dd>{formatarData(rotina.proximo_disparo)}</dd></div><div><dt>Intenção prevista</dt><dd>{rotina.intencao_prevista ?? "Não classificada"}</dd></div></dl>
                </div>
                <div className="routine-card-actions"><button type="button" className="text-button" disabled={operacaoEmCurso} onClick={() => alternarStatus(rotina)}>{rotina.ativa ? "Pausar" : "Ativar"}</button><button type="button" className="text-button" onClick={() => setRotinaHistorico(rotina)}>Resultados</button><button type="button" className="secondary-button" onClick={() => abrirEdicao(rotina)}>Editar</button><button type="button" className="danger-button" onClick={() => setRotinaParaExcluir(rotina)}>Excluir</button></div>
              </article>
            ))}
          </section>
        ) : (
          <section className="routines-empty" aria-live="polite"><span aria-hidden="true">◇</span><h2>{rotinas.length ? "Nenhuma rotina encontrada" : "Crie sua primeira rotina"}</h2><p>{rotinas.length ? "Tente ajustar a busca ou os filtros selecionados." : "Automatize uma consulta recorrente para acompanhar o portfólio."}</p>{!rotinas.length ? <button className="primary-button" type="button" onClick={abrirCriacao}>Criar rotina</button> : null}</section>
        )}
      </main>

      {modalAberto ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(evento) => { if (evento.target === evento.currentTarget) setModalAberto(false); }}>
          <section className="routine-modal" role="dialog" aria-modal="true" aria-labelledby="formulario-rotina-titulo">
            <header><div><p className="eyebrow">{modoFormulario === "criar" ? "Nova automação" : "Configuração"}</p><h2 id="formulario-rotina-titulo">{modoFormulario === "criar" ? "Criar rotina" : "Editar rotina"}</h2></div><button type="button" className="modal-close" onClick={() => setModalAberto(false)} aria-label="Fechar formulário">×</button></header>
            <form onSubmit={salvar} noValidate>
              {erroOperacao ? <div className="routines-error" role="alert">{erroOperacao}</div> : null}
              <label><span>Nome da rotina *</span><input value={formulario.nome} onChange={(evento) => setFormulario({ ...formulario, nome: evento.target.value })} aria-invalid={Boolean(erros.nome)} aria-describedby={erros.nome ? "erro-nome" : undefined} placeholder="Ex.: Resumo semanal do portfólio" />{erros.nome ? <small className="field-error" id="erro-nome">{erros.nome}</small> : null}</label>
              <label><span>Ação em linguagem natural *</span><textarea value={formulario.prompt} onChange={(evento) => setFormulario({ ...formulario, prompt: evento.target.value })} aria-invalid={Boolean(erros.prompt)} aria-describedby={erros.prompt ? "erro-prompt" : "ajuda-prompt"} placeholder="Descreva o que o Prata deve consultar ou acompanhar" rows={4} /><small id="ajuda-prompt">O backend validará as guardas e a intenção antes de salvar.</small>{erros.prompt ? <small className="field-error" id="erro-prompt">{erros.prompt}</small> : null}</label>
              <div className="form-grid"><label><span>Agendamento (cron) *</span><input value={formulario.agenda_cron} onChange={(evento) => setFormulario({ ...formulario, agenda_cron: evento.target.value })} aria-invalid={Boolean(erros.agenda_cron)} aria-describedby={erros.agenda_cron ? "erro-agenda" : "ajuda-agenda"} /><small id="ajuda-agenda">Minuto, hora, dia, mês e dia da semana.</small>{erros.agenda_cron ? <small className="field-error" id="erro-agenda">{erros.agenda_cron}</small> : null}</label><label><span>Fuso horário *</span><select value={formulario.timezone} onChange={(evento) => setFormulario({ ...formulario, timezone: evento.target.value })}><option value="America/Sao_Paulo">America/Sao_Paulo</option><option value="UTC">UTC</option></select></label></div>
              <label className="switch-field"><input type="checkbox" checked={formulario.ativa} onChange={(evento) => setFormulario({ ...formulario, ativa: evento.target.checked })} /><span><strong>Rotina ativa</strong><small>Agendar assim que a configuração for salva.</small></span></label>
              <footer><button className="secondary-button" type="button" onClick={() => setModalAberto(false)}>Cancelar</button><button className="primary-button" type="submit" disabled={salvarRotina.isPending}>{salvarRotina.isPending ? "Validando e salvando..." : modoFormulario === "criar" ? "Criar rotina" : "Salvar alterações"}</button></footer>
            </form>
          </section>
        </div>
      ) : null}

      {rotinaParaExcluir ? (
        <div className="modal-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="excluir-rotina-titulo" aria-describedby="excluir-rotina-descricao"><span className="danger-icon" aria-hidden="true">!</span><h2 id="excluir-rotina-titulo">Excluir rotina?</h2><p id="excluir-rotina-descricao">A rotina <strong>{rotinaParaExcluir.nome}</strong> e seu agendamento serão removidos. Rotinas com histórico devem ser pausadas para preservar a auditoria.</p><div><button className="secondary-button" type="button" onClick={() => setRotinaParaExcluir(null)}>Cancelar</button><button className="danger-button danger-button--solid" type="button" disabled={removerRotina.isPending} onClick={excluir}>{removerRotina.isPending ? "Excluindo..." : "Excluir rotina"}</button></div></section></div>
      ) : null}

      {rotinaHistorico ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(evento) => { if (evento.target === evento.currentTarget) setRotinaHistorico(null); }}>
          <section className="routine-modal routine-history" role="dialog" aria-modal="true" aria-labelledby="historico-rotina-titulo">
            <header><div><p className="eyebrow">Resultados da rotina</p><h2 id="historico-rotina-titulo">{rotinaHistorico.nome}</h2></div><button type="button" className="modal-close" onClick={() => setRotinaHistorico(null)} aria-label="Fechar histórico">×</button></header>
            <div className="routine-history-content">
              <button className="primary-button" type="button" disabled={executarRotina.isPending} onClick={executarAgora}>{executarRotina.isPending ? "Executando..." : "Executar agora"}</button>
              {erroOperacao ? <div className="routines-error" role="alert">{erroOperacao}</div> : null}
              {consultaExecucoes.isLoading ? <p role="status">Carregando histórico...</p> : null}
              {consultaExecucoes.isError ? <div className="routines-error" role="alert">{mensagemDoErro(consultaExecucoes.error, "Não foi possível carregar o histórico.")}</div> : null}
              {!consultaExecucoes.isLoading && !consultaExecucoes.isError && !consultaExecucoes.data?.length ? <p className="routine-history-empty">Esta rotina ainda não possui execuções.</p> : null}
              {consultaExecucoes.data?.length ? <ol className="routine-executions">{consultaExecucoes.data.map((execucao) => <li key={execucao.id}><header><strong>{formatarData(execucao.iniciada_em)}</strong><span className={`execution-status execution-status--${execucao.status}`}>{execucao.status.replace("_", " ")}</span></header><p>{execucao.resposta ?? execucao.erro ?? "Execução encerrada sem resposta."}</p>{execucao.desfecho ? <small>Desfecho: {execucao.desfecho}</small> : null}</li>)}</ol> : null}
            </div>
          </section>
        </div>
      ) : null}

      {toast ? <div className="toast-success" role="status"><span aria-hidden="true">✓</span>{toast}</div> : null}
    </div>
  );
}
