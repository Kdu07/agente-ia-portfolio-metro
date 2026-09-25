/**
 * Criação e edição de uma rotina, num diálogo (gaveta no celular).
 *
 * Os campos, os rótulos com "*" e as validações são os de sempre; a agenda
 * continua sendo escolhida por frequência, horário e fuso, e a conversão
 * para cron fica em `agenda.ts`. Repetir, Fuso e Dia da semana seguem como
 * `<select>` nativo, e os dias personalizados como caixas de seleção de
 * verdade, só com a aparência de botão.
 */

import { type FormEvent, useState } from "react";

import { Button } from "@/componentes/ui/button";
import { CampoSelecao } from "@/componentes/ui/CampoSelecao";
import { DialogoResponsivo } from "@/componentes/ui/DialogoResponsivo";
import { IconeAviso, IconeRelogio } from "@/componentes/ui/icones";
import { Input } from "@/componentes/ui/input";
import { Switch } from "@/componentes/ui/switch";
import { cn } from "@/utilitarios/cn";
import {
  DIAS_SEMANA,
  type DiaSemana,
  type ErrosDoFormulario,
  type FormularioRotina as Formulario,
  type Repeticao,
  resumoDaAgenda,
  validarFormulario,
} from "./agenda";

interface Props {
  aberto: boolean;
  modo: "criar" | "editar";
  inicial: Formulario;
  salvando: boolean;
  erro: string;
  onFechar: () => void;
  onSalvar: (formulario: Formulario) => void;
}

const ROTULO = "text-[13px] font-[550] text-foreground";
const ERRO = "text-xs font-medium text-destructive";

