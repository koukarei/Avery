FROM python:3.10.11
USER root

RUN mkdir /backend
WORKDIR /backend
COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --upgrade stanza torch transformers

# Install OpenJDK-11
RUN apt-get update && \
    apt-get install -y openjdk-11-jdk && \
    apt-get install -y ant && \
    apt-get clean
    
# Set environment variables
ENV TOKENIZERS_PARALLELISM false

# Download Spacy English model
RUN python -m spacy download en_core_web_sm