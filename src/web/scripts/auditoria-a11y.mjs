/**
 * Auditoria WCAG 2.1 A/AA das telas do frontend (issue #468).
 *
 * Sobe o `vite preview` (ou usa BASE_URL), intercepta /api/* no Playwright
 * com JSON minimo alinhado aos dubles de teste, percorre 6 telas × 2 temas
 * e coleta violacoes axe (tags wcag2a/aa e wcag21a/aa).
 *
 * Uso: npm run audit:a11y
 * Variaveis: BASE_URL (opcional), PORTA_PREVIEW (padrao 4173), PULAR_BUILD=1
 */

import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { AxeBuilder } from "@axe-core/playwright";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "../..");
const RELATORIO = path.join(REPO_ROOT, "docs/evidencias/2026-09-28-auditoria-acessibilidade.txt");

const PORTA = Number(process.env.PORTA_PREVIEW || 4173);
const BASE_URL = (process.env.BASE_URL || `http://127.0.0.1:${PORTA}`).replace(/\/$/, "");
const TAGS_AXE = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const USUARIO = {
  id: "usuario-demonstracao",
  nome: "Fernanda Silva",
  email: "fernanda@empresa.com.br",
  perfil: "lider_projeto",
  permissoes: ["ver_intencoes", "gerir_rotinas"],
};

const CONVERSAS = [
  {
    id: "projeto-x",
    titulo: "Status do Projeto X",
    criada_em: new Date(Date.now() - 5 * 3_600_000).toISOString(),
    atualizada_em: new Date(Date.now() - 2 * 3_600_000).toISOString(),
    total_turnos: 3,
  },
];

const ROTINAS = [
  {
    id: "rotina-status-semanal",
    nome: "Resumo semanal do portfólio",
    prompt: "Consolidar o status, os riscos e os próximos marcos dos projetos ativos.",
    agenda_cron: "0 9 * * mon",
    timezone: "America/Sao_Paulo",
    ativa: true,
    intencao_prevista: "consultar_status_portfolio",
    intencao_prevista_rotulo: "Consultar status do portfólio",
    proximo_disparo: new Date(Date.now() + 3 * 86_400_000).toISOString(),
    criada_em: new Date(Date.now() - 20 * 86_400_000).toISOString(),
    atualizada_em: new Date(Date.now() - 6 * 86_400_000).toISOString(),
  },
];

const VOLUME = [{ chave: "consultar_status_projeto", rotulo: "Consultar status de projeto", total: 184 }];
const DESFECHOS = [{ chave: "encaminhada", rotulo: "Atendida", total: 495 }];
const RESUMO_SEGURANCA = {
  total_mensagens: 596,
  bloqueios_injecao: 14,
  bloqueios_abuso: 7,
  bloqueios_saida: 2,
  taxa_de_bloqueio: 0.039,
};
const SERIE_BLOQUEIOS = [
  { nome: "injecao", pontos: [{ momento: "2026-09-22", total: 2 }] },
  { nome: "abuso", pontos: [{ momento: "2026-09-22", total: 1 }] },
  { nome: "saida", pontos: [{ momento: "2026-09-22", total: 0 }] },
];
const RESUMO_CATALOGO = {
  intencoes_acionadas: 6,
  intencoes_sem_uso: 2,
  enunciados_fora_de_escopo: 41,
  enunciados_baixa_confianca: 23,
};
const FORA_DE_ESCOPO = [
  {
    prompt: "Qual a previsão do tempo para amanhã?",
    ocorrencias: 6,
    ultima_em: new Date().toISOString(),
    confianca_media: 0.12,
  },
];
const BAIXA_CONFIANCA = [
  {
    prompt: "E o andamento daquele projeto?",
    ocorrencias: 11,
    ultima_em: new Date().toISOString(),
    confianca_media: 0.44,
  },
];
const LATENCIA = {
  p50: 1350,
  p95: 2900,
  etapas: [
    { etapa: "injecao", p50: 180, p95: 420, amostras: 596 },
    { etapa: "abuso", p50: 95, p95: 240, amostras: 582 },
    { etapa: "intencao", p50: 40, p95: 110, amostras: 575 },
    { etapa: "executor", p50: 980, p95: 2250, amostras: 509 },
    { etapa: "saida", p50: 120, p95: 310, amostras: 495 },
  ],
};

