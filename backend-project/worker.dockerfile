FROM python:3.10

WORKDIR /app

# Copy your requirements file
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire backend directory
COPY . .