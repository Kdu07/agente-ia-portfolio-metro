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
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
