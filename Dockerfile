FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalacje systemowe + uv przeniesione do /usr/local/bin
RUN apt-get update && apt-get install -y curl build-essential \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie projektu
COPY . .

# Instalacja zależności przez uv
RUN uv sync --frozen
RUN uv run python manage.py collectstatic --noinput
EXPOSE 8002

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8002", "timeloggingproject.wsgi:application"]
