# Fase 1: Compilar binario Rust
FROM rust:latest AS builder

WORKDIR /app
COPY servicio_mrcp/ servicio_mrcp/
WORKDIR /app/servicio_mrcp
RUN cargo build --release

# Fase 2: Imagen final con Python y binario Rust
FROM python:3.10-slim

WORKDIR /app

# Copiar binario Rust
COPY --from=builder /app/servicio_mrcp/target/release/mrcp_service servicio_mrcp/mrcp_service

# Copiar archivos necesarios
COPY servidor_websocket2.py .
COPY requirements.txt .

# ✅ Copiar `index.html` desde `servicio_mrcp/static/`
COPY servicio_mrcp/static/ static/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Exponer puertos: HTTP (8080), WebSocket (8000), MRCP (5060)
EXPOSE 8080 8000 5060

# Ejecutar ambos servicios
CMD ["sh", "-c", "./servicio_mrcp/mrcp_service & python servidor_websocket2.py"]
