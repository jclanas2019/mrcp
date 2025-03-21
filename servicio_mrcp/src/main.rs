use tokio::net::TcpListener;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_tungstenite::connect_async;
use tungstenite::protocol::Message;
use futures_util::{StreamExt, SinkExt};
use url::Url;
use std::time::Duration;

#[tokio::main]
async fn main() {
    // Iniciar ambos servicios en tareas separadas
    let _mrcp_handle = tokio::spawn(async { start_mrcp_server().await });
    let _ws_handle = tokio::spawn(async { start_websocket_client().await });
    
    // Esperar la señal Ctrl+C para terminar
    tokio::signal::ctrl_c().await.expect("Error al capturar Ctrl+C");
    println!("🛑 Servidor detenido");
}

// Servidor MRCP 
async fn start_mrcp_server() {
    // Intentar iniciar el servidor MRCP con manejo de errores
    match TcpListener::bind("0.0.0.0:5060").await {
        Ok(listener) => {
            println!("✅ MRCP escuchando en 5060");
            
            loop {
                match listener.accept().await {
                    Ok((mut socket, addr)) => {
                        println!("📡 Nueva conexión MRCP desde: {}", addr);
                        
                        // Spawn una tarea para manejar cada conexión
                        tokio::spawn(async move {
                            let mut buffer = [0; 4096];
                            
                            match socket.read(&mut buffer).await {
                                Ok(size) if size > 0 => {
                                    println!("📥 MRCP Recibido ({} bytes): {}", 
                                             size, String::from_utf8_lossy(&buffer[..size]));
                                    
                                    // Responder al cliente
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

// Cliente WebSocket para el motor de voz con sistema de reconexión
async fn start_websocket_client() {
    let url = Url::parse("ws://localhost:8000").unwrap();
    let max_retries = 10;  // Número máximo de intentos
    let retry_interval = Duration::from_secs(2);  // Tiempo entre intentos
    let mut should_continue = true;
    
    println!("🔄 Iniciando cliente WebSocket...");
    
    while should_continue {
        for attempt in 1..=max_retries {
            println!("🔄 Intento de conexión {} de {}", attempt, max_retries);
            
            match connect_async(url.clone()).await {
                Ok((mut ws_stream, response)) => {
                    println!("✅ Conectado al WebSocket del motor de voz");
                    println!("📄 Información de conexión: {:?}", response);
                    
                    // Enviar un mensaje de prueba
                    println!("📤 Enviando mensaje de prueba...");
                    match ws_stream.send(Message::Text(r#"{"texto":"Hola, soy el servidor MRCP", "voz":"es"}"#.into())).await {
                        Ok(_) => println!("📤 Mensaje enviado correctamente"),
                        Err(e) => {
                            println!("❌ Error al enviar mensaje: {}", e);
                            // Si falla el envío, esperamos y continuamos al siguiente intento
                            tokio::time::sleep(retry_interval).await;
                            continue;
                        }
                    }
                    
                    // Esperar y procesar mensajes recibidos
                    println!("👂 Esperando respuestas del servidor...");
                    while let Some(result) = ws_stream.next().await {
                        match result {
                            Ok(msg) => match msg {
                                Message::Text(text) => {
                                    println!("📥 Respuesta del WebSocket: {}", text);
                                    
                                    // Aquí puedes procesar la respuesta JSON si lo necesitas
                                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
                                        if let Some(_audio_data) = json.get("audio_base64") {
                                            println!("🔊 Audio recibido correctamente");
                                            // Aquí podrías guardar o reproducir el audio
                                        }
                                    }
                                },
                                Message::Binary(data) => println!("📥 Datos binarios recibidos: {} bytes", data.len()),
                                Message::Ping(_) => {
                                    println!("📍 Ping recibido, respondiendo con Pong");
                                    if let Err(e) = ws_stream.send(Message::Pong(vec![])).await {
                                        println!("❌ Error al enviar Pong: {}", e);
                                    }
                                },
                                Message::Pong(_) => println!("📍 Pong recibido"),
                                Message::Close(frame) => {
                                    println!("🔴 Conexión cerrada por el servidor: {:?}", frame);
                                    break;
                                },
                                _ => println!("📥 Mensaje desconocido recibido"),
                            },
                            Err(e) => {
                                println!("❌ Error en la conexión WebSocket: {}", e);
                                break;
                            }
                        }
                    }
                    
                    println!("🔄 Conexión WebSocket cerrada, reintentando...");
                    break; // Salir del bucle de intentos, pero seguir en el bucle principal
                },
                Err(e) => {
                    eprintln!("❌ Error al conectar con WebSocket: {}", e);
                    
                    if attempt == max_retries {
                        eprintln!("❌ Se agotaron los intentos de conexión");
                        // Pausa más larga antes de reiniciar
                        tokio::time::sleep(Duration::from_secs(30)).await;
                        // Continuamos el bucle principal después de una pausa larga
                        break;
                    }
                }
            }
            
            // Esperar antes del siguiente intento
            println!("⏳ Esperando {} segundos antes de reintentar...", retry_interval.as_secs());
            tokio::time::sleep(retry_interval).await;
        }
        
        // Solo para evitar un bucle muy intensivo en caso de fallo total
        tokio::time::sleep(Duration::from_secs(1)).await;
    }
}