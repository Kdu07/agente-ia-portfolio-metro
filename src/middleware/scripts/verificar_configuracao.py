"""Script para verificar configurações do .env

Execute: python -m scripts.verificar_configuracao
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def verificar_configuracao():
    """Verifica se as configurações essenciais estão presentes."""
    print("=== Verificacao de Configuracao ===\n")

    problemas = []
    avisos = []

    # Verificações obrigatórias
    if not settings.session_secret:
        problemas.append("[X] SESSION_SECRET nao configurado")
    else:
        print("[OK] SESSION_SECRET configurado")

    if not settings.database_url:
        problemas.append("[X] DATABASE_URL nao configurado")
    else:
        print("[OK] DATABASE_URL configurado")

    # Verificações do Entra ID
    if not settings.entra_tenant_id:
        problemas.append("[X] ENTRA_TENANT_ID nao configurado")
    else:
        print("[OK] ENTRA_TENANT_ID configurado")

    if not settings.entra_client_id:
        problemas.append("[X] ENTRA_CLIENT_ID nao configurado")
    else:
        print("[OK] ENTRA_CLIENT_ID configurado")

    if not settings.entra_client_secret:
        problemas.append("[X] ENTRA_CLIENT_SECRET nao configurado")
    else:
        print("[OK] ENTRA_CLIENT_SECRET configurado")

    # Verificações do executor
    print(f"\n[INFO] Executor configurado: {settings.executor}")

    if settings.executor == "copilot":
        if not settings.directline_secret:
            problemas.append("[X] DIRECTLINE_SECRET nao configurado (necessario para executor copilot)")
        else:
            print("[OK] DIRECTLINE_SECRET configurado")

    elif settings.executor == "proprio":
        print("[INFO] Executor proprio (RAG) selecionado")

        if not settings.pinecone_api_key:
            problemas.append("[X] PINECONE_API_KEY nao configurado (necessario para executor proprio)")
        else:
            print("[OK] PINECONE_API_KEY configurado")

        if not settings.gemini_api_key:
            problemas.append("[X] GEMINI_API_KEY nao configurado (necessario para executor proprio)")
        else:
            print("[OK] GEMINI_API_KEY configurado")

        # Verifica arquivo de credenciais do Drive
        drive_creds = Path(settings.drive_service_account_json)
        if not drive_creds.exists():
            avisos.append(f"[!] Arquivo de credenciais do Drive nao encontrado: {settings.drive_service_account_json}")
        else:
            print(f"[OK] Arquivo de credenciais do Drive encontrado")

    # Verificações opcionais
    if not settings.content_safety_endpoint:
        avisos.append("[!] CONTENT_SAFETY_ENDPOINT nao configurado (opcional)")
    if not settings.content_safety_key:
        avisos.append("[!] CONTENT_SAFETY_KEY nao configurado (opcional)")

    # Resumo
    print("\n" + "="*50)
    if problemas:
        print("\n[X] PROBLEMAS ENCONTRADOS:")
        for problema in problemas:
            print(f"  {problema}")
        print("\n[!] Configure as variaveis acima no arquivo .env")
    else:
        print("\n[OK] Todas as configuracoes obrigatorias estao presentes!")

    if avisos:
        print("\n[!] AVISOS (opcional):")
        for aviso in avisos:
            print(f"  {aviso}")

    if not problemas:
        print("\n[OK] Voce pode iniciar o projeto!")
        print("   Docker: docker compose -f infra/docker-compose.yml up --build")
        print("   Local: cd src/middleware && .venv\\Scripts\\uvicorn app.main:app --reload")

    return len(problemas) == 0


if __name__ == "__main__":
    sucesso = verificar_configuracao()
    sys.exit(0 if sucesso else 1)
