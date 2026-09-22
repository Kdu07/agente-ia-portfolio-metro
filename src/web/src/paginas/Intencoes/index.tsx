/**
 * Dashboard de analise de intencoes. Restrito a `ver_intencoes`.
 *
 * Dois recortes, e a separacao importa:
 *
 * - SEGURANCA: volume de bloqueios por guarda, ao longo do tempo. Injecao,
 *   abuso e saida em series separadas, porque um pico em injecao e
 *   incidente e um pico em abuso e problema de uso. Somar as tres
 *   esconderia os dois.
 * - CATALOGO: o que os usuarios pedem e o agente nao faz
 *   (`fora_de_escopo`) e onde o classificador hesita
 *   (`baixa_confianca`). E o backlog de novas intencoes, e o ponto onde o
 *   ciclo registro -> analise -> catalogo se fecha.
 *
 * Um terceiro bloco, DESEMPENHO, mostra a latencia do pipeline: o custo
 * das barreiras acima, medido.
 *
 * Carregamento, erro e periodo sem dados sao tres estados distintos, com
 * tres apresentacoes distintas. Quem tem acesso mas escolheu um periodo
 * sem mensagens precisa ler "nao houve uso", e nao "algo quebrou": as duas
 * leituras levam a acoes opostas.
 */

import { type ReactNode, useState } from "react";

import {
  BarrasPorIntencao,
  CartaoResumo,
  DistribuicaoDesfechos,
  SerieBloqueios,
  TabelaEnunciados,
} from "@/componentes/graficos";
import { formatarDuracao, formatarInteiro, formatarPercentual } from "@/componentes/graficos/formatos";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { type DadosPainel, type FiltroPerfil, usePainelIntencoes } from "@/hooks/usePainelIntencoes";
import type { Janela } from "@/tipos";

const JANELAS: { valor: Janela; rotulo: string; descricao: string }[] = [
  { valor: "7d", rotulo: "Últimos 7 dias", descricao: "nos últimos 7 dias" },
  { valor: "30d", rotulo: "Últimos 30 dias", descricao: "nos últimos 30 dias" },
  { valor: "90d", rotulo: "Últimos 90 dias", descricao: "nos últimos 90 dias" },
];

const PERFIS: { valor: FiltroPerfil; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos os perfis" },
  { valor: "diretoria", rotulo: "Diretoria" },
  { valor: "lider_projeto", rotulo: "Líder de projeto" },
  { valor: "membro_equipe", rotulo: "Membro de equipe" },
];

const ROTULO_DA_ETAPA: Record<string, string> = {
  injecao: "Guarda de injeção",
  abuso: "Guarda de uso indevido",
  intencao: "Classificação",
  executor: "Executor",
  saida: "Guarda de saída",
};

const CAMPO =
  "mt-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-desfecho-recusa";

