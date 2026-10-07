/**
 * Testes unitários das funções de execucoes.ts.
 *
 * Cobrem o mapeamento de status de execução para rótulos, ícones e classes.
 */

import { describe, expect, it } from "vitest";

import { STATUS_DE_EXECUCAO } from "@/paginas/Rotinas/execucoes";
import type { StatusExecucao } from "@/tipos";

describe("STATUS_DE_EXECUCAO", () => {
  it("mapeia status sucesso corretamente", () => {
    const status = STATUS_DE_EXECUCAO.sucesso;
    expect(status.rotulo).toBe("Concluída");
    expect(status.classe).toBe("bg-desfecho-ok/10 text-desfecho-ok");
    expect(status.icone).toBeDefined();
  });

  it("mapeia status bloqueada corretamente", () => {
    const status = STATUS_DE_EXECUCAO.bloqueada;
    expect(status.rotulo).toBe("Bloqueada");
    expect(status.classe).toBe("bg-desfecho-injecao/10 text-desfecho-injecao");
    expect(status.icone).toBeDefined();
  });

  it("mapeia status falha corretamente", () => {
    const status = STATUS_DE_EXECUCAO.falha;
    expect(status.rotulo).toBe("Falhou");
    expect(status.classe).toBe("bg-desfecho-falha/10 text-desfecho-falha");
    expect(status.icone).toBeDefined();
  });

  it("mapeia status em_execucao corretamente", () => {
    const status = STATUS_DE_EXECUCAO.em_execucao;
    expect(status.rotulo).toBe("Em execução");
    expect(status.classe).toBe("bg-primario-suave text-primario-texto [&_svg]:motion-safe:animate-spin");
    expect(status.icone).toBeDefined();
  });

  it("contém todos os status esperados", () => {
    const statusEsperados: StatusExecucao[] = ["sucesso", "bloqueada", "falha", "em_execucao"];
    const statusDisponiveis = Object.keys(STATUS_DE_EXECUCAO) as StatusExecucao[];

    statusEsperados.forEach((status) => {
      expect(statusDisponiveis).toContain(status);
    });
  });

  it("cada status tem rotulo definido", () => {
    Object.values(STATUS_DE_EXECUCAO).forEach((status) => {
      expect(status.rotulo).toBeTruthy();
      expect(typeof status.rotulo).toBe("string");
    });
  });

  it("cada status tem icone definido", () => {
    Object.values(STATUS_DE_EXECUCAO).forEach((status) => {
      expect(status.icone).toBeDefined();
      expect(typeof status.icone).toBe("object");
    });
  });

  it("cada status tem classe CSS definida", () => {
    Object.values(STATUS_DE_EXECUCAO).forEach((status) => {
      expect(status.classe).toBeTruthy();
      expect(typeof status.classe).toBe("string");
    });
  });

  it("status em_execucao tem animação de spin", () => {
    const status = STATUS_DE_EXECUCAO.em_execucao;
    expect(status.classe).toContain("animate-spin");
  });

  it("status sucesso usa cores de desfecho ok", () => {
    const status = STATUS_DE_EXECUCAO.sucesso;
    expect(status.classe).toContain("desfecho-ok");
  });

  it("status bloqueada usa cores de desfecho injecao", () => {
    const status = STATUS_DE_EXECUCAO.bloqueada;
    expect(status.classe).toContain("desfecho-injecao");
  });

  it("status falha usa cores de desfecho falha", () => {
    const status = STATUS_DE_EXECUCAO.falha;
    expect(status.classe).toContain("desfecho-falha");
  });

  it("rótulos estão em português e com acentuação correta", () => {
    expect(STATUS_DE_EXECUCAO.sucesso.rotulo).toBe("Concluída");
    expect(STATUS_DE_EXECUCAO.bloqueada.rotulo).toBe("Bloqueada");
    expect(STATUS_DE_EXECUCAO.falha.rotulo).toBe("Falhou");
    expect(STATUS_DE_EXECUCAO.em_execucao.rotulo).toBe("Em execução");
  });
});
