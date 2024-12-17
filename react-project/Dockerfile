FROM node:23-bookworm-slim

WORKDIR /usr/src/app

# RUN mkdir /app

# WORKDIR /app

# 先にpackage.jsonとpackage-lock.jsonをマウントさせる
COPY app/package.json ./

CMD ["npm", "install"]
