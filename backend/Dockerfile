# Stage 1: Builder
FROM python:3.9-slim as builder
ENV POETRY_VERSION=1.7.1 # Or desired version
RUN pip install "poetry==$POETRY_VERSION"
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
# Create venv and install only production dependencies
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Final image
FROM python:3.9-slim
WORKDIR /app
# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv .venv
# Activate venv
ENV PATH="/app/.venv/bin:$PATH"
COPY . . # Copy your application code
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]