export function Intencoes() {
  const [janela, setJanela] = useState<Janela>("30d");
  const [perfil, setPerfil] = useState<FiltroPerfil>("todos");
  const painel = usePainelIntencoes(janela, perfil);
  const descricaoJanela = JANELAS.find((opcao) => opcao.valor === janela)?.descricao ?? "";

  let conteudo: ReactNode;
  if (painel.erro) {
    conteudo = (
      <div role="alert" className="rounded-xl border border-desfecho-injecao bg-white p-6">
        <h2 className="text-base font-semibold text-slate-900">Não foi possível carregar o painel</h2>
        <p className="mt-2 text-sm text-slate-700">{painel.erro}</p>
        <button
          type="button"
          onClick={painel.tentarNovamente}
          className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-50"
        >
          Tentar novamente
        </button>
      </div>
    );
  } else if (painel.carregando || !painel.dados) {
    conteudo = (
      <div role="status" aria-live="polite" className="grid gap-4">
        <span className="sr-only">Carregando o painel de intenções</span>
        <div className="h-28 animate-pulse rounded-xl bg-slate-100" aria-hidden="true" />
        <div className="h-64 animate-pulse rounded-xl bg-slate-100" aria-hidden="true" />
      </div>
    );
  } else if (painel.dados.resumoSeguranca.total_mensagens === 0) {
    conteudo = (
      <EstadoVazio
        titulo="Sem dados no período"
        descricao={`Nenhuma mensagem foi registrada ${descricaoJanela}${
          perfil === "todos" ? "" : " para o perfil selecionado"
        }. Escolha um período maior ou outro perfil para ver os recortes de segurança e de evolução do catálogo.`}
      />
    );
  } else {
    conteudo = <Recortes dados={painel.dados} />;
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="assistant-title">
          <span>
            <strong>Análise de intenções</strong>
            <small>Segurança e evolução do catálogo</small>
          </span>
        </div>
      </header>

      <div className="mx-auto w-[min(1180px,calc(100%-32px))] py-6 sm:py-9">
        <section aria-label="Filtros do painel" className="flex flex-wrap gap-4">
          <label className="flex flex-col text-xs font-medium text-slate-700">
            Período
            <select
              className={CAMPO}
              value={janela}
              onChange={(evento) => setJanela(evento.target.value as Janela)}
            >
              {JANELAS.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-700">
            Perfil
            <select
              className={CAMPO}
              value={perfil}
              onChange={(evento) => setPerfil(evento.target.value as FiltroPerfil)}
            >
              {PERFIS.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          </label>
        </section>

        <div className="mt-6">{conteudo}</div>
      </div>
    </div>
  );
}

function Recortes({ dados }: { dados: DadosPainel }) {
  const seguranca = dados.resumoSeguranca;
  const catalogo = dados.resumoCatalogo;

  return (
    <div className="grid gap-8">
      <section aria-labelledby="recorte-seguranca" className="grid gap-4">
        <h2 id="recorte-seguranca" className="text-lg font-semibold text-slate-900">
          Segurança
        </h2>
        <CartaoResumo
          titulo="Resumo de segurança"
          itens={[
            {
              rotulo: "Mensagens",
              valor: formatarInteiro(seguranca.total_mensagens),
              detalhe: `${formatarPercentual(seguranca.taxa_de_bloqueio)} bloqueadas`,
            },
            { rotulo: "Bloqueios por injeção", valor: formatarInteiro(seguranca.bloqueios_injecao) },
            { rotulo: "Bloqueios por uso indevido", valor: formatarInteiro(seguranca.bloqueios_abuso) },
            { rotulo: "Respostas retidas na saída", valor: formatarInteiro(seguranca.bloqueios_saida) },
          ]}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <SerieBloqueios series={dados.serie} />
          <DistribuicaoDesfechos dados={dados.desfechos} />
        </div>
      </section>

      <section aria-labelledby="recorte-catalogo" className="grid gap-4">
        <h2 id="recorte-catalogo" className="text-lg font-semibold text-slate-900">
          Evolução do catálogo
        </h2>
        <CartaoResumo
          titulo="Resumo do catálogo"
          itens={[
            { rotulo: "Intenções acionadas", valor: formatarInteiro(catalogo.intencoes_acionadas) },
            { rotulo: "Intenções sem uso", valor: formatarInteiro(catalogo.intencoes_sem_uso) },
            { rotulo: "Fora do escopo", valor: formatarInteiro(catalogo.enunciados_fora_de_escopo) },
            { rotulo: "Baixa confiança", valor: formatarInteiro(catalogo.enunciados_baixa_confianca) },
          ]}
        />
        <BarrasPorIntencao dados={dados.volume} />
        <div className="grid gap-4 lg:grid-cols-2">
          <TabelaEnunciados
            titulo="Pedidos fora do escopo"
            enunciados={dados.foraDeEscopo}
            mensagemVazia="Nenhum pedido fora do escopo no período."
          />
          <TabelaEnunciados
            titulo="Pedidos com baixa confiança"
            enunciados={dados.baixaConfianca}
            mensagemVazia="Nenhum pedido com baixa confiança no período."
          />
        </div>
      </section>

      <section aria-labelledby="recorte-desempenho" className="grid gap-4">
        <h2 id="recorte-desempenho" className="text-lg font-semibold text-slate-900">
          Desempenho
        </h2>
        <CartaoResumo
          titulo="Latência do pipeline"
          itens={[
            { rotulo: "Mediana (p50)", valor: formatarDuracao(dados.latencia.p50) },
            { rotulo: "95º percentil (p95)", valor: formatarDuracao(dados.latencia.p95) },
          ]}
        />
        {dados.latencia.etapas.length > 0 ? (
          <CartaoResumo
            titulo="Latência por etapa (p95)"
            itens={dados.latencia.etapas.map((etapa) => ({
              rotulo: ROTULO_DA_ETAPA[etapa.etapa] ?? etapa.etapa,
              valor: etapa.amostras > 0 ? formatarDuracao(etapa.p95) : "—",
              detalhe:
                etapa.amostras > 0
                  ? `${formatarInteiro(etapa.amostras)} mensagens`
                  : "Não percorrida no período",
            }))}
          />
        ) : null}
      </section>
    </div>
  );
}
