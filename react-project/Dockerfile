FROM node:22.3.0
WORKDIR /code/
# 先にpackage.jsonとpackage-lock.jsonをマウントさせる
COPY package*.json .

RUN npm install
