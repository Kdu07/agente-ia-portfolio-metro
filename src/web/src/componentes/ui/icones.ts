/**
 * Todos os ícones da interface, com nome pelo papel e não pelo desenho.
 *
 * Antes cada tela usava um caractere Unicode diferente (↺ ⌕ ◇ → × ! ✓ +),
 * e cada um vinha de uma fonte de reserva com linha de base própria: é daí
 * que saía o desalinhamento. Agora tudo é Phosphor, importado só daqui.
 *
 * Cada ícone vem do próprio arquivo (`dist/csr/<Nome>`), e não do índice
 * do pacote. No build o índice some por tree-shaking, mas no servidor de
 * desenvolvimento o Vite o pré-empacota inteiro: são 1.500 ícones e 6 MB
 * que o navegador interpreta a cada recarga. Por isso o lint barra o
 * pacote em qualquer outro arquivo, inclusive nos gerados pelo shadcn.
 *
 * Tamanho e peso padrão vêm do `IconContext` na raiz (20 px, regular). O
 * peso `fill` fica reservado ao item ativo da navegação.
 */

// `dist/lib/<arquivo>`, e não `/lib`: o mapa de exports do pacote aponta
// `/lib` para um `index.es.js` que não é publicado.
export type { Icon as Icone, IconProps as PropsDoIcone, IconWeight as PesoDoIcone } from "@phosphor-icons/react/dist/lib/types";
export { IconContext } from "@phosphor-icons/react/dist/lib/context";

// Navegação e moldura
export { PlusIcon as IconeNovaConversa, PlusIcon as IconeAdicionar } from "@phosphor-icons/react/dist/csr/Plus";
export { NotePencilIcon as IconeEscreverNova } from "@phosphor-icons/react/dist/csr/NotePencil";
export { ChatCircleTextIcon as IconeConversa } from "@phosphor-icons/react/dist/csr/ChatCircleText";
export {
  ClockCounterClockwiseIcon as IconeHistorico,
  ClockCounterClockwiseIcon as IconeResultados,
} from "@phosphor-icons/react/dist/csr/ClockCounterClockwise";
export { ChartBarIcon as IconeIntencoes } from "@phosphor-icons/react/dist/csr/ChartBar";
export { CalendarCheckIcon as IconeRotinas, CalendarCheckIcon as IconeRotina } from "@phosphor-icons/react/dist/csr/CalendarCheck";
export { ListIcon as IconeMenu } from "@phosphor-icons/react/dist/csr/List";
export { XIcon as IconeFechar } from "@phosphor-icons/react/dist/csr/X";
export { SidebarSimpleIcon as IconeRecolher } from "@phosphor-icons/react/dist/csr/SidebarSimple";

// Listas e filtros
export { MagnifyingGlassIcon as IconeBuscar } from "@phosphor-icons/react/dist/csr/MagnifyingGlass";
export { SortAscendingIcon as IconeOrdenar } from "@phosphor-icons/react/dist/csr/SortAscending";
export { CaretDownIcon as IconeCaret } from "@phosphor-icons/react/dist/csr/CaretDown";
export { ArchiveIcon as IconeArquivar } from "@phosphor-icons/react/dist/csr/Archive";

// Compositor e mensagens
export { MicrophoneIcon as IconeMicrofone, MicrophoneIcon as IconeVoz } from "@phosphor-icons/react/dist/csr/Microphone";
export { StopIcon as IconeParar } from "@phosphor-icons/react/dist/csr/Stop";
export { ArrowUpIcon as IconeEnviar } from "@phosphor-icons/react/dist/csr/ArrowUp";
export { CopyIcon as IconeCopiar } from "@phosphor-icons/react/dist/csr/Copy";
export { CheckIcon as IconeCopiado, CheckIcon as IconeMarcado } from "@phosphor-icons/react/dist/csr/Check";

// Menu do perfil
export { SunIcon as IconeClaro } from "@phosphor-icons/react/dist/csr/Sun";
export { MoonIcon as IconeEscuro } from "@phosphor-icons/react/dist/csr/Moon";
export { DesktopIcon as IconeSistema } from "@phosphor-icons/react/dist/csr/Desktop";
export { SignOutIcon as IconeSair } from "@phosphor-icons/react/dist/csr/SignOut";
export { CaretUpDownIcon as IconeConta } from "@phosphor-icons/react/dist/csr/CaretUpDown";

// Rotinas e histórico
export { PauseIcon as IconePausar } from "@phosphor-icons/react/dist/csr/Pause";
export { PlayIcon as IconeAtivar, PlayIcon as IconeExecutar } from "@phosphor-icons/react/dist/csr/Play";
export { PencilSimpleIcon as IconeEditar, PencilSimpleIcon as IconeRegistrar } from "@phosphor-icons/react/dist/csr/PencilSimple";
export { TrashIcon as IconeExcluir } from "@phosphor-icons/react/dist/csr/Trash";

// Avisos e estados
export { BellRingingIcon as IconeAlerta } from "@phosphor-icons/react/dist/csr/BellRinging";
export { CheckCircleIcon as IconeSucesso, CheckCircleIcon as IconeConcluida } from "@phosphor-icons/react/dist/csr/CheckCircle";
export { WarningCircleIcon as IconeAviso } from "@phosphor-icons/react/dist/csr/WarningCircle";
export { LockSimpleIcon as IconeCadeado } from "@phosphor-icons/react/dist/csr/LockSimple";
export { ClockIcon as IconeRelogio } from "@phosphor-icons/react/dist/csr/Clock";
export { SignpostIcon as IconeCaminho } from "@phosphor-icons/react/dist/csr/Signpost";
export { CircleNotchIcon as IconeCarregando } from "@phosphor-icons/react/dist/csr/CircleNotch";

// Desfechos das respostas e status de execução (o rótulo ao lado diz o que aconteceu)
export {
  ShieldWarningIcon as IconeNaoAtendida,
  ShieldWarningIcon as IconeBloqueada,
} from "@phosphor-icons/react/dist/csr/ShieldWarning";
export {
  CloudSlashIcon as IconeIndisponivel,
  CloudSlashIcon as IconeFalhou,
} from "@phosphor-icons/react/dist/csr/CloudSlash";
export { CompassIcon as IconeForaDoEscopo } from "@phosphor-icons/react/dist/csr/Compass";
export { QuestionIcon as IconeBaixaConfianca } from "@phosphor-icons/react/dist/csr/Question";
export { ProhibitIcon as IconeRegrasDeUso } from "@phosphor-icons/react/dist/csr/Prohibit";

// Sugestões da conversa vazia
export { FlagIcon as IconeMarco } from "@phosphor-icons/react/dist/csr/Flag";
export { WarningIcon as IconeRisco } from "@phosphor-icons/react/dist/csr/Warning";
export { ChartLineUpIcon as IconeComparar } from "@phosphor-icons/react/dist/csr/ChartLineUp";

// Usados pelos componentes do shadcn
export { CaretRightIcon as IconeCaretDireita } from "@phosphor-icons/react/dist/csr/CaretRight";
export { CircleIcon as IconeCirculo } from "@phosphor-icons/react/dist/csr/Circle";
