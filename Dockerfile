FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1

CMD ["./docker-entrypoint.sh"]