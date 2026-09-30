/**
 * Captura responsiva das seis telas da interface nas três larguras de referência.
 * Larguras: celular (375 px), tablet (768 px), desktop (1280 px).
 * Saída: docs/evidencias/responsivo/<tela>-<dispositivo>.png
 *
 * Uso: npm run captura:responsivo   (ou: node scripts/captura-responsiva.mjs)
 * Variáveis: BASE_URL (opcional), PORTA_PREVIEW (padrão 4173), PULAR_BUILD=1
 */

import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "../..");
const OUT_DIR = path.join(REPO_ROOT, "docs/evidencias/responsivo");

const PORTA = Number(process.env.PORTA_PREVIEW || 4173);
const BASE_URL = (process.env.BASE_URL || `http://127.0.0.1:${PORTA}`).replace(/\/$/, "");

const LARGURAS = [
  { id: "celular", width: 375, height: 812 },
  { id: "tablet", width: 768, height: 1024 },
  { id: "desktop", width: 1280, height: 800 },
];

const TELAS = [
  { id: "login", caminho: "/entrar", seletor: "h1" },
  { id: "principal", caminho: "/", seletor: "main, [role='main'], textarea" },
  { id: "historico", caminho: "/historico", seletor: "h1, [role='heading']" },
  { id: "intencoes", caminho: "/intencoes", seletor: "h1, [role='heading']" },
  { id: "rotinas", caminho: "/rotinas", seletor: "h1, [role='heading']" },
  { id: "nao-encontrada", caminho: "/pagina-inexistente", seletor: "a[href='/']" },
];

const USUARIO = {
  id: "usuario-demonstracao",
  nome: "Fernanda Silva",
  email: "fernanda@empresa.com.br",
  perfil: "lider_projeto",
  permissoes: ["ver_intencoes", "gerir_rotinas"],
};

function jsonOk(rota, corpo, status = 200) {
  return rota.fulfill({ status, contentType: "application/json", body: JSON.stringify(corpo) });
}

async function registrarMocks(page) {
  await page.route("**/api/**", async (rota) => {
    const pedido = rota.request();
    const metodo = pedido.method();
    const caminho = new URL(pedido.url()).pathname.replace(/^\/api/, "") || "/";

    if (metodo === "GET" && caminho === "/auth/eu")                               return jsonOk(rota, USUARIO);
    if (metodo === "POST" && caminho === "/auth/logout")                          return rota.fulfill({ status: 204, body: "" });
    if (metodo === "GET" && caminho === "/conversas")                             return jsonOk(rota, [{ id: "projeto-x", titulo: "Status do Projeto X", criada_em: new Date().toISOString(), atualizada_em: new Date().toISOString(), total_turnos: 0 }]);
    if (metodo === "GET" && /^\/conversas\/[^/]+$/.test(caminho))                return jsonOk(rota, { id: "projeto-x", titulo: "Status do Projeto X", turnos: [] });
    if (metodo === "GET" && caminho === "/rotinas")                               return jsonOk(rota, []);
    if (metodo === "GET" && /^\/rotinas\/[^/]+\/execucoes$/.test(caminho))       return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/volume")                      return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/desfechos")                   return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/seguranca/resumo")            return jsonOk(rota, { total_mensagens: 0, bloqueios_injecao: 0, bloqueios_abuso: 0, bloqueios_saida: 0, taxa_de_bloqueio: 0 });
    if (metodo === "GET" && caminho === "/intencoes/seguranca/serie")             return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/catalogo/resumo")             return jsonOk(rota, { intencoes_acionadas: 0, intencoes_sem_uso: 0, enunciados_fora_de_escopo: 0, enunciados_baixa_confianca: 0 });
    if (metodo === "GET" && caminho === "/intencoes/catalogo/fora-de-escopo")     return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/catalogo/baixa-confianca")    return jsonOk(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/latencia")                    return jsonOk(rota, { p50: 0, p95: 0, etapas: [] });

    if (["POST", "PUT", "DELETE"].includes(metodo)) return rota.fulfill({ status: 204, body: "" });
    return jsonOk(rota, {});
  });
}

async function aguardarServidor(url, tentativas = 60) {
  for (let i = 0; i < tentativas; i++) {
    try {
      const r = await fetch(url);
      if (r.ok || r.status === 404) return;
    } catch { }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Servidor não respondeu em ${url}`);
}

function iniciarPreview() {
  const filho = spawn(`npx vite preview --host 127.0.0.1 --port ${PORTA}`, {
    cwd: WEB_ROOT,
    stdio: ["ignore", "pipe", "pipe"],
    shell: true,
    env: { ...process.env },
  });
  filho.stdout.on("data", (d) => process.stderr.write(`[preview] ${d}`));
  filho.stderr.on("data", (d) => process.stderr.write(`[preview] ${d}`));
  return filho;
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  let preview = null;

  if (!process.env.BASE_URL) {
    if (!process.env.PULAR_BUILD) {
      process.stderr.write("Compilando frontend (npm run build)...\n");
      await new Promise((resolve, reject) => {
        const build = spawn("npm run build", { cwd: WEB_ROOT, stdio: "inherit", shell: true });
        build.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`build exit ${code}`))));
      });
    }
    preview = iniciarPreview();
    await aguardarServidor(BASE_URL);
  }

  const browser = await chromium.launch({ headless: true });

  try {
    for (const disp of LARGURAS) {
      for (const tela of TELAS) {
        const contexto = await browser.newContext({
          viewport: { width: disp.width, height: disp.height },
          colorScheme: "light",
        });
        const page = await contexto.newPage();
        await registrarMocks(page);

        const url = `${BASE_URL}${tela.caminho}`;
        process.stderr.write(`Capturando ${tela.id} em ${disp.id} (${disp.width}×${disp.height}) → ${url}\n`);

        // Navega e aguarda resposta do /auth/eu para que o hook useUsuario resolva
        const [, ] = await Promise.all([
          page.waitForResponse((resp) => resp.url().includes("/api/auth/eu"), { timeout: 30_000 }).catch(() => null),
          page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 }),
        ]);

        // Espera a renderização estabilizar
        await page.waitForTimeout(1500);
        try {
          await page.waitForSelector(tela.seletor, { timeout: 10_000 });
        } catch { /* tela pode não ter o seletor exato */ }

        const filepath = path.join(OUT_DIR, `${tela.id}-${disp.id}.png`);
        await page.screenshot({ path: filepath, fullPage: true });
        process.stderr.write(`  → salvo em ${filepath}\n`);

        await contexto.close();
      }
    }
  } finally {
    await browser.close();
    if (preview) preview.kill("SIGTERM");
  }

  process.stderr.write("\nCapturas concluídas.\n");
}

main().catch((erro) => {
  console.error(erro);
  process.exit(1);
});
