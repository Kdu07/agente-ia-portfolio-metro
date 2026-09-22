/**
 * Contratos da API, espelhando app/schemas/ do middleware.
 *
 * Mantidos à mão de propósito enquanto o esquema se move: gerar a partir
 * do OpenAPI é o passo certo quando as ondas 4 e 5 estabilizarem, mas
 * hoje a geração acopla o build do frontend a uma API que ainda muda
 * várias vezes por semana.
 *
 * Ao alterar um schema no backend, alterar aqui na mesma mudança.
 */

export type Perfil = "diretoria" | "lider_projeto" | "membro_equipe";

export type Permissao = "ver_intencoes" | "gerir_rotinas";

export type Canal = "chat" | "voz" | "rotina";

/** Periodos do painel de intencoes, como `Janela` em app/analytics/metricas.py. */
export type Janela = "7d" | "30d" | "90d";

/**
 * Vocabulário fechado de app/pipeline/desfechos.py. O frontend usa isto
 * para colorir a bolha e explicar o que aconteceu — nunca para decidir
 * acesso.
 */
export type Desfecho =
  | "encaminhada"
  | "bloqueada_injecao_regra"
  | "bloqueada_injecao_modelo"
  | "bloqueada_abuso"
  | "recusada_fora_escopo"
  | "recusada_baixa_confianca"
  | "bloqueada_saida"
  | "falha_executor";

export interface Usuario {
  id: string;
  nome: string;
  email: string | null;
  perfil: Perfil;
  /**
   * Usado apenas para decidir quais abas exibir. Não é controle de
   * acesso: quem barra é o backend, em cada rota. Esconder o menu é
   * conveniência de navegação.
   */
  permissoes: Permissao[];
}

export interface ChatRequest {
  mensagem: string;
  conversa_id?: string | null;
  canal?: Canal;
}

export interface ChatResponse {
  resposta: string;
  conversa_id: string;
  intencao_id: string | null;
  desfecho: Desfecho;
  bloqueada: boolean;
}

export interface ConversaResumo {
  id: string;
  titulo: string | null;
  criada_em: string;
  atualizada_em: string;
  total_turnos: number;
}

export interface Turno {
  id: string;
  prompt: string;
  resposta: string;
  canal: Canal;
  intencao_id: string | null;
  desfecho: Desfecho;
  bloqueada: boolean;
  criada_em: string;
}

export interface ConversaDetalhe {
  id: string;
  titulo: string | null;
  criada_em: string;
  turnos: Turno[];
}

/** Retorno de POST /rotinas/validar. */
export interface ValidacaoRotina {
  valida: boolean;
  intencao_prevista: string | null;
  erro: string | null;
}

export type StatusExecucao = "em_execucao" | "sucesso" | "bloqueada" | "falha";

export interface Rotina {
  id: string;
  nome: string;
  prompt: string;
  agenda_cron: string;
  timezone: string;
  ativa: boolean;
  intencao_prevista: string | null;
  proximo_disparo: string | null;
  criada_em: string;
  atualizada_em: string;
}

export interface Execucao {
  id: string;
  rotina_id: string;
  iniciada_em: string;
  concluida_em: string | null;
  status: StatusExecucao;
  resposta: string | null;
  desfecho: Desfecho | null;
  erro: string | null;
}

export interface Contagem {
  chave: string;
  rotulo: string;
  total: number;
}

export interface PontoSerie {
  momento: string;
  total: number;
}

export interface Serie {
  nome: string;
  pontos: PontoSerie[];
}

export interface EnunciadoAgrupado {
  prompt: string;
  ocorrencias: number;
  ultima_em: string;
  confianca_media: number;
}

export interface ResumoSeguranca {
  total_mensagens: number;
  bloqueios_injecao: number;
  bloqueios_abuso: number;
  bloqueios_saida: number;
  taxa_de_bloqueio: number;
}

/** Percentis de uma etapa do pipeline, em milissegundos. */
export interface LatenciaEtapa {
  etapa: string;
  p50: number;
  p95: number;
  /** Zero indica etapa nao percorrida na janela, e nao etapa instantanea. */
  amostras: number;
}

/** Percentis de latencia do pipeline, em milissegundos. */
export interface Latencia {
  p50: number;
  p95: number;
  etapas: LatenciaEtapa[];
}

export interface ResumoCatalogo {
  intencoes_acionadas: number;
  intencoes_sem_uso: number;
  enunciados_fora_de_escopo: number;
  enunciados_baixa_confianca: number;
}

export interface TokenVoz {
  token: string;
  regiao: string;
  expira_em_segundos: number;
  idioma: string;
}
