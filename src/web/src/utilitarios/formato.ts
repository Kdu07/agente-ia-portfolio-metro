/**
 * Formatacao de data e hora para exibicao.
 *
 * Tudo em `America/Sao_Paulo` e locale pt-BR: o backend envia ISO 8601
 * com fuso, e deixar o navegador decidir faria a mesma interacao
 * aparecer com horarios diferentes para pessoas em maquinas configuradas
 * de forma distinta.
 */

const FUSO = "America/Sao_Paulo";

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

/**
 * Rotulo relativo para listas de historico. Trocar "08 set, 14:32" por
 * "Hoje" no caso recente e o que permite bater o olho e localizar a
 * conversa sem ler a data inteira.
 */
export function quandoFoi(iso: string): string {
  const momento = new Date(iso);
  const agora = new Date();
  const umDia = 86_400_000;
  const diferenca = agora.getTime() - momento.getTime();

  if (diferenca < umDia && agora.getDate() === momento.getDate()) {
    return `Hoje, ${horaCurta(iso)}`;
  }
  if (diferenca < 2 * umDia) return `Ontem, ${horaCurta(iso)}`;
  return `${dataCurta(iso)}, ${horaCurta(iso)}`;
}
