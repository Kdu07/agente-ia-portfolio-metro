# Imagem do middleware. Serve a dois serviços do compose: `middleware`
# (uvicorn) e `worker` (agendador). O que muda entre eles é o `command`,
# não a imagem — mesmo código, gatilhos diferentes.
FROM python:3.12-slim

# Sem buffer, o log chega ao Log Analytics na hora, e não quando o buffer
# do Python enche. HF_HOME fixa onde o modelo mora, para que o download do
# build e a leitura na subida apontem para o mesmo diretório.
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf

WORKDIR /app

# Valida duracao, decodificacao e presenca exclusiva de trilha de audio
# antes de consumir a franquia do Azure Speech.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiado antes do código para que a camada de dependências seja
# reaproveitada quando só a aplicação muda.
COPY pyproject.toml ./
# sentence-transformers aceita o torch CPU já instalado e deixa de puxar
# os enormes wheels CUDA para uma imagem que não usa GPU.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "torch>=2.2"
RUN pip install --no-cache-dir ".[rag]"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large')"

# Daqui em diante o modelo é só leitura: a réplica não consulta o Hugging
# Face ao subir, e fica pronta sem depender da rede nem do limite do hub.
# AQUECER_MODELOS carrega o classificador na subida (ver app/main.py).
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    AQUECER_MODELOS=true

COPY app ./app
COPY dados ./dados
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
