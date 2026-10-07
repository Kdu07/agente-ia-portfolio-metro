import { cleanup, fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  Avatar,
  AvatarBadge,
  AvatarFallback,
  AvatarGroup,
  AvatarGroupCount,
} from "@/componentes/ui/avatar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/componentes/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/componentes/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/componentes/ui/dropdown-menu";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/componentes/ui/drawer";
import { Separator } from "@/componentes/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/componentes/ui/sheet";
import { renderizar } from "./utilitarios";

afterEach(cleanup);

describe("componentes Avatar", () => {
  it("exibe alternativa acessível e contador para um grupo", () => {
    renderizar(
      <AvatarGroup>
        <Avatar size="sm">
          <AvatarFallback>CR</AvatarFallback>
          <AvatarBadge aria-label="Disponível" />
        </Avatar>
        <AvatarGroupCount>+2</AvatarGroupCount>
      </AvatarGroup>,
    );

    expect(screen.getByText("CR")).toBeInTheDocument();
    expect(screen.getByLabelText("Disponível")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
  });
});

describe("Separator", () => {
  it("expõe orientação vertical a tecnologias assistivas", () => {
    renderizar(<Separator orientation="vertical" decorative={false} />);

    expect(screen.getByRole("separator")).toHaveAttribute("aria-orientation", "vertical");
  });
});

describe("Sheet", () => {
  it("abre o painel e fecha pelo controle acessível", async () => {
    const usuario = userEvent.setup();
    renderizar(
      <Sheet>
        <SheetTrigger asChild>
          <button type="button">Abrir painel</button>
        </SheetTrigger>
        <SheetContent side="left">
          <SheetHeader>
            <SheetTitle>Preferências</SheetTitle>
            <SheetDescription>Configurações da conta</SheetDescription>
          </SheetHeader>
          <SheetFooter>Alterações salvas</SheetFooter>
        </SheetContent>
      </Sheet>,
    );

    await usuario.click(screen.getByRole("button", { name: "Abrir painel" }));
    expect(await screen.findByRole("dialog", { name: "Preferências" })).toBeInTheDocument();
    expect(screen.getByText("Configurações da conta")).toBeInTheDocument();
    expect(screen.getByText("Alterações salvas")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Drawer", () => {
  it("apresenta o conteúdo e fecha por ação explícita", async () => {
    renderizar(
      <Drawer>
        <DrawerTrigger asChild>
          <button type="button">Abrir gaveta</button>
        </DrawerTrigger>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Detalhes</DrawerTitle>
            <DrawerDescription>Resumo do item selecionado</DrawerDescription>
          </DrawerHeader>
          <DrawerFooter>
            <DrawerClose asChild>
              <button type="button">Concluir</button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Abrir gaveta" }));
    expect(await screen.findByRole("dialog", { name: "Detalhes" })).toBeInTheDocument();
    expect(screen.getByText("Resumo do item selecionado")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Concluir" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("DropdownMenu", () => {
  it("altera opções e navega em um submenu", async () => {
    const usuario = userEvent.setup();
    const onSelecionar = vi.fn();
    renderizar(
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button type="button">Abrir opções</button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel inset>Exibição</DropdownMenuLabel>
          <DropdownMenuGroup>
            <DropdownMenuCheckboxItem checked={false} onCheckedChange={onSelecionar}>
              Mostrar concluídas
            </DropdownMenuCheckboxItem>
            <DropdownMenuRadioGroup value="lista" onValueChange={onSelecionar}>
              <DropdownMenuRadioItem value="lista">Lista</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive">
            Excluir
            <DropdownMenuShortcut>Del</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger inset>Mais opções</DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              <DropdownMenuItem>Duplicar</DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>,
    );

    await usuario.click(screen.getByRole("button", { name: "Abrir opções" }));
    expect(await screen.findByText("Exibição")).toBeInTheDocument();
    await usuario.click(screen.getByRole("menuitemcheckbox", { name: "Mostrar concluídas" }));
    expect(onSelecionar).toHaveBeenCalledWith(true);
    await usuario.click(screen.getByRole("button", { name: "Abrir opções" }));
    await usuario.click(screen.getByRole("menuitem", { name: "Mais opções" }));
    expect(await screen.findByRole("menuitem", { name: "Duplicar" })).toBeInTheDocument();
  });
});

describe("Dialog e AlertDialog", () => {
  it("confirma uma ação destrutiva e oferece cancelamento acessível", async () => {
    const usuario = userEvent.setup();
    const confirmar = vi.fn();
    renderizar(
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <button type="button">Excluir registro</button>
        </AlertDialogTrigger>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogMedia aria-hidden="true">!</AlertDialogMedia>
            <AlertDialogTitle>Confirmar exclusão</AlertDialogTitle>
            <AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmar}>Excluir</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>,
    );

    await usuario.click(screen.getByRole("button", { name: "Excluir registro" }));
    expect(await screen.findByRole("alertdialog", { name: "Confirmar exclusão" })).toBeInTheDocument();
    expect(screen.getByText("Esta ação não pode ser desfeita.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Excluir registro" }));
    await usuario.click(await screen.findByRole("button", { name: "Excluir" }));
    expect(confirmar).toHaveBeenCalledOnce();
  });

  it("fecha o diálogo comum após a ação do rodapé", async () => {
    const usuario = userEvent.setup();
    renderizar(
      <Dialog>
        <DialogTrigger asChild>
          <button type="button">Abrir diálogo</button>
        </DialogTrigger>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Editar perfil</DialogTitle>
            <DialogDescription>Atualize seus dados.</DialogDescription>
          </DialogHeader>
          <DialogFooter showCloseButton>Formulário</DialogFooter>
        </DialogContent>
      </Dialog>,
    );

    await usuario.click(screen.getByRole("button", { name: "Abrir diálogo" }));
    expect(await screen.findByRole("dialog", { name: "Editar perfil" })).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
