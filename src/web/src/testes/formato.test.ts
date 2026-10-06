import { describe, expect, it } from "vitest";

import { agruparPorData, formatarQuando, grupoDeData, quandoFoi } from "@/utilitarios/formato";

// Quinta-feira, 24/09/2026, 15h em Sao Paulo.
const QUINTA = new Date("2026-09-24T15:00:00-03:00");

describe("Grupos de data das listas de conversa", () => {
  it("separa hoje, ontem, esta semana e anteriores pela semana do calendario", () => {
    expect(grupoDeData("2026-09-24T09:00:00-03:00", QUINTA)).toBe("Hoje");
    expect(grupoDeData("2026-09-23T09:00:00-03:00", QUINTA)).toBe("Ontem");
    expect(grupoDeData("2026-09-22T09:00:00-03:00", QUINTA)).toBe("Esta semana");
    expect(grupoDeData("2026-09-21T09:00:00-03:00", QUINTA)).toBe("Esta semana");
    // Domingo pertence a semana anterior, mesmo estando a quatro dias.
    expect(grupoDeData("2026-09-20T09:00:00-03:00", QUINTA)).toBe("Anteriores");
  });

  it("compara o dia em Sao Paulo, e nao em UTC", () => {
    // 02h30 UTC do dia 24 ainda e 23h30 do dia 23 em Sao Paulo.
    expect(grupoDeData("2026-09-24T02:30:00Z", QUINTA)).toBe("Ontem");
    expect(quandoFoi("2026-09-24T02:30:00Z", QUINTA)).toBe("Ontem, 23:30");
  });

  it("na segunda-feira, domingo ja e ontem e sabado vai para anteriores", () => {
    const segunda = new Date("2026-09-21T10:00:00-03:00");
    expect(grupoDeData("2026-09-20T18:00:00-03:00", segunda)).toBe("Ontem");
    expect(grupoDeData("2026-09-19T18:00:00-03:00", segunda)).toBe("Anteriores");
  });

  it("agrupa na ordem fixa e sem grupo vazio", () => {
    const grupos = agruparPorData(
      [
        { id: "a", quando: "2026-09-24T10:00:00-03:00" },
        { id: "b", quando: "2026-09-10T10:00:00-03:00" },
        { id: "c", quando: "2026-09-24T08:00:00-03:00" },
      ],
      (item) => item.quando,
      QUINTA,
    );

    expect(grupos.map((grupo) => grupo.grupo)).toEqual(["Hoje", "Anteriores"]);
    expect(grupos[0].itens.map((item) => item.id)).toEqual(["a", "c"]);
  });
});

describe("Quando, na lista de rotinas", () => {
  // Terca-feira, 06/10/2026, 10h em Sao Paulo.
  const TERCA = new Date("2026-10-06T10:00:00-03:00");

  it("diz hoje, amanha e ontem pelo dia do calendario", () => {
    expect(formatarQuando("2026-10-06T08:00:00-03:00", TERCA)).toBe("hoje, 08:00");
    expect(formatarQuando("2026-10-07T00:00:00-03:00", TERCA)).toBe("amanhã, 00:00");
    expect(formatarQuando("2026-10-05T23:00:00-03:00", TERCA)).toBe("ontem, 23:00");
  });

  it("usa o dia da semana, sem -feira, nos proximos dias", () => {
    expect(formatarQuando("2026-10-08T09:00:00-03:00", TERCA)).toBe("quinta, 09:00");
    expect(formatarQuando("2026-10-12T09:00:00-03:00", TERCA)).toBe("segunda, 09:00");
  });

  it("usa a data curta alem da semana e no passado", () => {
    expect(formatarQuando("2026-10-13T09:00:00-03:00", TERCA)).toBe("13 de out., 09:00");
    expect(formatarQuando("2026-10-02T17:00:00-03:00", TERCA)).toBe("2 de out., 17:00");
  });

  it("mostra o ano so quando nao e o corrente", () => {
    expect(formatarQuando("2027-01-05T17:00:00-03:00", TERCA)).toBe("5 de jan. de 2027, 17:00");
  });

  it("compara o dia e o ano em Sao Paulo, e nao em UTC", () => {
    // 02h30 UTC do dia 7 ainda e 23h30 do dia 6 em Sao Paulo.
    expect(formatarQuando("2026-10-07T02:30:00Z", TERCA)).toBe("hoje, 23:30");
    // 01h UTC de 1/1/2027 ainda e 31/12/2026 em Sao Paulo: sem ano.
    expect(formatarQuando("2027-01-01T01:00:00Z", TERCA)).toBe("31 de dez., 22:00");
  });
});
