FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for cryptography (Kalshi RSA auth)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh
# Safety net: fix CRLF line endings if committed from Windows
RUN sed -i 's/\r$//' entrypoint.sh

# Persistent data volume will be mounted here by Fly.io
RUN mkdir -p /data

ENV DB_PATH=/data/gamblai.db
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
