/**
 * Degradê vertical da logo, pintado pelos tokens `--logo-tinta-1..3`.
 *
 * As cores vêm de variável CSS, e não de atributo fixo, para que a mesma
 * logo saia marinho sobre fundo claro e prata sobre marinho: quem decide é
 * a superfície, com a utilidade `marca-prata`.
 */
export function DegradeDaLogo({ id }: { id: string }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" style={{ stopColor: "var(--logo-tinta-1)" }} />
      <stop offset="0.55" style={{ stopColor: "var(--logo-tinta-2)" }} />
      <stop offset="1" style={{ stopColor: "var(--logo-tinta-3)" }} />
    </linearGradient>
  );
}
