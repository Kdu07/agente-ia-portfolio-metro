import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Principal } from "@/paginas/Principal";

afterEach(cleanup);

describe("Página principal", () => {
  it("abre os detalhes de uma notificação de pendência", () => {
    render(<Principal />);

    expect(screen.getByRole("dialog", { name: "Notificação do assistente" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver detalhes" }));

    expect(screen.queryByRole("dialog", { name: "Notificação do assistente" })).not.toBeInTheDocument();
    expect(screen.getByText(/Entrega da Fase 2.*está atrasado/)).toBeInTheDocument();
  });

  it("indica quando a entrada por voz está ativa", () => {
    render(<Principal />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar entrada por voz" }));

    expect(screen.getByRole("button", { name: "Parar entrada por voz" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox", { name: "Mensagem" })).toHaveAttribute("placeholder", "Ouvindo... fale agora");
  });
});
