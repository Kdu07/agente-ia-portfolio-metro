/**
 * Pagina principal: a conversa com o agente.
 *
 * O envio passa pelo contrato de POST /chat. Em desenvolvimento quem
 * responde e o duble em `mocks/handlers.ts`; a tela nao sabe a diferenca,
 * e essa e a propriedade que permite trocar o duble pelo middleware sem
 * tocar aqui.
 *
 * Sem `:conversaId` a tela e uma conversa nova, com sugestoes de partida.
 * Com o parametro, os turnos gravados sao carregados e as mensagens novas
 * entram na sequencia. A remontagem entre uma conversa e outra e
 * garantida pela `key` em `rotas.tsx`.
 *
 * O cabecalho mostra o titulo da conversa e quantas perguntas ela tem. O
 * "Projeto X" fixo que ficava ali parecia um seletor de projeto e nao era.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AnimatePresence } from "motion/react";

import { AvisoMarco } from "@/componentes/chat/AvisoMarco";
import { BolhaMensagem } from "@/componentes/chat/BolhaMensagem";
import { Composer } from "@/componentes/chat/Composer";
import { ConversaVazia } from "@/componentes/chat/ConversaVazia";
import { IndicadorDigitando } from "@/componentes/chat/IndicadorDigitando";
import { BotaoIcone } from "@/componentes/ui/BotaoIcone";
import { Button } from "@/componentes/ui/button";
import { CabecalhoPagina } from "@/componentes/ui/CabecalhoPagina";
import { IconeAviso, IconeEscreverNova } from "@/componentes/ui/icones";
import { CHAVE_CONVERSA_ATIVA, useConversa } from "@/hooks/useConversa";
import { useMicrofone } from "@/hooks/useMicrofone";

export function Principal() {
  const { conversaId } = useParams<{ conversaId: string }>();
  const {
    linhas,
    titulo,
    carregando,
    enviando,
    erro,
    podeReenviar,
    erroAoCarregar,
    recarregar,
    enviar,
    reenviarUltima,
    conversaIdAtual,
  } = useConversa(conversaId);
  const navegar = useNavigate();

  // O alerta proativo so faz sentido numa conversa nova: ele fala do
  // agora, e reaparecer ao abrir uma conversa de tres dias atras daria a
  // impressao de que o marco acabou de atrasar.
  const [notificacao, setNotificacao] = useState(!conversaIdAtual);
  const [texto, setTexto] = useState("");
  const campo = useRef<HTMLTextAreaElement>(null);

  // A transcricao final chega ao campo em vez de ser enviada direto: a
  // pessoa precisa poder revisar antes, porque reconhecimento de fala
  // erra nome proprio e numero, que e justamente o que uma solicitacao
  // sobre projeto costuma conter.
  const receberTranscricao = useCallback((transcrito: string) => {
    setTexto((atual) => (atual ? `${atual} ${transcrito}` : transcrito));
  }, []);
  const voz = useMicrofone(receberTranscricao);

  // A lista de mensagens tem rolagem propria. Sem trazer o fim para a
  // vista a cada mensagem nova, a resposta chega fora do campo visivel e
  // a pessoa precisa rolar para descobrir que ela chegou.
  const fimDaLista = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ block: "end" });
  }, [linhas.length, enviando]);

  function submeter() {
    enviar(texto);
    setTexto("");
  }

  function escolherSugestao(sugestao: string) {
    setTexto(sugestao);
    campo.current?.focus();
  }

  function verDetalhes() {
    setNotificacao(false);
    enviar("Por que o marco “Entrega da Fase 2” está atrasado?");
  }

  // Mesmo caminho do botao da barra lateral: sem a conversa ativa no
  // `sessionStorage` e com o estado que troca a chave da pagina (#425).
  function novaConversa() {
    sessionStorage.removeItem(CHAVE_CONVERSA_ATIVA);
    navegar("/", { state: { novaConversa: true } });
  }

  const semMensagens = !carregando && linhas.length === 0;
  const perguntas = linhas.filter((linha) => linha.autor === "usuario");
  // Ate o servidor devolver o titulo, "Nova conversa": repetir a primeira
  // pergunta no topo duplicaria na tela o texto que ja esta logo abaixo.
  const tituloDaConversa = titulo ?? "Nova conversa";
  const subtitulo =
    perguntas.length === 0
      ? "Ainda sem mensagens"
      : `${perguntas.length} ${perguntas.length === 1 ? "pergunta" : "perguntas"}`;

  return (
    <div className="fundo-conversa grao flex h-full min-h-0 flex-col">
      <CabecalhoPagina
        tituloDaPagina
        titulo={tituloDaConversa}
        subtitulo={subtitulo}
        className="border-border/70 bg-card/55 backdrop-blur-md"
        acoes={<BotaoIcone rotulo="Nova conversa" icone={IconeEscreverNova} onClick={novaConversa} />}
      />

      <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={enviando}>
        <div className="mx-auto w-full max-w-190 px-3.5 pt-6.5 pb-4 md:px-6">
          {carregando ? <p className="text-sm text-muted-foreground">Carregando a conversa...</p> : null}

          {semMensagens ? (
            <>
              <AnimatePresence initial={false}>
                {notificacao ? (
                  <AvisoMarco key="aviso" onVerDetalhes={verDetalhes} onDispensar={() => setNotificacao(false)} />
                ) : null}
              </AnimatePresence>
              <ConversaVazia onEscolher={escolherSugestao} />
            </>
          ) : null}

          <div className="grid gap-5">
            {linhas.map((linha) => (
              <BolhaMensagem
                key={linha.id}
                autor={linha.autor}
                texto={linha.texto}
                horario={linha.horario}
                desfecho={linha.desfecho}
                canal={linha.canal}
                local={linha.local}
                intencaoId={linha.intencaoId}
              />
            ))}
            {enviando ? <IndicadorDigitando /> : null}
          </div>

          <div ref={fimDaLista} />
        </div>
      </div>

      <div className="px-3 pt-2 pb-3.5 md:px-6">
        {voz.erro ? (
          <div
            role="alert"
            className="mx-auto mb-2 flex w-full max-w-190 items-center gap-2.5 rounded-lg border border-destructive/40 bg-card px-4 py-3 text-sm text-foreground"
          >
            <IconeAviso aria-hidden="true" className="shrink-0 text-destructive" />
            {voz.erro}
          </div>
        ) : null}

        {erroAoCarregar ? (
          <div
            role="alert"
            className="mx-auto mb-2 flex w-full max-w-190 items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-card px-4 py-3"
          >
            <span className="flex items-center gap-2.5 text-sm text-foreground">
              <IconeAviso aria-hidden="true" className="shrink-0 text-destructive" />
              {erroAoCarregar}
            </span>
            <Button type="button" variant="outline" size="sm" onClick={recarregar} className="shrink-0 bg-card">
              Recarregar conversa
            </Button>
          </div>
        ) : null}

        {erro ? (
          <div
            role="alert"
            className="mx-auto mb-2 flex w-full max-w-190 items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-card px-4 py-3"
          >
            <span className="flex items-center gap-2.5 text-sm text-foreground">
              <IconeAviso aria-hidden="true" className="shrink-0 text-destructive" />
              {erro}
            </span>
            {podeReenviar ? (
              <Button type="button" variant="outline" size="sm" onClick={reenviarUltima} className="shrink-0 bg-card">
                Tentar novamente
              </Button>
            ) : null}
          </div>
        ) : null}

        <Composer
          refCampo={campo}
          valor={texto}
          estadoVoz={voz.estado}
          parcial={voz.parcial}
          onAlterar={setTexto}
          onEnviar={submeter}
          onAlternarVoz={voz.alternar}
        />
        <p className="mx-auto mt-2 w-full max-w-190 text-center text-xs text-muted-foreground">
          A Prata responde com base nos documentos dos projetos. Confira dados críticos antes de decidir.
        </p>
      </div>
    </div>
  );
}
