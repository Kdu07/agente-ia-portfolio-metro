/**
 * Formatacao dos numeros e datas exibidos no painel.
 *
 * Centralizada para que o cartao, o grafico e a tabela escrevam o mesmo
 * valor do mesmo jeito: "3,9%" num lugar e "0.039" noutro faz quem le
 * duvidar de que se trata do mesmo numero.
 */

const INTEIRO = new Intl.NumberFormat("pt-BR");
const PERCENTUAL = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const DATA_HORA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatarInteiro(valor: number): string {
  return INTEIRO.format(valor);
}

/** Proporcao entre 0 e 1 como percentual com uma casa: 0.039 vira "3,9%". */
export function formatarPercentual(proporcao: number): string {
  return PERCENTUAL.format(proporcao);
}

/** Milissegundos com a unidade mais legivel: "850 ms" ou "2,9 s". */
export function formatarDuracao(ms: number): string {
  if (ms < 1000) return `${formatarInteiro(Math.round(ms))} ms`;
  return `${(ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`;
}

/**
 * Dia de um ponto da serie, como "20/09".
 *
 * Le a data direto do texto, sem passar por `new Date`. O backend manda o
 * inicio do dia no fuso de Sao Paulo ("2026-09-20T00:00:00-03:00") e o
 * duble manda so a data ("2026-09-20"); convertida para `Date`, a segunda
 * forma vira meia-noite UTC e, lida em Sao Paulo, cairia no dia anterior.
 */
export function formatarDia(momento: string): string {
  const [ano, mes, dia] = momento.slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}` : momento;
}

export function formatarDataHora(momento: string): string {
  return DATA_HORA.format(new Date(momento));
}
