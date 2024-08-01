FROM python:3.9-slim
USER root

WORKDIR /app
COPY . /app

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/facebookresearch/fastText.git
RUN cd fastText && pip install .
RUN cd ..

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
EXPOSE 7861
# ENV GRADIO_SERVER_NAME="0.0.0.0"


