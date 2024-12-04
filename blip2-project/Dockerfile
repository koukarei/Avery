FROM python:3.9-slim

COPY requirements.txt ./

# Install dependencies
RUN pip install -r requirements.txt

RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 && \
    apt-get clean