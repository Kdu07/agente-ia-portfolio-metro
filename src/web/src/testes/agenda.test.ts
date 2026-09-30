/**
 * Testes unitários das funções de agenda.ts.
 *
 * Cobrem a conversão entre formulário e cron, validação e formatação.
 */

import { describe, expect, it } from "vitest";

import {
  cronDoFormulario,
  dadosParaApi,
  descreverAgenda,
  formularioDaAgenda,
  formularioDaRotina,
  formatarData,
  FORMULARIO_VAZIO,
  resumoDaAgenda,
  rotuloDaIntencao,
  validarFormulario,
  type DiaSemana,
  type FormularioRotina,
} from "@/paginas/Rotinas/agenda";
import type { Rotina } from "@/tipos";

describe("cronDoFormulario", () => {
  it("gera cron para repetição diária", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "diaria" as const,
      horario: "08:30",
    };
    expect(cronDoFormulario(formulario)).toBe("30 8 * * *");
  });

  it("gera cron para dias úteis", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "dias_uteis" as const,
      horario: "09:00",
    };
    expect(cronDoFormulario(formulario)).toBe("0 9 * * mon-fri");
  });

  it("gera cron para repetição semanal", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "semanal" as const,
      horario: "10:00",
      dia_semana: "wed" as const,
    };
    expect(cronDoFormulario(formulario)).toBe("0 10 * * wed");
  });

  it("gera cron para dias personalizados", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "dias_personalizados" as const,
      horario: "14:00",
      dias_selecionados: ["mon", "wed", "fri"] as DiaSemana[],
    };
    expect(cronDoFormulario(formulario)).toBe("0 14 * * mon,wed,fri");
  });

  it("gera cron para repetição mensal", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "mensal" as const,
      horario: "08:00",
      dia_mes: "15",
    };
    expect(cronDoFormulario(formulario)).toBe("0 8 15 * *");
  });

  it("preserva cron legado quando repetição é legada", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "legada" as const,
      agenda_legada: "0 8 * * mon-fri",
    };
    expect(cronDoFormulario(formulario)).toBe("0 8 * * mon-fri");
  });

  it("trata horário limite 00:00", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "diaria" as const,
      horario: "00:00",
    };
    expect(cronDoFormulario(formulario)).toBe("0 0 * * *");
  });

  it("trata horário limite 23:59", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "diaria" as const,
      horario: "23:59",
    };
    expect(cronDoFormulario(formulario)).toBe("59 23 * * *");
  });
});

