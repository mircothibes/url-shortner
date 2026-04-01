# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Don't use --reload in production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
