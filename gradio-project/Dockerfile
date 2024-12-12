FROM python:3.9-slim
USER root

RUN mkdir /app
WORKDIR /app
COPY requirements.txt ./

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 7861
# ENV GRADIO_SERVER_NAME="0.0.0.0"


