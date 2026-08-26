import { type FormEvent, useEffect, useMemo, useState } from "react";

import type { Rotina } from "@/tipos";

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

const ROTINAS_DEMONSTRACAO: Rotina[] = [
  {
    id: "rotina-status-semanal",
    nome: "Resumo semanal do portfólio",
    prompt: "Consolidar o status, os riscos e os próximos marcos dos projetos ativos.",
    agenda_cron: "0 9 * * 1",
    timezone: "America/Sao_Paulo",
    ativa: true,
    intencao_prevista: "Consultar status do portfólio",
    proximo_disparo: "2026-08-31T09:00:00-03:00",
    criada_em: "2026-08-12T14:20:00-03:00",
    atualizada_em: "2026-08-25T16:10:00-03:00",
  },
  {
    id: "rotina-riscos",
    nome: "Riscos da Linha 6",
    prompt: "Listar riscos críticos da Linha 6 sem atualização há mais de sete dias.",
    agenda_cron: "0 8 * * 1-5",
    timezone: "America/Sao_Paulo",
    ativa: true,
    intencao_prevista: "Consultar riscos do projeto",
    proximo_disparo: "2026-08-27T08:00:00-03:00",
    criada_em: "2026-08-14T10:30:00-03:00",
    atualizada_em: "2026-08-24T11:45:00-03:00",
  },
  {
    id: "rotina-marcos",
    nome: "Revisão mensal de marcos",
    prompt: "Identificar marcos atrasados e preparar um resumo para a reunião do PMO.",
    agenda_cron: "0 17 5 * *",
    timezone: "America/Sao_Paulo",
    ativa: false,
    intencao_prevista: "Consultar marcos atrasados",
    proximo_disparo: null,
    criada_em: "2026-08-08T09:00:00-03:00",
    atualizada_em: "2026-08-20T15:20:00-03:00",
  },
];

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