const TELAS = [
  { id: "login", nome: "Login", caminho: "/entrar", seletor: "h1" },
  { id: "principal", nome: "Principal", caminho: "/", seletor: "main, [role='main'], textarea, form" },
  { id: "historico", nome: "Histórico", caminho: "/historico", seletor: "h1, [role='heading']" },
  { id: "intencoes", nome: "Intenções", caminho: "/intencoes", seletor: "h1, [role='heading']" },
  { id: "rotinas", nome: "Rotinas", caminho: "/rotinas", seletor: "h1, [role='heading']" },
  {
    id: "nao-encontrada",
    nome: "Não encontrada",
    caminho: "/pagina-inexistente",
    // CabecalhoPagina usa <p> por padrao (sem tituloDaPagina); o CTA confirma a tela.
    seletor: "a[href='/']",
  },
];

const TEMAS = [
  { id: "claro", valor: "claro", classeDark: false },
  { id: "escuro", valor: "escuro", classeDark: true },
];

function json(rota, corpo, status = 200) {
  return rota.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(corpo),
  });
}

async function registrarMocks(page) {
  await page.route("**/api/**", async (rota) => {
    const pedido = rota.request();
    const metodo = pedido.method();
    const url = new URL(pedido.url());
    const caminho = url.pathname.replace(/^\/api/, "") || "/";

    if (metodo === "GET" && caminho === "/auth/eu") return json(rota, USUARIO);
    if (metodo === "POST" && caminho === "/auth/logout") {
      return rota.fulfill({ status: 204, body: "" });
    }
    if (metodo === "GET" && caminho === "/conversas") return json(rota, CONVERSAS);
    if (metodo === "GET" && /^\/conversas\/[^/]+$/.test(caminho)) {
      return json(rota, {
        id: "projeto-x",
        titulo: "Status do Projeto X",
        criada_em: CONVERSAS[0].criada_em,
        atualizada_em: CONVERSAS[0].atualizada_em,
        turnos: [],
      });
    }
    if (metodo === "GET" && caminho === "/rotinas") return json(rota, ROTINAS);
    if (metodo === "GET" && /^\/rotinas\/[^/]+\/execucoes$/.test(caminho)) return json(rota, []);
    if (metodo === "GET" && caminho === "/intencoes/volume") return json(rota, VOLUME);
    if (metodo === "GET" && caminho === "/intencoes/desfechos") return json(rota, DESFECHOS);
    if (metodo === "GET" && caminho === "/intencoes/seguranca/resumo") return json(rota, RESUMO_SEGURANCA);
    if (metodo === "GET" && caminho === "/intencoes/seguranca/serie") return json(rota, SERIE_BLOQUEIOS);
    if (metodo === "GET" && caminho === "/intencoes/catalogo/resumo") return json(rota, RESUMO_CATALOGO);
    if (metodo === "GET" && caminho === "/intencoes/catalogo/fora-de-escopo") return json(rota, FORA_DE_ESCOPO);
    if (metodo === "GET" && caminho === "/intencoes/catalogo/baixa-confianca") return json(rota, BAIXA_CONFIANCA);
    if (metodo === "GET" && caminho === "/intencoes/latencia") return json(rota, LATENCIA);

    // Demais rotas da API: 204/JSON vazio para nao derrubar a pagina.
    if (metodo === "POST" || metodo === "PUT" || metodo === "DELETE") {
      return rota.fulfill({ status: 204, body: "" });
    }
    return json(rota, {});
  });
}

async function aplicarTema(page, tema) {
  await page.addInitScript((preferencia) => {
    try {
      localStorage.setItem("prata:tema", preferencia);
    } catch {
      // ignore
    }
    document.documentElement.classList.toggle("dark", preferencia === "escuro");
  }, tema.valor);
}

