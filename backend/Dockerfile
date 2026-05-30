FROM python:3.12-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/usr/local/bin:$PATH
COPY --from=builder /install /usr/local
COPY backend ./backend
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
# /app/uploads must exist and be owned by appuser in the image: when the named
# `uploads` volume is first mounted here it inherits this ownership, so the
# non-root process can write photos. Without it the fresh volume is root-owned
# and uploads fail with PermissionError -> 500.
USER appuser
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
