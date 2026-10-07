/**
 * Formatacao de data e hora para exibicao.
 *
 * Tudo em `America/Sao_Paulo` e locale pt-BR: o backend envia ISO 8601
 * com fuso, e deixar o navegador decidir faria a mesma interacao
 * aparecer com horarios diferentes para pessoas em maquinas configuradas
 * de forma distinta.
 */

export const FUSO = "America/Sao_Paulo";
const UM_DIA = 86_400_000;

export function horaCurta(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: FUSO,
  }).format(new Date(iso));
}

export function dataCurta(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    timeZone: FUSO,
  }).format(new Date(iso));
}

// O dia do calendario em Sao Paulo, como meia-noite UTC. Comparar dias
// assim, e nao pelo relogio da maquina, evita que uma conversa das 23h
// caia em "Ontem" para quem esta com o fuso configurado em UTC.
function diaEmSaoPaulo(momento: Date): number {
  const [ano, mes, dia] = new Intl.DateTimeFormat("en-CA", { timeZone: FUSO })
    .format(momento)
    .split("-")
    .map(Number);
  return Date.UTC(ano, mes - 1, dia);
}

function diasAtras(iso: string, agora: Date): number {
  return Math.round((diaEmSaoPaulo(agora) - diaEmSaoPaulo(new Date(iso))) / UM_DIA);
}

/**
 * Rotulo relativo para listas de historico. Trocar "08 set, 14:32" por
 * "Hoje" no caso recente e o que permite bater o olho e localizar a
 * conversa sem ler a data inteira.
 */
export function quandoFoi(iso: string, agora = new Date()): string {
  const dias = diasAtras(iso, agora);
  if (dias <= 0) return `Hoje, ${horaCurta(iso)}`;
  if (dias === 1) return `Ontem, ${horaCurta(iso)}`;
  return `${dataCurta(iso)}, ${horaCurta(iso)}`;
}

/**
 * Quando, em linguagem de agenda, para o passado e o futuro: "hoje, 08:00",
 * "amanhã, 08:00", "ontem, 23:00", "quinta, 09:00" nos dias seguintes da
 * semana e "5 de nov., 17:00" alem disso, com o ano so quando nao e o
 * corrente. Na lista de rotinas, quem le quer saber quando, e nao decifrar
 * "07 de out. de 2026". Conta dias do calendario em Sao Paulo, como
 * `quandoFoi`: 23h59 de hoje e 0h01 de amanha sao dias diferentes.
 */
export function formatarQuando(iso: string, agora = new Date()): string {
  const hora = horaCurta(iso);
  const dias = -diasAtras(iso, agora);
  if (dias === 0) return `hoje, ${hora}`;
  if (dias === 1) return `amanhã, ${hora}`;
  if (dias === -1) return `ontem, ${hora}`;
  const data = new Date(iso);
  if (dias > 1 && dias < 7) {
    const semana = new Intl.DateTimeFormat("pt-BR", { weekday: "long", timeZone: FUSO }).format(data).replace("-feira", "");
    return `${semana}, ${hora}`;
  }
  const outroAno = new Date(diaEmSaoPaulo(data)).getUTCFullYear() !== new Date(diaEmSaoPaulo(agora)).getUTCFullYear();
  const dia = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "short",
    timeZone: FUSO,
    ...(outroAno ? { year: "numeric" as const } : {}),
  }).format(data);
  return `${dia}, ${hora}`;
}

export type GrupoDeData = "Hoje" | "Ontem" | "Esta semana" | "Anteriores";

/** Ordem em que os grupos aparecem nas listas, do mais recente ao mais antigo. */
export const GRUPOS_DE_DATA: GrupoDeData[] = ["Hoje", "Ontem", "Esta semana", "Anteriores"];

/**
 * Grupo de uma data nas listas de conversa. "Esta semana" e a semana do
 * calendario, de segunda-feira ate anteontem: um rotulo que diz "semana"
 * e junta sete dias corridos faria a conversa de domingo passado aparecer
 * como desta semana.
 */
export function grupoDeData(iso: string, agora = new Date()): GrupoDeData {
  const dias = diasAtras(iso, agora);
  if (dias <= 0) return "Hoje";
  if (dias === 1) return "Ontem";
  const diasDesdeSegunda = (new Date(diaEmSaoPaulo(agora)).getUTCDay() + 6) % 7;
  return dias <= diasDesdeSegunda ? "Esta semana" : "Anteriores";
}

/** Separa uma lista ja ordenada nos grupos de data, sem grupo vazio. */
export function agruparPorData<T>(itens: T[], dataDe: (item: T) => string, agora = new Date()) {
  const grupos = new Map<GrupoDeData, T[]>();
  for (const item of itens) {
    const grupo = grupoDeData(dataDe(item), agora);
    grupos.set(grupo, [...(grupos.get(grupo) ?? []), item]);
  }
  return GRUPOS_DE_DATA.filter((grupo) => grupos.has(grupo)).map((grupo) => ({
    grupo,
    itens: grupos.get(grupo)!,
  }));
}
