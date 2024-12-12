FROM node:23-bookworm-slim

RUN mkdir /app

WORKDIR /app

# 先にpackage.jsonとpackage-lock.jsonをマウントさせる
COPY package*.json ./
