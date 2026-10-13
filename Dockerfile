FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONNUNBUFFERED=1

COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock.txt

COPY . .
