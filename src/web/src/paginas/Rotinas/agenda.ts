/**
 * Agenda das rotinas: formulario por frequencia <-> expressao cron.
 *
 * A pessoa escolhe "Segunda a sexta, as 8h" e o backend recebe
 * "0 8 * * mon-fri". A conversao nos dois sentidos mora aqui, separada da
 * tela, porque e o trecho mais testado da gestao de rotinas (#438): a tela
 * pode mudar de visual sem que ninguem precise reler esta logica.
 *
 * Um cron que o formulario nao sabe representar vira "legada" e e
 * preservado como veio, em vez de ser reescrito sem a pessoa pedir.
 */

import type { Rotina } from "@/tipos";

export type Repeticao = "diaria" | "dias_uteis" | "semanal" | "mensal" | "dias_personalizados" | "legada";
export type DiaSemana = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

export interface FormularioRotina {
  nome: string;
  prompt: string;
  repeticao: Repeticao;
  horario: string;
  dia_semana: DiaSemana;
  dias_selecionados: DiaSemana[];
  dia_mes: string;
  agenda_legada: string;
  timezone: string;
  ativa: boolean;
}

export type ErrosDoFormulario = Partial<Record<keyof FormularioRotina, string>>;

export interface DadosRotinaApi {
  nome: string;
  prompt: string;
  agenda_cron: string;
  timezone: string;
  ativa: boolean;
}

export const DIAS_SEMANA: { valor: DiaSemana; rotulo: string; plural: string }[] = [
  { valor: "mon", rotulo: "Segunda-feira", plural: "segundas-feiras" },
  { valor: "tue", rotulo: "Terça-feira", plural: "terças-feiras" },
  { valor: "wed", rotulo: "Quarta-feira", plural: "quartas-feiras" },
  { valor: "thu", rotulo: "Quinta-feira", plural: "quintas-feiras" },
  { valor: "fri", rotulo: "Sexta-feira", plural: "sextas-feiras" },
  { valor: "sat", rotulo: "Sábado", plural: "sábados" },
  { valor: "sun", rotulo: "Domingo", plural: "domingos" },
];

export const FORMULARIO_VAZIO: FormularioRotina = {
  nome: "",
  prompt: "",
  repeticao: "dias_uteis",
  horario: "08:00",
  dia_semana: "mon",
  dias_selecionados: ["mon", "wed", "fri"],
  dia_mes: "1",
  agenda_legada: "",
  timezone: "America/Sao_Paulo",
  ativa: true,
};

export function cronDoFormulario(formulario: FormularioRotina) {
  if (formulario.repeticao === "legada") return formulario.agenda_legada.trim();
  const [hora, minuto] = formulario.horario.split(":");
  if (formulario.repeticao === "diaria") return `${Number(minuto)} ${Number(hora)} * * *`;
  if (formulario.repeticao === "dias_uteis") return `${Number(minuto)} ${Number(hora)} * * mon-fri`;
  if (formulario.repeticao === "semanal") return `${Number(minuto)} ${Number(hora)} * * ${formulario.dia_semana}`;
  if (formulario.repeticao === "dias_personalizados") return `${Number(minuto)} ${Number(hora)} * * ${formulario.dias_selecionados.join(",")}`;
  return `${Number(minuto)} ${Number(hora)} ${Number(formulario.dia_mes)} * *`;
}

export function formularioDaAgenda(cron: string): Pick<FormularioRotina, "repeticao" | "horario" | "dia_semana" | "dias_selecionados" | "dia_mes" | "agenda_legada"> {
  const legada = { repeticao: "legada" as const, horario: "08:00", dia_semana: "mon" as const, dias_selecionados: [] as DiaSemana[], dia_mes: "1", agenda_legada: cron };
  const [minuto, hora, diaMes, mes, diaSemana, ...restante] = cron.trim().split(/\s+/);
  const minutoNumero = Number(minuto);
  const horaNumero = Number(hora);
  if (restante.length || !Number.isInteger(minutoNumero) || minutoNumero < 0 || minutoNumero > 59 || !Number.isInteger(horaNumero) || horaNumero < 0 || horaNumero > 23 || mes !== "*") return legada;

  const horario = `${String(horaNumero).padStart(2, "0")}:${String(minutoNumero).padStart(2, "0")}`;
  const base = { horario, dia_semana: "mon" as DiaSemana, dias_selecionados: ["mon", "wed", "fri"] as DiaSemana[], dia_mes: "1", agenda_legada: "" };
  if (diaMes === "*" && diaSemana === "*") return { ...base, repeticao: "diaria" };
  if (diaMes === "*" && diaSemana.toLowerCase() === "mon-fri") return { ...base, repeticao: "dias_uteis" };

  const diaNome = diaSemana.toLowerCase() as DiaSemana;
  if (diaMes === "*" && DIAS_SEMANA.some((dia) => dia.valor === diaNome)) return { ...base, repeticao: "semanal", dia_semana: diaNome };

  const diasNomeados = diaSemana.toLowerCase().split(",") as DiaSemana[];
  if (diaMes === "*" && diasNomeados.length > 1 && diasNomeados.every((valor) => DIAS_SEMANA.some((dia) => dia.valor === valor))) {
    return { ...base, repeticao: "dias_personalizados", dias_selecionados: DIAS_SEMANA.filter((dia) => diasNomeados.includes(dia.valor)).map((dia) => dia.valor) };
  }

  // No APScheduler 3.x, o dia numérico zero é segunda-feira.
  const diaNumerico = Number(diaSemana);
  if (diaMes === "*" && Number.isInteger(diaNumerico) && diaNumerico >= 0 && diaNumerico <= 6) {
    return { ...base, repeticao: "semanal", dia_semana: DIAS_SEMANA[diaNumerico].valor };
  }

  const diaMesNumero = Number(diaMes);
  if (diaSemana === "*" && Number.isInteger(diaMesNumero) && diaMesNumero >= 1 && diaMesNumero <= 31) {
    return { ...base, repeticao: "mensal", dia_mes: String(diaMesNumero) };
  }
  return legada;
}