export function Rotinas() {
  const [rotinas, setRotinas] = useState(ROTINAS_DEMONSTRACAO);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<FiltroStatus>("todas");
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("proximo");
  const [modalAberto, setModalAberto] = useState(false);
  const [modoFormulario, setModoFormulario] = useState<ModoFormulario>("criar");
  const [formulario, setFormulario] = useState(FORMULARIO_VAZIO);
  const [erros, setErros] = useState<Partial<Record<keyof FormularioRotina, string>>>({});
  const [rotinaSelecionada, setRotinaSelecionada] = useState<Rotina | null>(null);
  const [rotinaParaExcluir, setRotinaParaExcluir] = useState<Rotina | null>(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    const temporizador = window.setTimeout(() => setCarregando(false), 350);
    return () => window.clearTimeout(temporizador);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const temporizador = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(temporizador);
  }, [toast]);

  const rotinasVisiveis = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    return rotinas
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
    setModalAberto(true);
  }

  function abrirEdicao(rotina: Rotina) {
    setModoFormulario("editar");
    setRotinaSelecionada(rotina);
    setFormulario({ nome: rotina.nome, prompt: rotina.prompt, agenda_cron: rotina.agenda_cron, timezone: rotina.timezone, ativa: rotina.ativa });
    setErros({});
    setModalAberto(true);
  }

  function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novosErros = validarFormulario(formulario);
    setErros(novosErros);
    if (Object.keys(novosErros).length) return;

    const agora = new Date().toISOString();
    if (modoFormulario === "editar" && rotinaSelecionada) {
      setRotinas((atuais) => atuais.map((rotina) => rotina.id === rotinaSelecionada.id ? {
        ...rotina,
        ...formulario,
        proximo_disparo: formulario.ativa ? rotina.proximo_disparo ?? new Date(Date.now() + 86_400_000).toISOString() : null,
        atualizada_em: agora,
      } : rotina));
      setToast("Rotina atualizada com sucesso.");
    } else {
      setRotinas((atuais) => [{
        id: `rotina-${Date.now()}`,
        ...formulario,
        intencao_prevista: "A validar pelo backend",
        proximo_disparo: formulario.ativa ? new Date(Date.now() + 86_400_000).toISOString() : null,
        criada_em: agora,
        atualizada_em: agora,
      }, ...atuais]);
      setToast("Rotina criada com sucesso.");
    }
    setModalAberto(false);
  }

  function alternarStatus(rotina: Rotina) {
    const ativa = !rotina.ativa;
    setRotinas((atuais) => atuais.map((item) => item.id === rotina.id ? {
      ...item,
      ativa,
      proximo_disparo: ativa ? new Date(Date.now() + 86_400_000).toISOString() : null,
      atualizada_em: new Date().toISOString(),
    } : item));
    setToast(ativa ? "Rotina ativada." : "Rotina pausada.");
  }

  function excluir() {
    if (!rotinaParaExcluir) return;
    setRotinas((atuais) => atuais.filter((rotina) => rotina.id !== rotinaParaExcluir.id));
    setRotinaParaExcluir(null);
    setToast("Rotina excluída com sucesso.");
  }

  const ativas = rotinas.filter((rotina) => rotina.ativa).length;

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

        <section className="routines-toolbar" aria-label="Busca e filtros">
          <label className="search-field"><span aria-hidden="true">⌕</span><input value={busca} onChange={(evento) => setBusca(evento.target.value)} placeholder="Buscar por nome, ação ou intenção" aria-label="Buscar rotinas" /></label>
          <label><span>Status</span><select value={filtro} onChange={(evento) => setFiltro(evento.target.value as FiltroStatus)}><option value="todas">Todas</option><option value="ativas">Ativas</option><option value="pausadas">Pausadas</option></select></label>
          <label><span>Ordenar por</span><select value={ordenacao} onChange={(evento) => setOrdenacao(evento.target.value as Ordenacao)}><option value="proximo">Próxima execução</option><option value="nome">Nome</option><option value="atualizacao">Atualização recente</option></select></label>
        </section>

        {carregando ? (
          <section className="routines-loading" aria-label="Carregando rotinas" aria-live="polite"><span /><span /><span /><p>Carregando rotinas...</p></section>
        ) : rotinasVisiveis.length ? (
          <section className="routines-list" aria-label="Rotinas cadastradas">
            {rotinasVisiveis.map((rotina) => (
              <article className="routine-card" key={rotina.id}>
                <div className="routine-card-main">
                  <div className="routine-card-title"><span className={rotina.ativa ? "status-dot status-dot--active" : "status-dot"} /><div><h2>{rotina.nome}</h2><span className={rotina.ativa ? "status-badge status-badge--active" : "status-badge"}>{rotina.ativa ? "Ativa" : "Pausada"}</span></div></div>
                  <p>{rotina.prompt}</p>
                  <dl><div><dt>Frequência</dt><dd>{descreverAgenda(rotina.agenda_cron)}</dd></div><div><dt>Próxima execução</dt><dd>{formatarData(rotina.proximo_disparo)}</dd></div><div><dt>Intenção prevista</dt><dd>{rotina.intencao_prevista ?? "Não classificada"}</dd></div></dl>
                </div>
                <div className="routine-card-actions"><button type="button" className="text-button" onClick={() => alternarStatus(rotina)}>{rotina.ativa ? "Pausar" : "Ativar"}</button><button type="button" className="secondary-button" onClick={() => abrirEdicao(rotina)}>Editar</button><button type="button" className="danger-button" onClick={() => setRotinaParaExcluir(rotina)}>Excluir</button></div>
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
              <label><span>Nome da rotina *</span><input value={formulario.nome} onChange={(evento) => setFormulario({ ...formulario, nome: evento.target.value })} aria-invalid={Boolean(erros.nome)} aria-describedby={erros.nome ? "erro-nome" : undefined} placeholder="Ex.: Resumo semanal do portfólio" />{erros.nome ? <small className="field-error" id="erro-nome">{erros.nome}</small> : null}</label>
              <label><span>Ação em linguagem natural *</span><textarea value={formulario.prompt} onChange={(evento) => setFormulario({ ...formulario, prompt: evento.target.value })} aria-invalid={Boolean(erros.prompt)} aria-describedby={erros.prompt ? "erro-prompt" : "ajuda-prompt"} placeholder="Descreva o que o Prata deve consultar ou acompanhar" rows={4} /><small id="ajuda-prompt">O backend validará a intenção antes de salvar definitivamente.</small>{erros.prompt ? <small className="field-error" id="erro-prompt">{erros.prompt}</small> : null}</label>
              <div className="form-grid"><label><span>Agendamento (cron) *</span><input value={formulario.agenda_cron} onChange={(evento) => setFormulario({ ...formulario, agenda_cron: evento.target.value })} aria-invalid={Boolean(erros.agenda_cron)} aria-describedby={erros.agenda_cron ? "erro-agenda" : "ajuda-agenda"} /><small id="ajuda-agenda">Minuto, hora, dia, mês e dia da semana.</small>{erros.agenda_cron ? <small className="field-error" id="erro-agenda">{erros.agenda_cron}</small> : null}</label><label><span>Fuso horário *</span><select value={formulario.timezone} onChange={(evento) => setFormulario({ ...formulario, timezone: evento.target.value })}><option value="America/Sao_Paulo">America/Sao_Paulo</option><option value="UTC">UTC</option></select></label></div>
              <label className="switch-field"><input type="checkbox" checked={formulario.ativa} onChange={(evento) => setFormulario({ ...formulario, ativa: evento.target.checked })} /><span><strong>Rotina ativa</strong><small>Agendar assim que a configuração for salva.</small></span></label>
              <footer><button className="secondary-button" type="button" onClick={() => setModalAberto(false)}>Cancelar</button><button className="primary-button" type="submit">{modoFormulario === "criar" ? "Criar rotina" : "Salvar alterações"}</button></footer>
            </form>
          </section>
        </div>
      ) : null}

      {rotinaParaExcluir ? (
        <div className="modal-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="excluir-rotina-titulo" aria-describedby="excluir-rotina-descricao"><span className="danger-icon" aria-hidden="true">!</span><h2 id="excluir-rotina-titulo">Excluir rotina?</h2><p id="excluir-rotina-descricao">A rotina <strong>{rotinaParaExcluir.nome}</strong> e seu agendamento serão removidos. Esta ação não poderá ser desfeita.</p><div><button className="secondary-button" type="button" onClick={() => setRotinaParaExcluir(null)}>Cancelar</button><button className="danger-button danger-button--solid" type="button" onClick={excluir}>Excluir rotina</button></div></section></div>
      ) : null}

      {toast ? <div className="toast-success" role="status"><span aria-hidden="true">✓</span>{toast}</div> : null}
    </div>
  );
}
