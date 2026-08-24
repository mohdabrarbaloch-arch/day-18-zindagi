FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first for better layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[dev] || pip install --no-cache-dir \
        fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings \
        "python-jose[cryptography]" bcrypt python-multipart slowapi

# Copy application code
COPY app ./app
COPY static ./static
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
