/**
 * Junta classes do Tailwind resolvendo conflitos.
 *
 * `clsx` monta a lista a partir de condições, e `twMerge` descarta a
 * utilidade que perde para outra do mesmo grupo: um componente que recebe
 * `className="px-2"` sobre um `px-4` interno fica com `px-2`, em vez de
 * depender da ordem das regras no CSS gerado. É o `cn` que os componentes
 * do shadcn importam.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...entradas: ClassValue[]) {
  return twMerge(clsx(entradas));
}
