use tokio::net::TcpListener;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_tungstenite::connect_async;
use tungstenite::protocol::Message;
use futures_util::{StreamExt, SinkExt};
use url::Url;
use std::time::Duration;
use hyper::{Body, Request, Response, Server, StatusCode};
use hyper::service::{make_service_fn, service_fn};
use std::fs;
use std::net::SocketAddr;
use std::path::PathBuf;
use mime_guess::from_path;

#[tokio::main]
async fn main() {
    let _mrcp_handle = tokio::spawn(async { start_mrcp_server().await });
    let _ws_handle = tokio::spawn(async { start_websocket_client().await });
    let _http_handle = tokio::spawn(async { start_http_server().await });

    tokio::signal::ctrl_c().await.expect("Error al capturar Ctrl+C");
    println!("🛑 Servidor detenido");
}

async fn start_mrcp_server() {
    match TcpListener::bind("0.0.0.0:5060").await {
        Ok(listener) => {
            println!("✅ MRCP escuchando en 5060");
            loop {
                match listener.accept().await {
                    Ok((mut socket, addr)) => {
                        println!("📡 Nueva conexión MRCP desde: {}", addr);
                        tokio::spawn(async move {
                            let mut buffer = [0; 4096];
                            match socket.read(&mut buffer).await {
                                Ok(size) if size > 0 => {
                                    println!("📥 MRCP Recibido ({} bytes): {}", size, String::from_utf8_lossy(&buffer[..size]));
                                    if let Err(e) = socket.write_all(b"MRCP/2.0 200 OK\r\n\r\n").await {
                                        eprintln!("❌ Error al responder: {}", e);
                                    }
                                },
                                Ok(_) => println!("⚠️ Conexión MRCP cerrada por el cliente"),
                                Err(e) => eprintln!("❌ Error al leer de la conexión MRCP: {}", e),
                            }
                        });
                    },
                    Err(e) => eprintln!("❌ Error al aceptar conexión MRCP: {}", e),
                }
            }
        },
        Err(e) => {
            eprintln!("❌ Error al iniciar servidor MRCP: {}", e);
        }
    }
}

async fn start_websocket_client() {
    let url = Url::parse("ws://localhost:8000").unwrap();
    let max_retries = 10;
    let retry_interval = Duration::from_secs(2);

    println!("🔄 Iniciando cliente WebSocket...");

    for attempt in 1..=max_retries {
        println!("🔄 Intento de conexión {} de {}", attempt, max_retries);
        match connect_async(url.clone()).await {
            Ok((mut ws_stream, response)) => {
                println!("✅ Conectado al WebSocket");
                println!("📄 Información de conexión: {:?}", response);

                let mensaje = r#"{"texto":"Hola, soy el servidor MRCP", "voz":"es"}"#;
                if let Err(e) = ws_stream.send(Message::Text(mensaje.into())).await {
                    println!("❌ Error al enviar mensaje: {}", e);
                }
                break;
            },
            Err(e) => {
                eprintln!("❌ Error al conectar WebSocket: {}", e);
                tokio::time::sleep(retry_interval).await;
            }
        }
    }
}

async fn start_http_server() {
    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("🌐 Servidor HTTP escuchando en http://{}", addr);

    let base_path = PathBuf::from("/app/static"); // 📌 Ajuste para Docker

    let make_svc = make_service_fn(move |_conn| {
        let base_path = base_path.clone();
        async move {
            Ok::<_, hyper::Error>(service_fn(move |req: Request<Body>| {
                let base_path = base_path.clone();
                async move {
                    println!("📌 [HTTP] {} {}", req.method(), req.uri().path());

                    let path = if req.uri().path() == "/" {
                        base_path.join("index.html")
                    } else {
                        base_path.join(req.uri().path().trim_start_matches('/'))
                    };

                    let path_display = path.to_string_lossy().to_string();

                    match fs::read(&path) {
                        Ok(contents) => {
                            let mime = from_path(&path).first_or_octet_stream();
                            println!("✅ [HTTP] 200 OK - Sirviendo archivo: {}", path_display);
                            Ok::<_, hyper::Error>(Response::builder()
                                .status(StatusCode::OK)
                                .header("Content-Type", mime.to_string())
                                .body(Body::from(contents))
                                .unwrap())
                        }
                        Err(_) => {
                            println!("❌ [HTTP] 404 Not Found - Archivo no encontrado: {}", path_display);
                            Ok::<_, hyper::Error>(Response::builder()
                                .status(StatusCode::NOT_FOUND)
                                .body(Body::from("Archivo no encontrado"))
                                .unwrap())
                        }
                    }
                }
            }))
        }
    });

    if let Err(e) = Server::bind(&addr).serve(make_svc).await {
        eprintln!("❌ Error en servidor HTTP: {}", e);
    }
}
