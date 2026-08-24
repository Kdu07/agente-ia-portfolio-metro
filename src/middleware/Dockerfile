# Imagem do middleware. Serve a dois serviços do compose: `middleware`
# (uvicorn) e `worker` (agendador). O que muda entre eles é o `command`,
# não a imagem — mesmo código, gatilhos diferentes.
FROM python:3.12-slim

WORKDIR /app

# Copiado antes do código para que a camada de dependências seja
# reaproveitada quando só a aplicação muda.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
