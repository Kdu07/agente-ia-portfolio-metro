import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  Avatar,
  AvatarBadge,
  AvatarFallback,
  AvatarGroup,
  AvatarGroupCount,
  AvatarImage,
} from "@/componentes/ui/avatar";
import { Separator } from "@/componentes/ui/separator";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("Elementos visuais compartilhados", () => {
  it("renderiza avatar, fallback, imagem, badge e contagem de grupo", () => {
    renderizar(
      <AvatarGroup>
        <Avatar size="sm">
          <AvatarImage src="/avatar.png" alt="Pessoa" />
          <AvatarFallback>PS</AvatarFallback>
          <AvatarBadge data-testid="avatar-badge" />
        </Avatar>
        <AvatarGroupCount>+2</AvatarGroupCount>
      </AvatarGroup>,
    );

    expect(document.querySelector('[data-slot="avatar-group"]')).toBeInTheDocument();
    expect(screen.getByText("PS")).toBeInTheDocument();
    expect(screen.getByTestId("avatar-badge")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("expõe separadores horizontais e verticais com suas orientações", () => {
    renderizar(
      <>
        <Separator decorative={false} />
        <Separator decorative={false} orientation="vertical" />
      </>,
    );

    expect(screen.getAllByRole("separator")).toHaveLength(2);
    expect(screen.getAllByRole("separator")[0]).toHaveAttribute("data-orientation", "horizontal");
    expect(screen.getAllByRole("separator")[1]).toHaveAttribute("data-orientation", "vertical");
  });
});
