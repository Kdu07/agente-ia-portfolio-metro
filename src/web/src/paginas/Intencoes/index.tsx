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
 *
 * Tudo pinta pelos tokens do tema, e o painel funciona no claro e no
 * escuro: antes os cartoes eram brancos e os graficos, hexadecimais do
 * tema claro.
 */

import { type ReactNode, useState } from "react";

import {
  BarrasPorIntencao,
  CartaoResumo,
  DistribuicaoDesfechos,
  SerieBloqueios,
  TabelaEnunciados,
  TempoPorEtapa,
} from "@/componentes/graficos";
import { ESTILO_DA_ETAPA, ESTILO_DA_GUARDA } from "@/componentes/graficos/cores";
import { formatarDuracao, formatarInteiro, formatarPercentual } from "@/componentes/graficos/formatos";
import { Button } from "@/componentes/ui/button";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import { CampoSelecao } from "@/componentes/ui/CampoSelecao";
import { EstadoVazio } from "@/componentes/ui/EstadoVazio";
import { IconeAviso, IconeIntencoes } from "@/componentes/ui/icones";
import { Skeleton } from "@/componentes/ui/skeleton";
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

export function Intencoes() {
  const [janela, setJanela] = useState<Janela>("30d");
  const [perfil, setPerfil] = useState<FiltroPerfil>("todos");
  const painel = usePainelIntencoes(janela, perfil);
  const descricaoJanela = JANELAS.find((opcao) => opcao.valor === janela)?.descricao ?? "";

  let conteudo: ReactNode;
  if (painel.erro) {
    conteudo = (
      <div role="alert" className="grid max-w-135 justify-items-start gap-2 rounded-xl border border-destructive/40 bg-card p-6">
        <span className="mb-1 grid size-10.5 place-items-center rounded-[12px] bg-destructive/10 text-destructive">
          <IconeAviso aria-hidden="true" />
        </span>
        <h2 className="text-base font-semibold">Não foi possível carregar o painel</h2>
        <p className="text-sm text-muted-foreground">{painel.erro}</p>
        <Button type="button" variant="outline" className="mt-2" onClick={painel.tentarNovamente}>
          Tentar novamente
        </Button>
      </div>
    );
  } else if (painel.carregando || !painel.dados) {
    conteudo = (
      <div role="status" aria-live="polite" className="grid gap-3">
        <span className="sr-only">Carregando o painel de intenções</span>
        <Skeleton className="h-6 w-32 bg-muted" aria-hidden="true" />
        <Skeleton className="h-22 rounded-xl bg-muted" aria-hidden="true" />
        <div className="grid gap-3 lg:grid-cols-2" aria-hidden="true">
          <Skeleton className="h-72 rounded-xl bg-muted" />
          <Skeleton className="h-72 rounded-xl bg-muted" />
        </div>
      </div>
    );
  } else if (painel.dados.resumoSeguranca.total_mensagens === 0) {
    conteudo = (
      <EstadoVazio
        icone={IconeIntencoes}
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
    <div className="flex h-full min-h-0 flex-col">
      <CabecalhoPagina titulo="Intenções" />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-295 px-3.5 pt-6 pb-10 md:px-6">
          <h1 className="font-display text-[26px]">Análise de intenções</h1>
          <p className="mt-1 text-muted-foreground">Segurança, evolução do catálogo e desempenho do pipeline.</p>

          <section aria-label="Filtros do painel" className="mt-4.5 mb-6 flex flex-wrap gap-3">
            <div className="grid min-w-44 gap-1.5">
              <label htmlFor="filtro-periodo" className="text-[13px] font-[550] text-foreground">
                Período
              </label>
              <CampoSelecao id="filtro-periodo" value={janela} onChange={(evento) => setJanela(evento.target.value as Janela)}>
                {JANELAS.map((opcao) => (
                  <option key={opcao.valor} value={opcao.valor}>
                    {opcao.rotulo}
                  </option>
                ))}
              </CampoSelecao>
            </div>
            <div className="grid min-w-44 gap-1.5">
              <label htmlFor="filtro-perfil" className="text-[13px] font-[550] text-foreground">
                Perfil
              </label>
              <CampoSelecao
                id="filtro-perfil"
                value={perfil}
                onChange={(evento) => setPerfil(evento.target.value as FiltroPerfil)}
              >
                {PERFIS.map((opcao) => (
                  <option key={opcao.valor} value={opcao.valor}>
                    {opcao.rotulo}
                  </option>
                ))}
              </CampoSelecao>
            </div>
          </section>

          {conteudo}
        </div>
      </div>
    </div>
  );
}

function TituloDeSecao({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="text-[17px] font-[650] tracking-[-0.012em] text-foreground font-stretch-116%">
      {children}
    </h2>
  );
}

function Recortes({ dados }: { dados: DadosPainel }) {
  const seguranca = dados.resumoSeguranca;
  const catalogo = dados.resumoCatalogo;
  const etapa = (nome: string) => dados.latencia.etapas.find((item) => item.etapa === nome);
  const executor = etapa("executor");
  const injecao = etapa("injecao");

  return (
    <div className="grid gap-8">
      <section aria-labelledby="recorte-seguranca" className="grid gap-3">
        <TituloDeSecao id="recorte-seguranca">Segurança</TituloDeSecao>
        <CartaoResumo
          titulo="Resumo de segurança"
          itens={[
            {
              rotulo: "Mensagens",
              valor: formatarInteiro(seguranca.total_mensagens),
              detalhe: `${formatarPercentual(seguranca.taxa_de_bloqueio)} bloqueadas`,
            },
            {
              rotulo: "Bloqueios por injeção",
              valor: formatarInteiro(seguranca.bloqueios_injecao),
              amostra: { cor: ESTILO_DA_GUARDA.injecao.cor, traco: ESTILO_DA_GUARDA.injecao.traco },
            },
            {
              rotulo: "Bloqueios por uso indevido",
              valor: formatarInteiro(seguranca.bloqueios_abuso),
              amostra: { cor: ESTILO_DA_GUARDA.abuso.cor, traco: ESTILO_DA_GUARDA.abuso.traco },
            },
            {
              rotulo: "Respostas retidas na saída",
              valor: formatarInteiro(seguranca.bloqueios_saida),
              amostra: { cor: ESTILO_DA_GUARDA.saida.cor, traco: ESTILO_DA_GUARDA.saida.traco },
            },
          ]}
        />
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <SerieBloqueios series={dados.serie} />
          <DistribuicaoDesfechos dados={dados.desfechos} />
        </div>
      </section>

      <section aria-labelledby="recorte-catalogo" className="grid gap-3">
        <TituloDeSecao id="recorte-catalogo">Evolução do catálogo</TituloDeSecao>
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
        <div className="grid gap-3 lg:grid-cols-2">
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

      <section aria-labelledby="recorte-desempenho" className="grid gap-3">
        <TituloDeSecao id="recorte-desempenho">Desempenho</TituloDeSecao>
        <CartaoResumo
          titulo="Latência do pipeline"
          itens={[
            { rotulo: "Mediana (p50)", valor: formatarDuracao(dados.latencia.p50) },
            { rotulo: "95º percentil (p95)", valor: formatarDuracao(dados.latencia.p95) },
            ...(executor && executor.amostras > 0
              ? [{ rotulo: "Executor, p95", valor: formatarDuracao(executor.p95), amostra: { cor: ESTILO_DA_ETAPA.executor.cor } }]
              : []),
            ...(injecao && injecao.amostras > 0
              ? [{ rotulo: "Guarda de injeção, p95", valor: formatarDuracao(injecao.p95), amostra: { cor: ESTILO_DA_ETAPA.injecao.cor } }]
              : []),
          ]}
        />
        {dados.latencia.etapas.length > 0 ? (
          // A etiqueta da região continua a mesma do cartão de p95 que esta
          // barra substituiu; a tabela acessível traz o p95 de cada etapa.
          <section aria-label="Latência por etapa (p95)">
            <TempoPorEtapa etapas={dados.latencia.etapas} />
          </section>
        ) : null}
      </section>
    </div>
  );
}
