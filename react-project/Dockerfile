FROM node:22.3.0
WORKDIR /code
# 先にpackage.jsonとpackage-lock.jsonをマウントさせる
COPY ./app/package*.json /code
RUN npm install