export function FormularioRotina({ aberto, modo, inicial, salvando, erro, onFechar, onSalvar }: Props) {
  const [formulario, setFormulario] = useState(inicial);
  const [erros, setErros] = useState<ErrosDoFormulario>({});

  function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novosErros = validarFormulario(formulario);
    setErros(novosErros);
    if (Object.keys(novosErros).length) return;
    onSalvar(formulario);
  }

  function alternarDia(dia: DiaSemana) {
    const selecionados = formulario.dias_selecionados.includes(dia)
      ? formulario.dias_selecionados.filter((item) => item !== dia)
      : [...formulario.dias_selecionados, dia];
    const ordenados = DIAS_SEMANA.filter((item) => selecionados.includes(item.valor)).map((item) => item.valor);
    setFormulario({ ...formulario, dias_selecionados: ordenados });
  }

  return (
    <DialogoResponsivo
      aberto={aberto}
      onFechar={onFechar}
      titulo={modo === "criar" ? "Criar rotina" : "Editar rotina"}
      descricao="Uma consulta que a Prata executa sozinha, no horário marcado. O pedido é conferido antes de salvar."
    >
      <form onSubmit={salvar} noValidate className="grid gap-4">
        {erro ? (
          <p role="alert" className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2.5 text-[13px] text-foreground">
            <IconeAviso aria-hidden="true" className="mt-px size-4 shrink-0 text-destructive" />
            {erro}
          </p>
        ) : null}

        <div className="grid gap-1.5">
          <label htmlFor="rotina-nome" className={ROTULO}>
            Nome da rotina *
          </label>
          <Input
            id="rotina-nome"
            value={formulario.nome}
            onChange={(evento) => setFormulario({ ...formulario, nome: evento.target.value })}
            aria-invalid={Boolean(erros.nome)}
            aria-describedby={erros.nome ? "erro-nome" : undefined}
            placeholder="Ex.: Resumo semanal do portfólio"
            autoComplete="off"
            className="h-10 bg-card"
          />
          {erros.nome ? <small className={ERRO} id="erro-nome">{erros.nome}</small> : null}
        </div>

        <div className="grid gap-1.5">
          <label htmlFor="rotina-prompt" className={ROTULO}>
            Ação em linguagem natural *
          </label>
          <textarea
            id="rotina-prompt"
            value={formulario.prompt}
            onChange={(evento) => setFormulario({ ...formulario, prompt: evento.target.value })}
            aria-invalid={Boolean(erros.prompt)}
            aria-describedby={erros.prompt ? "erro-prompt" : "ajuda-prompt"}
            placeholder="Descreva o que o Prata deve consultar ou acompanhar"
            rows={3}
            className="min-h-19 w-full resize-y rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-1 transition-[border-color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-primary/55 focus-visible:ring-3 focus-visible:ring-primary/15 aria-invalid:border-destructive"
          />
          <small id="ajuda-prompt" className="text-[12.5px] text-muted-foreground">
            A intenção prevista aparece na lista depois de salvar.
          </small>
          {erros.prompt ? <small className={ERRO} id="erro-prompt">{erros.prompt}</small> : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-[1.3fr_.9fr_1.2fr]">
          <div className="grid gap-1.5">
            <label htmlFor="rotina-repeticao" className={ROTULO}>
              Repetir *
            </label>
            <CampoSelecao
              id="rotina-repeticao"
              value={formulario.repeticao}
              onChange={(evento) => setFormulario({ ...formulario, repeticao: evento.target.value as Repeticao })}
            >
              <option value="diaria">Todos os dias</option>
              <option value="dias_uteis">Segunda a sexta</option>
              <option value="semanal">Semanalmente</option>
              <option value="mensal">Mensalmente</option>
              <option value="dias_personalizados">Dias personalizados</option>
              {formulario.repeticao === "legada" ? <option value="legada">Agendamento antigo</option> : null}
            </CampoSelecao>
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="rotina-horario" className={ROTULO}>
              Horário *
            </label>
            <Input
              id="rotina-horario"
              type="time"
              value={formulario.horario}
              onChange={(evento) => setFormulario({ ...formulario, horario: evento.target.value })}
              aria-invalid={Boolean(erros.horario)}
              aria-describedby={erros.horario ? "erro-horario" : undefined}
              className="h-10 bg-card tabular-nums"
            />
            {erros.horario ? <small className={ERRO} id="erro-horario">{erros.horario}</small> : null}
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="rotina-fuso" className={ROTULO}>
              Fuso *
            </label>
            <CampoSelecao
              id="rotina-fuso"
              value={formulario.timezone}
              onChange={(evento) => setFormulario({ ...formulario, timezone: evento.target.value })}
            >
              {/* O valor segue o identificador IANA que o agendador espera; a tela
                  mostra o nome que a pessoa reconhece. */}
              <option value="America/Sao_Paulo">Brasília</option>
              <option value="UTC">UTC</option>
            </CampoSelecao>
          </div>
        </div>

        {formulario.repeticao === "semanal" ? (
          <div className="grid gap-1.5">
            <label htmlFor="rotina-dia-semana" className={ROTULO}>
              Dia da semana *
            </label>
            <CampoSelecao
              id="rotina-dia-semana"
              value={formulario.dia_semana}
              onChange={(evento) => setFormulario({ ...formulario, dia_semana: evento.target.value as DiaSemana })}
            >
              {DIAS_SEMANA.map((dia) => (
                <option key={dia.valor} value={dia.valor}>
                  {dia.rotulo}
                </option>
              ))}
            </CampoSelecao>
          </div>
        ) : null}

        {formulario.repeticao === "mensal" ? (
          <div className="grid gap-1.5">
            <label htmlFor="rotina-dia-mes" className={ROTULO}>
              Dia do mês *
            </label>
            <Input
              id="rotina-dia-mes"
              type="number"
              min="1"
              max="31"
              value={formulario.dia_mes}
              onChange={(evento) => setFormulario({ ...formulario, dia_mes: evento.target.value })}
              aria-invalid={Boolean(erros.dia_mes)}
              aria-describedby={erros.dia_mes ? "erro-dia-mes" : undefined}
              className="h-10 w-28 bg-card tabular-nums"
            />
            {erros.dia_mes ? <small className={ERRO} id="erro-dia-mes">{erros.dia_mes}</small> : null}
          </div>
        ) : null}

        {formulario.repeticao === "dias_personalizados" ? (
          <fieldset className="grid min-w-0 gap-1.5" aria-describedby={erros.dias_selecionados ? "erro-dias" : undefined}>
            <legend className={cn(ROTULO, "mb-1.5")}>Dias da semana *</legend>
            <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-7">
              {DIAS_SEMANA.map((dia) => (
                <label key={dia.valor} className="relative cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formulario.dias_selecionados.includes(dia.valor)}
                    onChange={() => alternarDia(dia.valor)}
                    className="peer sr-only"
                  />
                  <span className="grid h-8.5 place-items-center rounded-md border border-input bg-card text-[12.5px] font-[550] text-muted-foreground transition-colors peer-checked:border-primary peer-checked:bg-primario-suave peer-checked:text-primario-texto peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ring">
                    {dia.rotulo.slice(0, 3)}
                  </span>
                </label>
              ))}
            </div>
            {erros.dias_selecionados ? <small className={ERRO} id="erro-dias">{erros.dias_selecionados}</small> : null}
          </fieldset>
        ) : null}

        {formulario.repeticao === "legada" ? (
          <div role="note" className="rounded-md border border-desfecho-abuso/30 bg-desfecho-abuso/10 px-3.5 py-3 text-[13px] leading-relaxed text-foreground">
            Este agendamento foi criado em um formato antigo (
            <code className="font-mono text-[13.5px]">{formulario.agenda_legada}</code>) e será preservado. Para
            modificá-lo, escolha uma nova opção em <strong>Repetir</strong>.
          </div>
        ) : null}

        <p aria-live="polite" className="flex items-start gap-2 rounded-md bg-primario-suave px-3 py-2.5 text-[13.5px] leading-snug text-foreground">
          <IconeRelogio aria-hidden="true" className="mt-px size-4 shrink-0 text-primario-texto" />
          <span>{resumoDaAgenda(formulario)}</span>
        </p>

        <div className="flex items-center justify-between gap-3.5 rounded-lg bg-secondary px-3.5 py-3">
          <div>
            <p id="rotulo-ativa" className="text-[13.5px] font-semibold text-foreground">
              Rotina ativa
            </p>
            <p id="ajuda-ativa" className="text-[12.5px] text-muted-foreground">
              Agendar assim que a configuração for salva.
            </p>
          </div>
          <Switch
            checked={formulario.ativa}
            onCheckedChange={(ativa) => setFormulario({ ...formulario, ativa })}
            aria-labelledby="rotulo-ativa"
            aria-describedby="ajuda-ativa"
            className="data-[state=unchecked]:bg-controle-desligado"
          />
        </div>

        <div className="mt-1 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onFechar} className="bg-card">
            Cancelar
          </Button>
          <Button type="submit" disabled={salvando}>
            {salvando ? "Validando e salvando..." : modo === "criar" ? "Criar rotina" : "Salvar alterações"}
          </Button>
        </div>
      </form>
    </DialogoResponsivo>
  );
}
