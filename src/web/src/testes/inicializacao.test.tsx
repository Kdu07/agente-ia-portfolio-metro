import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  iniciarDubles: vi.fn(),
  createRoot: vi.fn(),
  render: vi.fn(),
}));

vi.mock("@/mocks/navegador", () => ({ iniciarDubles: mocks.iniciarDubles }));
vi.mock("react-dom/client", () => ({ createRoot: mocks.createRoot }));

afterEach(() => {
  document.body.replaceChildren();
  vi.resetModules();
});

describe("Inicialização da interface", () => {
  it("só monta a aplicação depois que os dublês assumem a rede", async () => {
    let liberarDubles!: () => void;
    mocks.iniciarDubles.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          liberarDubles = resolve;
        }),
    );
    mocks.createRoot.mockReturnValue({ render: mocks.render });
    document.body.innerHTML = '<div id="raiz"></div>';

    await import("@/main");

    expect(mocks.iniciarDubles).toHaveBeenCalledOnce();
    expect(mocks.createRoot).not.toHaveBeenCalled();

    liberarDubles();
    await vi.waitFor(() => expect(mocks.createRoot).toHaveBeenCalledWith(document.getElementById("raiz")));
    expect(mocks.render).toHaveBeenCalledOnce();
  });
});