describe("formularioDaAgenda", () => {
  it("interpreta cron diário", () => {
    const resultado = formularioDaAgenda("0 8 * * *");
    expect(resultado).toEqual({
      horario: "08:00",
      repeticao: "diaria",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("interpreta cron de dias úteis", () => {
    const resultado = formularioDaAgenda("0 9 * * mon-fri");
    expect(resultado).toEqual({
      horario: "09:00",
      repeticao: "dias_uteis",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("interpreta cron semanal", () => {
    const resultado = formularioDaAgenda("30 10 * * wed");
    expect(resultado).toEqual({
      horario: "10:30",
      repeticao: "semanal",
      dia_semana: "wed",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("interpreta cron de dias personalizados", () => {
    const resultado = formularioDaAgenda("0 14 * * mon,wed,fri");
    expect(resultado).toEqual({
      horario: "14:00",
      repeticao: "dias_personalizados",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"] as DiaSemana[],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("interpreta cron mensal", () => {
    const resultado = formularioDaAgenda("0 8 15 * *");
    expect(resultado).toEqual({
      horario: "08:00",
      repeticao: "mensal",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "15",
      agenda_legada: "",
    });
  });

  it("retorna legada para cron não reconhecido", () => {
    const resultado = formularioDaAgenda("0 8 1 1 *");
    expect(resultado.repeticao).toBe("legada");
    expect(resultado.agenda_legada).toBe("0 8 1 1 *");
  });

  it("retorna legada para cron com campos extras", () => {
    const resultado = formularioDaAgenda("0 8 * * mon-fri some_extra_field");
    expect(resultado.repeticao).toBe("legada");
  });

  it("retorna legada para minuto inválido", () => {
    const resultado = formularioDaAgenda("60 8 * * *");
    expect(resultado.repeticao).toBe("legada");
  });

  it("retorna legada para hora inválida", () => {
    const resultado = formularioDaAgenda("0 24 * * *");
    expect(resultado.repeticao).toBe("legada");
  });

  it("interpreta dia numérico (APScheduler 3.x)", () => {
    const resultado = formularioDaAgenda("0 8 * * 0");
    expect(resultado).toEqual({
      horario: "08:00",
      repeticao: "semanal",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("trata dia do mês limite 1", () => {
    const resultado = formularioDaAgenda("0 8 1 * *");
    expect(resultado).toEqual({
      horario: "08:00",
      repeticao: "mensal",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "1",
      agenda_legada: "",
    });
  });

  it("trata dia do mês limite 31", () => {
    const resultado = formularioDaAgenda("0 8 31 * *");
    expect(resultado).toEqual({
      horario: "08:00",
      repeticao: "mensal",
      dia_semana: "mon",
      dias_selecionados: ["mon", "wed", "fri"],
      dia_mes: "31",
      agenda_legada: "",
    });
  });
});

describe("resumoDaAgenda", () => {
  it("descreve agenda diária", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "diaria" as const,
      horario: "08:00",
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina será executada todos os dias, às 08:00.");
  });

  it("descreve agenda de dias úteis", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "dias_uteis" as const,
      horario: "09:00",
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina será executada de segunda a sexta, às 09:00.");
  });

  it("descreve agenda semanal", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      repeticao: "semanal" as const,
      horario: "10:00",
      dia_semana: "wed" as const,
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina será executada toda quarta-feira, às 10:00.");
  });

  it("descreve agenda de dias personalizados", () => {
    const formulario: FormularioRotina = {
      ...FORMULARIO_VAZIO,
      repeticao: "dias_personalizados" as const,
      horario: "14:00",
      dias_selecionados: ["mon", "wed", "fri"] as DiaSemana[],
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina será executada às segundas-feiras, quartas-feiras e sextas-feiras, às 14:00.");
  });

  it("descreve agenda mensal", () => {
    const formulario: FormularioRotina = {
      ...FORMULARIO_VAZIO,
      repeticao: "mensal" as const,
      horario: "08:00",
      dia_mes: "15",
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina será executada todo dia 15 de cada mês, às 08:00.");
  });

  it("descreve agenda legada", () => {
    const formulario: FormularioRotina = {
      ...FORMULARIO_VAZIO,
      repeticao: "legada" as const,
      agenda_legada: "0 8 * * mon-fri",
    };
    expect(resumoDaAgenda(formulario)).toBe("Esta rotina possui um agendamento antigo. Escolha uma nova frequência para alterá-lo.");
  });

  it("pede seleção de dias quando nenhum dia selecionado", () => {
    const formulario: FormularioRotina = {
      ...FORMULARIO_VAZIO,
      repeticao: "dias_personalizados" as const,
      horario: "14:00",
      dias_selecionados: [] as DiaSemana[],
    };
    expect(resumoDaAgenda(formulario)).toBe("Selecione pelo menos um dia da semana.");
  });
});

describe("descreverAgenda", () => {
  it("descreve cron diário", () => {
    expect(descreverAgenda("0 8 * * *")).toBe("todos os dias, às 08:00");
  });

  it("descreve cron de dias úteis", () => {
    expect(descreverAgenda("0 9 * * mon-fri")).toBe("de segunda a sexta, às 09:00");
  });

  it("descreve cron legado", () => {
    expect(descreverAgenda("algum_cron_legado")).toBe("Agendamento antigo preservado");
  });
});

describe("validarFormulario", () => {
  it("valida formulário vazio", () => {
    const erros = validarFormulario(FORMULARIO_VAZIO);
    expect(erros.nome).toBe("Informe um nome com pelo menos 3 caracteres.");
    expect(erros.prompt).toBe("Descreva a ação da rotina com pelo menos 10 caracteres.");
  });

  it("valida nome curto", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, nome: "ab" };
    const erros = validarFormulario(formulario);
    expect(erros.nome).toBe("Informe um nome com pelo menos 3 caracteres.");
  });

  it("valida nome válido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, nome: "Nome válido" };
    const erros = validarFormulario(formulario);
    expect(erros.nome).toBeUndefined();
  });

  it("valida prompt curto", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, prompt: "curto" };
    const erros = validarFormulario(formulario);
    expect(erros.prompt).toBe("Descreva a ação da rotina com pelo menos 10 caracteres.");
  });

  it("valida prompt válido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, prompt: "Descrição suficientemente longa" };
    const erros = validarFormulario(formulario);
    expect(erros.prompt).toBeUndefined();
  });

  it("valida horário inválido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, horario: "25:00" };
    const erros = validarFormulario(formulario);
    expect(erros.horario).toBe("Informe um horário válido.");
  });

  it("valida horário válido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, horario: "08:30" };
    const erros = validarFormulario(formulario);
    expect(erros.horario).toBeUndefined();
  });

  it("valida horário limite 00:00", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, horario: "00:00" };
    const erros = validarFormulario(formulario);
    expect(erros.horario).toBeUndefined();
  });

  it("valida horário limite 23:59", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, horario: "23:59" };
    const erros = validarFormulario(formulario);
    expect(erros.horario).toBeUndefined();
  });

  it("valida dia do mês fora do intervalo", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, repeticao: "mensal" as const, dia_mes: "32" };
    const erros = validarFormulario(formulario);
    expect(erros.dia_mes).toBe("Informe um dia entre 1 e 31.");
  });

  it("valida dia do mês válido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, repeticao: "mensal" as const, dia_mes: "15" };
    const erros = validarFormulario(formulario);
    expect(erros.dia_mes).toBeUndefined();
  });

  it("valida dia do mês limite 1", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, repeticao: "mensal" as const, dia_mes: "1" };
    const erros = validarFormulario(formulario);
    expect(erros.dia_mes).toBeUndefined();
  });

  it("valida dia do mês limite 31", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, repeticao: "mensal" as const, dia_mes: "31" };
    const erros = validarFormulario(formulario);
    expect(erros.dia_mes).toBeUndefined();
  });

  it("valida dias personalizados vazios", () => {
    const formulario = { ...FORMULARIO_VAZIO, repeticao: "dias_personalizados" as const, dias_selecionados: [] as DiaSemana[] };
    const erros = validarFormulario(formulario);
    expect(erros.dias_selecionados).toBe("Selecione pelo menos um dia da semana.");
  });

  it("valida dias personalizados com seleção", () => {
    const formulario = { ...FORMULARIO_VAZIO, repeticao: "dias_personalizados" as const, dias_selecionados: ["mon"] as DiaSemana[] };
    const erros = validarFormulario(formulario);
    expect(erros.dias_selecionados).toBeUndefined();
  });

  it("valida timezone vazio", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, timezone: "" };
    const erros = validarFormulario(formulario);
    expect(erros.timezone).toBe("Selecione um fuso horário.");
  });

  it("valida timezone preenchido", () => {
    const formulario: FormularioRotina = { ...FORMULARIO_VAZIO, timezone: "America/Sao_Paulo" };
    const erros = validarFormulario(formulario);
    expect(erros.timezone).toBeUndefined();
  });

  it("retorna sem erros para formulário válido", () => {
    const formulario: FormularioRotina = {
      ...FORMULARIO_VAZIO,
      nome: "Nome válido",
      prompt: "Descrição suficientemente longa",
      horario: "08:00",
      timezone: "America/Sao_Paulo",
    };
    const erros = validarFormulario(formulario);
    expect(Object.keys(erros)).toHaveLength(0);
  });
});

