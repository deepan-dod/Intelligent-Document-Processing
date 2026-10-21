FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
# Primary OCR engine (large download). Build with: --build-arg WITH_PADDLE=1
ARG WITH_PADDLE=0
RUN if [ "$WITH_PADDLE" = "1" ]; then pip install --no-cache-dir paddlepaddle paddleocr; fi
COPY . .
EXPOSE 5000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:5000/health')"
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "--timeout", "300", "app:create_app()"]
