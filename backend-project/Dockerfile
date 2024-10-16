FROM python:3.12-slim
USER root

RUN mkdir /backend
WORKDIR /backend
COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm