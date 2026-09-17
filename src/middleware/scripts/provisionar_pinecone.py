"""Script para provisionar o índice Pinecone automaticamente.

Execute: python -m scripts.provisionar_pinecone
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.rag.vetorial.base import VetorialBackend


def main():
    """Provisiona o índice Pinecone se necessário."""
    print("=== Provisionamento do índice Pinecone ===")
    print(f"Backend: {settings.vetorial_backend}")
    print(f"Índice: {settings.pinecone_index}")
    print(f"Namespace: {settings.pinecone_namespace}")

    if settings.vetorial_backend != "pinecone":
        print("⚠️  Backend não é Pinecone. Nada a fazer.")
        return

    if not settings.pinecone_api_key:
        print("❌ PINECONE_API_KEY não configurada. Configure no .env")
        return

    try:
        from app.rag.vetorial.provisionar import criar_indice

        print("🔧 Criando índice Pinecone...")
        criar_indice()
        print("✅ Índice Pinecone criado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar índice: {e}")
        print("💡 Tente manualmente: python -m app.rag.vetorial.provisionar --criar")


if __name__ == "__main__":
    main()
