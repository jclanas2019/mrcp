import asyncio
import websockets
import json
import os
import base64
import tempfile
from gtts import gTTS

async def generar_audio(texto, voz="es"):
    """Genera audio a partir de texto usando Google Text-to-Speech"""
    try:
        # Crear un archivo temporal para guardar el audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generar el audio usando gTTS
        tts = gTTS(text=texto, lang=voz)
        tts.save(temp_path)
        
        # Leer el archivo de audio generado
        with open(temp_path, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Eliminar el archivo temporal
        os.remove(temp_path)
        
        # Convertir a base64 para enviar por WebSocket
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        return {
            "success": True,
            "audio_base64": audio_base64,
            "formato": "mp3"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def responder(websocket):
    """Maneja la conexión WebSocket"""
    print(f"🟢 Cliente conectado desde {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"📥 Mensaje recibido: {message}")
            # Procesar JSON
            try:
                datos = json.loads(message)
                texto = datos.get("texto", "")
                voz = datos.get("voz", "es")
                
                if not texto:
                    respuesta = {"error": "No se proporcionó texto para sintetizar"}
                else:
                    # Generar audio con Google TTS
                    resultado_audio = await generar_audio(texto, voz)
                    respuesta = {
                        "tipo": "tts_respuesta",
                        "texto_original": texto,
                        **resultado_audio
                    }
            except json.JSONDecodeError:
                respuesta = {"error": "JSON inválido"}
            
            await websocket.send(json.dumps(respuesta))
            print(f"📤 Respuesta enviada: {'Audio generado correctamente' if respuesta.get('success', False) else respuesta}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔴 Cliente desconectado ({e.code}): {e.reason}")

async def main():
    """Inicia el servidor WebSocket."""
    print("🔊 Servidor WebSocket con Google TTS iniciado")
    print("🚀 Ejecutándose en ws://localhost:8000")
    
    # Utilizando la API actualizada de websockets
    async with websockets.serve(responder, "localhost", 8000):
        await asyncio.Future()  # Mantener el servidor activo indefinidamente

if __name__ == "__main__":
    asyncio.run(main())