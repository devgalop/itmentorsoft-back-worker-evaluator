FROM python:3.12-alpine3.20

WORKDIR /app

# Install git (required to clone dependencies from requirements.txt)
RUN apk add --no-cache git

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
