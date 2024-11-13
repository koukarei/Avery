FROM python:3.10.11
USER root

RUN mkdir /backend
WORKDIR /backend
COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt