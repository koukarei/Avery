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
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

CMD ["python", "gradio_app.py"]