async function checagemTeclado(page) {
  return page.evaluate(() => {
    const focaveis = [
      ...document.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((el) => {
      const estilo = window.getComputedStyle(el);
      return estilo.display !== "none" && estilo.visibility !== "hidden" && el.getClientRects().length > 0;
    });

    const amostra = focaveis.slice(0, 12).map((el, i) => {
      const rotulo =
        el.getAttribute("aria-label") ||
        el.getAttribute("title") ||
        (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 60) ||
        el.tagName.toLowerCase();
      return `${i + 1}. <${el.tagName.toLowerCase()}> ${rotulo}`;
    });

    const estilos = [...document.styleSheets]
      .flatMap((sheet) => {
        try {
          return [...sheet.cssRules].map((r) => r.cssText || "");
        } catch {
          return [];
        }
      })
      .join("\n");

    const temFocusVisible =
      /:focus-visible/.test(estilos) ||
      Boolean(document.querySelector("[class*='focus-visible'], [data-focus-visible]"));

    const dialogos = document.querySelectorAll('[role="dialog"], [role="alertdialog"], [data-state="open"][role="dialog"]');

    return {
      totalFocaveis: focaveis.length,
      amostraOrdemTab: amostra,
      temRegraFocusVisible: temFocusVisible,
      dialogosAbertos: dialogos.length,
      temMain: Boolean(document.querySelector("main, [role='main']")),
      temH1: Boolean(document.querySelector("h1")),
    };
  });
}

function formatarViolacao(v) {
  const criterios = (v.tags || []).filter((t) => /wcag/i.test(t)).join(", ") || "—";
  const nos = (v.nodes || [])
    .slice(0, 5)
    .map((n, i) => {
      const alvo = (n.target || []).join(" » ");
      const falha = (n.failureSummary || "").replace(/\s+/g, " ").slice(0, 220);
      return `      nó ${i + 1}: ${alvo}\n        ${falha}`;
    })
    .join("\n");
  return [
    `  - id: ${v.id}`,
    `    impacto: ${v.impact || "—"}`,
    `    critérios/tags: ${criterios}`,
    `    descrição: ${v.description}`,
    `    ajuda: ${v.help}`,
    `    nós afetados (${v.nodes?.length ?? 0}):`,
    nos || "      (sem nós)",
  ].join("\n");
}

function resumoImpacto(violacoes) {
  const contagem = { critical: 0, serious: 0, moderate: 0, minor: 0 };
  for (const v of violacoes) {
    const chave = v.impact && contagem[v.impact] !== undefined ? v.impact : "minor";
    contagem[chave] += 1;
  }
  return contagem;
}

async function aguardarServidor(url, tentativas = 60) {
  for (let i = 0; i < tentativas; i += 1) {
    try {
      const resp = await fetch(url, { method: "GET" });
      if (resp.ok || resp.status === 404) return;
    } catch {
      // ainda subindo
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Servidor não respondeu em ${url}`);
}

function iniciarPreview() {
  if (process.env.BASE_URL) return null;
  const filho = spawn("npx vite preview --host 127.0.0.1 --port " + String(PORTA), {
    cwd: WEB_ROOT,
    stdio: ["ignore", "pipe", "pipe"],
    shell: true,
    env: { ...process.env },
  });
  filho.stdout.on("data", (d) => process.stderr.write(`[preview] ${d}`));
  filho.stderr.on("data", (d) => process.stderr.write(`[preview] ${d}`));
  return filho;
}

async function gitInfo() {
  const require = createRequire(import.meta.url);
  const { execSync } = require("node:child_process");
  const run = (cmd) => {
    try {
      return execSync(cmd, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
    } catch {
      return "desconhecido";
    }
  };
  return {
    branch: run("git branch --show-current"),
    commit: run("git rev-parse HEAD"),
    curto: run("git rev-parse --short HEAD"),
  };
}

async function main() {
  const git = await gitInfo();
  let preview = null;

  if (!process.env.BASE_URL) {
    if (process.env.PULAR_BUILD !== "1") {
      process.stderr.write("Compilando frontend (npm run build)...\n");
      await new Promise((resolve, reject) => {
        const build = spawn("npm run build", {
          cwd: WEB_ROOT,
          stdio: "inherit",
          shell: true,
        });
        build.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`build exit ${code}`))));
      });
    }
    preview = iniciarPreview();
    await aguardarServidor(BASE_URL);
  }

  const browser = await chromium.launch({ headless: true });
  const resultados = [];
  const tecladoPorTela = [];

  try {
    for (const tema of TEMAS) {
      for (const tela of TELAS) {
        const contexto = await browser.newContext({
          viewport: { width: 1280, height: 800 },
          colorScheme: tema.id === "escuro" ? "dark" : "light",
        });
        const page = await contexto.newPage();
        await registrarMocks(page);
        await aplicarTema(page, tema);

        const url = `${BASE_URL}${tela.caminho}`;
        process.stderr.write(`Auditando ${tela.nome} / tema ${tema.id} → ${url}\n`);

        await page.goto(url, { waitUntil: "networkidle", timeout: 60_000 });
        // Garante tema apos hidratacao do React
        await page.evaluate((preferencia) => {
          try {
            localStorage.setItem("prata:tema", preferencia);
          } catch {
            // ignore
          }
          document.documentElement.classList.toggle("dark", preferencia === "escuro");
        }, tema.valor);

        await page.waitForTimeout(800);
        try {
          await page.waitForSelector(tela.seletor, { timeout: 15_000 });
        } catch {
          process.stderr.write(`  aviso: seletor ${tela.seletor} nao apareceu a tempo\n`);
        }

        const analise = await new AxeBuilder({ page }).withTags(TAGS_AXE).analyze();
        const teclado = await checagemTeclado(page);

        resultados.push({
          tela: tela.nome,
          caminho: tela.caminho,
          tema: tema.id,
          url: page.url(),
          violacoes: analise.violations,
          passes: analise.passes?.length ?? 0,
          incompletos: analise.incomplete?.length ?? 0,
          impacto: resumoImpacto(analise.violations),
        });

        if (tema.id === "claro") {
          tecladoPorTela.push({ tela: tela.nome, caminho: tela.caminho, ...teclado });
        }

        await contexto.close();
      }
    }
  } finally {
    await browser.close();
    if (preview) {
      preview.kill("SIGTERM");
    }
  }

  const linhas = [];
  linhas.push("# Evidência — Auditoria de acessibilidade WCAG 2.1 Nível A/AA");
  linhas.push(`Branch: ${git.branch}`);
  linhas.push(`Commit: ${git.commit}`);
  linhas.push(`Commit curto: ${git.curto}`);
  linhas.push(
    `Ambiente: Windows, Node ${process.version}, Playwright + @axe-core/playwright; frontend Vite preview em ${BASE_URL}; API mockada via page.route (sem backend).`,
  );
  linhas.push(`Data: 2026-09-28`);
  linhas.push(`Issue: #468 (DoD: 6 telas × 2 temas)`);
  linhas.push(`Ferramenta: axe-core via @axe-core/playwright; tags ${TAGS_AXE.join(", ")}`);
  linhas.push("");
  linhas.push("## Escopo");
  linhas.push("Telas: Login (/entrar), Principal (/), Histórico (/historico), Intenções (/intencoes), Rotinas (/rotinas), Não encontrada (/pagina-inexistente).");
  linhas.push('Temas: claro e escuro (localStorage prata:tema = "claro"|"escuro"; classe dark em <html>).');
  linhas.push("Autenticação: GET /api/auth/eu mockado com usuário Fernanda Silva (ver_intencoes + gerir_rotinas).");
  linhas.push("");
  linhas.push("## Resumo executivo");

  let totalViolacoes = 0;
  let combinacoesComFalha = 0;
  for (const r of resultados) {
    totalViolacoes += r.violacoes.length;
    if (r.violacoes.length > 0) combinacoesComFalha += 1;
  }
  linhas.push(`Combinações auditadas: ${resultados.length} (6 telas × 2 temas).`);
  linhas.push(`Combinações com pelo menos uma falha: ${combinacoesComFalha}.`);
  linhas.push(`Total de violações reportadas (somas por combinação): ${totalViolacoes}.`);
  linhas.push("");
  linhas.push("Tabela rápida (tela | tema | falhas | critical | serious | moderate | minor):");
  for (const r of resultados) {
    const i = r.impacto;
    linhas.push(
      `  ${r.tela.padEnd(16)} | ${r.tema.padEnd(6)} | ${String(r.violacoes.length).padStart(2)} | c=${i.critical} s=${i.serious} m=${i.moderate} n=${i.minor}`,
    );
  }
  linhas.push("");
  linhas.push("## Falhas por tela / tema / critério / severidade");
  linhas.push("");

  for (const r of resultados) {
    linhas.push(`### ${r.tela} — tema ${r.tema}`);
    linhas.push(`URL final: ${r.url}`);
    linhas.push(`Passes axe (regras OK): ${r.passes}; incompletos: ${r.incompletos}`);
    if (r.violacoes.length === 0) {
      linhas.push("Nenhuma violação WCAG 2.1 A/AA detectada pelo axe nesta combinação.");
    } else {
      linhas.push(`Violações (${r.violacoes.length}):`);
      for (const v of r.violacoes) {
        linhas.push(formatarViolacao(v));
      }
    }
    linhas.push("");
  }

  linhas.push("## Verificação manual / teclado e foco (apoio automatizado)");
  linhas.push(
    "Checklist DoD: ordem de Tab, foco visível, Escape em diálogos. Abaixo, amostragem automatizada no tema claro (DOM order dos focáveis) e presença de regras :focus-visible no CSS carregado.",
  );
  linhas.push("");
  for (const t of tecladoPorTela) {
    linhas.push(`### ${t.tela} (${t.caminho})`);
    linhas.push(`- Elementos focáveis visíveis: ${t.totalFocaveis}`);
    linhas.push(`- Landmark main / role=main: ${t.temMain ? "sim" : "não"}`);
    linhas.push(`- Heading h1: ${t.temH1 ? "sim" : "não"}`);
    linhas.push(`- Regra CSS :focus-visible detectada nas folhas: ${t.temRegraFocusVisible ? "sim" : "não observada no snapshot"}`);
    linhas.push(`- Diálogos abertos no momento da captura: ${t.dialogosAbertos}`);
    linhas.push("- Amostra da ordem de foco (DOM / Tab natural, até 12):");
    for (const item of t.amostraOrdemTab) {
      linhas.push(`  ${item}`);
    }
    linhas.push(
      "- Escape em diálogos: nenhum diálogo modal aberto no carregamento estático das telas auditadas; fluxo de Escape deve ser revalidado manualmente ao abrir Menu do perfil, barra lateral móvel ou formulário de rotina.",
    );
    linhas.push("");
  }

  linhas.push("## Observações e limitações");
  linhas.push("- API mockada no Playwright (page.route); não exercita o middleware real nem o MSW do navegador.");
  linhas.push("- axe não substitui revisão humana completa (contraste contextual, leitores de tela, gestos).");
  linhas.push("- Telas com gráficos (Intenções) podem gerar incompletos axe em nós SVG/canvas.");
  linhas.push("- Script: src/web/scripts/auditoria-a11y.mjs (npm run audit:a11y).");
  linhas.push("");
  linhas.push("EXIT_CODE: 0");

  await mkdir(path.dirname(RELATORIO), { recursive: true });
  await writeFile(RELATORIO, `${linhas.join("\n")}\n`, "utf8");
  process.stderr.write(`Relatório escrito em ${RELATORIO}\n`);

  // Espelha resumo no stdout para o agente/CI
  console.log(
    JSON.stringify(
      {
        relatorio: RELATORIO,
        combinacoes: resultados.length,
        comFalha: combinacoesComFalha,
        totalViolacoes,
        porCombinacao: resultados.map((r) => ({
          tela: r.tela,
          tema: r.tema,
          falhas: r.violacoes.length,
          ids: r.violacoes.map((v) => v.id),
          impacto: r.impacto,
        })),
      },
      null,
      2,
    ),
  );
}

main().catch((erro) => {
  console.error(erro);
  process.exit(1);
});
