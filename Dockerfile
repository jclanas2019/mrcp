# Fase de compilación con Rust
FROM rust:latest AS builder

WORKDIR /app

# Copiar el código fuente
COPY servicio_mrcp/ servicio_mrcp/

# Compilar el servicio MRCP
WORKDIR /app/servicio_mrcp
RUN cargo build --release

# Fase de ejecución con Python
FROM python:3.10

WORKDIR /app

# Copiar binario compilado
COPY --from=builder /app/servicio_mrcp/target/release/mrcp_service servicio_mrcp/mrcp_service

# Copiar el resto de archivos
COPY . .

# Instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Exponer los puertos
EXPOSE 5060 8000 8080

# Ejecutar MRCP, WebSocket y el servidor HTTP
CMD ["sh", "-c", "./servicio_mrcp/mrcp_service & python servidor_websocket2.py"]
