# Imagem do middleware. Serve a dois serviços do compose: `middleware`
# (uvicorn) e `worker` (agendador). O que muda entre eles é o `command`,
# não a imagem — mesmo código, gatilhos diferentes.
FROM python:3.12-slim

WORKDIR /app

# Copiado antes do código para que a camada de dependências seja
# reaproveitada quando só a aplicação muda.
COPY pyproject.toml ./
# sentence-transformers aceita o torch CPU já instalado e deixa de puxar
# os enormes wheels CUDA para uma imagem que não usa GPU.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "torch>=2.2"
RUN pip install --no-cache-dir ".[rag]"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large')"

COPY app ./app
COPY dados ./dados
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