export function resumoDaAgenda(formulario: FormularioRotina) {
  if (formulario.repeticao === "diaria") return `Esta rotina será executada todos os dias, às ${formulario.horario}.`;
  if (formulario.repeticao === "dias_uteis") return `Esta rotina será executada de segunda a sexta, às ${formulario.horario}.`;
  if (formulario.repeticao === "semanal") {
    const dia = DIAS_SEMANA.find((item) => item.valor === formulario.dia_semana)?.rotulo.toLowerCase();
    return `Esta rotina será executada toda ${dia}, às ${formulario.horario}.`;
  }
  if (formulario.repeticao === "dias_personalizados") {
    const dias = DIAS_SEMANA.filter((dia) => formulario.dias_selecionados.includes(dia.valor)).map((dia) => dia.plural);
    const lista = new Intl.ListFormat("pt-BR", { style: "long", type: "conjunction" }).format(dias);
    return dias.length ? `Esta rotina será executada às ${lista}, às ${formulario.horario}.` : "Selecione pelo menos um dia da semana.";
  }
  if (formulario.repeticao === "mensal") return `Esta rotina será executada todo dia ${formulario.dia_mes} de cada mês, às ${formulario.horario}.`;
  return "Esta rotina possui um agendamento antigo. Escolha uma nova frequência para alterá-lo.";
}

export function descreverAgenda(cron: string) {
  const agenda = { ...FORMULARIO_VAZIO, ...formularioDaAgenda(cron) };
  return agenda.repeticao === "legada" ? "Agendamento antigo preservado" : resumoDaAgenda(agenda).replace("Esta rotina será executada ", "").replace(/\.$/, "");
}

export function dadosParaApi(formulario: FormularioRotina): DadosRotinaApi {
  return {
    nome: formulario.nome,
    prompt: formulario.prompt,
    agenda_cron: cronDoFormulario(formulario),
    timezone: formulario.timezone,
    ativa: formulario.ativa,
  };
}

export function formularioDaRotina(rotina: Rotina): FormularioRotina {
  return {
    nome: rotina.nome,
    prompt: rotina.prompt,
    ...formularioDaAgenda(rotina.agenda_cron),
    timezone: rotina.timezone,
    ativa: rotina.ativa,
  };
}

export function validarFormulario(formulario: FormularioRotina) {
  const erros: ErrosDoFormulario = {};
  if (formulario.nome.trim().length < 3) erros.nome = "Informe um nome com pelo menos 3 caracteres.";
  if (formulario.prompt.trim().length < 10) erros.prompt = "Descreva a ação da rotina com pelo menos 10 caracteres.";
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(formulario.horario)) erros.horario = "Informe um horário válido.";
  const diaMes = Number(formulario.dia_mes);
  if (formulario.repeticao === "mensal" && (!Number.isInteger(diaMes) || diaMes < 1 || diaMes > 31)) erros.dia_mes = "Informe um dia entre 1 e 31.";
  if (formulario.repeticao === "dias_personalizados" && !formulario.dias_selecionados.length) erros.dias_selecionados = "Selecione pelo menos um dia da semana.";
  if (!formulario.timezone.trim()) erros.timezone = "Selecione um fuso horário.";
  return erros;
}

export function formatarData(valor: string | null) {
  if (!valor) return "Sem execução agendada";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(valor));
}

/**
 * Rotulo legivel da intencao prevista. O backend manda o rotulo do
 * catalogo; sem ele (backend antigo), o id vira frase, como o proprio
 * backend faz para intencao sem rotulo. O id cru nunca aparece.
 */
export function rotuloDaIntencao(rotina: Pick<Rotina, "intencao_prevista" | "intencao_prevista_rotulo">) {
  if (rotina.intencao_prevista_rotulo) return rotina.intencao_prevista_rotulo;
  if (!rotina.intencao_prevista) return "Não classificada";
  const frase = rotina.intencao_prevista.replaceAll("_", " ");
  return frase.charAt(0).toUpperCase() + frase.slice(1);
}
