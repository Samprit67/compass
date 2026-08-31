FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY compass ./compass
RUN pip install --no-cache-dir .

EXPOSE 8791

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8791/api/health')"

CMD ["python", "-m", "uvicorn", "compass.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8791"]
