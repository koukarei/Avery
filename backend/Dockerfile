FROM python:3.8-slim
USER root

WORKDIR /usr/src/app
COPY . .
RUN apt-get update && apt-get install -y python3-dev
RUN git clone https://github.com/facebookresearch/fastText.git
RUN cd fastText && pip install .
RUN cd ..

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 8000

CMD ["uvicorn", "main:app","--port=8000","--reload"]