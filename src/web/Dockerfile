# Build do React e empacotamento dos estaticos no Nginx.
#
# Multi-estagio: o Node existe apenas para buildar. A imagem final nao
# tem runtime JavaScript — e a razao pela qual o projeto tem um unico
# servidor de aplicacao (o Python), e nao dois.

FROM node:20-alpine AS build
WORKDIR /app

# O package-lock.json entra junto e a instalacao usa `npm ci`, nao
# `npm install`: e o lock que garante que a imagem seja construida com
# as mesmas versoes testadas localmente. Com `npm install` sem lock, um
# `^` no package.json faz a imagem receber uma versao mais nova que
# ninguem exercitou.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# Destino do proxy /api. O padrao atende o compose; no Container Apps o
# app recebe o nome do middleware (ver nginx.conf).
ENV API_UPSTREAM=middleware:8000
COPY --from=build /app/dist /usr/share/nginx/html
# Em templates/, e nao em conf.d/: o entrypoint da imagem gera o
# conf.d/default.conf na subida, com ${API_UPSTREAM} ja substituida.
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