describe("dadosParaApi", () => {
  it("converte formulário para formato da API", () => {
    const formulario = {
      ...FORMULARIO_VAZIO,
      nome: "Teste",
      prompt: "Descrição",
      repeticao: "diaria" as const,
      horario: "08:00",
      timezone: "America/Sao_Paulo",
      ativa: true,
    };
    const dados = dadosParaApi(formulario);
    expect(dados).toEqual({
      nome: "Teste",
      prompt: "Descrição",
      agenda_cron: "0 8 * * *",
      timezone: "America/Sao_Paulo",
      ativa: true,
    });
  });
});

describe("formularioDaRotina", () => {
  it("converte rotina para formulário", () => {
    const rotina: Rotina = {
      id: "1",
      nome: "Rotina teste",
      prompt: "Descrição",
      agenda_cron: "0 8 * * mon-fri",
      timezone: "America/Sao_Paulo",
      ativa: true,
      proximo_disparo: "2024-01-01T08:00:00",
      atualizada_em: "2024-01-01T00:00:00",
      criada_em: "2024-01-01T00:00:00",
      intencao_prevista: "consultar_status",
    };
    const formulario = formularioDaRotina(rotina);
    expect(formulario.nome).toBe("Rotina teste");
    expect(formulario.prompt).toBe("Descrição");
    expect(formulario.repeticao).toBe("dias_uteis");
    expect(formulario.timezone).toBe("America/Sao_Paulo");
    expect(formulario.ativa).toBe(true);
  });
});

describe("formatarData", () => {
  it("formata data válida", () => {
    const data = "2024-01-15T14:30:00";
    const resultado = formatarData(data);
    expect(resultado).toMatch(/15 de jan/);
    expect(resultado).toMatch(/14:30/);
  });

  it("retorna mensagem quando data é null", () => {
    const resultado = formatarData(null);
    expect(resultado).toBe("Sem execução agendada");
  });
});

describe("rotuloDaIntencao", () => {
  it("retorna rótulo quando disponível", () => {
    const rotina: Pick<Rotina, "intencao_prevista" | "intencao_prevista_rotulo"> = {
      intencao_prevista: "consultar_status",
      intencao_prevista_rotulo: "Consultar status",
    };
    expect(rotuloDaIntencao(rotina)).toBe("Consultar status");
  });

  it("formata id quando não há rótulo", () => {
    const rotina: Pick<Rotina, "intencao_prevista" | "intencao_prevista_rotulo"> = {
      intencao_prevista: "consultar_marcos_atrasados",
      intencao_prevista_rotulo: undefined,
    };
    expect(rotuloDaIntencao(rotina)).toBe("Consultar marcos atrasados");
  });

  it("retorna Não classificada quando não há intenção", () => {
    const rotina: Pick<Rotina, "intencao_prevista" | "intencao_prevista_rotulo"> = {
      intencao_prevista: null,
      intencao_prevista_rotulo: undefined,
    };
    expect(rotuloDaIntencao(rotina)).toBe("Não classificada");
  });

  it("capitaliza primeira letra do id formatado", () => {
    const rotina: Pick<Rotina, "intencao_prevista" | "intencao_prevista_rotulo"> = {
      intencao_prevista: "alguma_intencao",
      intencao_prevista_rotulo: undefined,
    };
    expect(rotuloDaIntencao(rotina)).toBe("Alguma intencao");
  });
});
