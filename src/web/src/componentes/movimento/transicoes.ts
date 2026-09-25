/**
 * Presets de movimento. Um lugar só para duração e curva: se cada
 * componente escolher os seus números, a interface perde o ritmo comum
 * e ninguém consegue ajustá-lo depois.
 */
export const CURVA_SAIDA = [0.16, 1, 0.3, 1] as const;
export const CURVA_PADRAO = [0.2, 0, 0, 1] as const;

// Pílula da navegação: mola com ~5% de ultrapassagem.
export const MOLA_INDICADOR = { type: "spring", stiffness: 420, damping: 32, mass: 0.8 } as const;

export const ENTRADA_RESPOSTA = {
  initial: { opacity: 0, y: 8, filter: "blur(3px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  transition: { duration: 0.38, ease: CURVA_SAIDA },
} as const;

export const ENTRADA_PERGUNTA = {
  initial: { opacity: 0, y: 14, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  transition: { duration: 0.36, ease: CURVA_SAIDA },
} as const;

export const CASCATA = { animate: { transition: { staggerChildren: 0.055 } } } as const;
export const SOBE = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: CURVA_SAIDA } },
} as const;

export const TROCA_DE_TELA = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.28, ease: CURVA_SAIDA } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.16, ease: CURVA_PADRAO } },
} as const;
