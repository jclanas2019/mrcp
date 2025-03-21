import asyncio
import websockets
import json
import os
import base64
import tempfile
from gtts import gTTS

# Importaciones para LangChain y Ollama
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import aiohttp

# Base de conocimiento - documentación técnica de sistemas de refrigeración industrial
BASE_CONOCIMIENTO = [
    {
        "id": "DOC001",
        "titulo": "Manual de sensores de temperatura para sistemas de refrigeración industrial",
        "descripcion": "Guía completa de selección, instalación y mantenimiento de sensores de temperatura.",
        "url": "https://www.ejemplo.com/manuales/sensores-temperatura.pdf",
        "keywords": ["sensor", "temperatura", "termostato", "RTD", "termopar", "PT100", "-50", "calibración"]
    },
    {
        "id": "DOC002",
        "titulo": "Procedimiento de mantenimiento de evaporadores industriales",
        "descripcion": "Protocolo para inspección, limpieza y mantenimiento preventivo de evaporadores.",
        "url": "https://www.ejemplo.com/procedimientos/mantenimiento-evaporadores.pdf",
        "keywords": ["evaporador", "escarcha", "hielo", "deshielo", "ventilador", "aletas", "serpentín"]
    },
    {
        "id": "DOC003",
        "titulo": "Guía de diagnóstico de fallos en compresores",
        "descripcion": "Identificación y resolución de problemas comunes en compresores industriales.",
        "url": "https://www.ejemplo.com/guias/diagnostico-compresores.pdf",
        "keywords": ["compresor", "bitzer", "vibración", "ruido", "presión", "aceite", "sobrecalentamiento"]
    },
    {
        "id": "DOC004",
        "titulo": "Configuración de protocolos MQTT para monitorización IIoT",
        "descripcion": "Implementación de comunicación MQTT en sistemas de refrigeración industrial.",
        "url": "https://www.ejemplo.com/configuracion/mqtt-refrigeracion.pdf",
        "keywords": ["MQTT", "protocolo", "comunicación", "broker", "tópico", "suscripción", "publicación"]
    },
    {
        "id": "DOC005",
        "titulo": "Estándares HACCP para cadenas de frío",
        "descripcion": "Implementación de HACCP en procesos de refrigeración industrial para alimentos.",
        "url": "https://www.ejemplo.com/normativas/haccp-refrigeracion.pdf",
        "keywords": ["HACCP", "cadena de frío", "seguridad alimentaria", "punto crítico", "monitoreo", "temperatura", "registro"]
    },
    {
        "id": "DOC006",
        "titulo": "Optimización de eficiencia energética en condensadores",
        "descripcion": "Métodos para reducir el consumo energético en sistemas de condensación.",
        "url": "https://www.ejemplo.com/eficiencia/condensadores.pdf",
        "keywords": ["condensador", "eficiencia", "energía", "consumo", "kW", "ventilador", "presión", "subenfriamiento"]
    },
    {
        "id": "DOC007",
        "titulo": "Implementación de sistemas SCADA para refrigeración industrial",
        "descripcion": "Guía para integración de sistemas SCADA en plantas de refrigeración.",
        "url": "https://www.ejemplo.com/sistemas/scada-refrigeracion.pdf",
        "keywords": ["SCADA", "HMI", "monitoreo", "control", "automatización", "supervisión", "alarma"]
    },
    {
        "id": "DOC008",
        "titulo": "Guía de refrigerantes industriales",
        "descripcion": "Propiedades, aplicaciones y manejo seguro de refrigerantes industriales.",
        "url": "https://www.ejemplo.com/guias/refrigerantes.pdf",
        "keywords": ["refrigerante", "amoniaco", "freón", "R404A", "R717", "carga", "presión", "temperatura"]
    },
    {
        "id": "DOC009",
        "titulo": "Manual de válvulas de expansión",
        "descripcion": "Selección, instalación y diagnóstico de válvulas de expansión.",
        "url": "https://www.ejemplo.com/manuales/valvulas-expansion.pdf",
        "keywords": ["válvula", "expansión", "termostática", "electrónica", "sobrecalentamiento", "subenfriamiento"]
    },
    {
        "id": "DOC010",
        "titulo": "Procedimientos de emergencia ante fugas de refrigerante",
        "descripcion": "Protocolos de seguridad ante fugas de refrigerantes industriales.",
        "url": "https://www.ejemplo.com/seguridad/fugas-refrigerante.pdf",
        "keywords": ["fuga", "emergencia", "seguridad", "detector", "evacuación", "protección", "amoniaco"]
    }
]

def buscar_documentos_relevantes(texto, max_docs=3):
    """Busca documentos relevantes basados en palabras clave en el texto"""
    # Convertir texto a minúsculas para búsqueda insensible a mayúsculas
    texto_lower = texto.lower()
    
    # Calcular relevancia para cada documento
    docs_relevancia = []
    for doc in BASE_CONOCIMIENTO:
        relevancia = 0
        for keyword in doc["keywords"]:
            if keyword.lower() in texto_lower:
                relevancia += 1
                
        if relevancia > 0:
            docs_relevancia.append({
                "documento": doc,
                "relevancia": relevancia
            })
    
    # Ordenar por relevancia y limitar al número máximo
    docs_relevancia.sort(key=lambda x: x["relevancia"], reverse=True)
    docs_seleccionados = [item["documento"] for item in docs_relevancia[:max_docs]]
    
    return docs_seleccionados

class AsyncOllama:
    """Clase para manejar llamadas asíncronas a Ollama"""
    def __init__(self, model_name="gemma3", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
    async def generate(self, prompt):
        """Genera una respuesta usando Ollama API de forma asíncrona"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        error = await response.text()
                        print(f"Error de Ollama: {error}")
                        return f"Error al procesar tu consulta. Por favor, intenta de nuevo más tarde."
            except Exception as e:
                print(f"Error de conexión con Ollama: {e}")
                return f"No se pudo conectar con el modelo de IA. Asegúrate de que Ollama está ejecutándose con el modelo gemma3."

async def procesar_con_langchain(texto):
    """Procesa el texto usando LangChain y Ollama con un prompt especializado en IIoT para refrigeración"""
    try:
        # Definir el PromptTemplate para sistemas IIoT de refrigeración industrial
        template = """
        # INSTRUCCIONES PARA EL ASISTENTE DE SOPORTE TÉCNICO DE SISTEMAS IIOT DE REFRIGERACIÓN INDUSTRIAL
        
        Eres FRÍO-BOT, un asistente virtual especializado en sistemas IIoT (Internet Industrial de las Cosas) para la monitorización y mantenimiento de cadenas de frío en refrigeración industrial. Tu propósito es proporcionar soporte técnico preciso, profesional y efectivo a técnicos, operadores e ingenieros que trabajan con estos sistemas.
        
        ## TU CONOCIMIENTO ESPECIALIZADO INCLUYE:
        - Sensores de temperatura, humedad y presión en sistemas de refrigeración industrial
        - Protocolos de comunicación industrial: Modbus, OPC-UA, MQTT, BACnet
        - Sistemas SCADA y plataformas de monitoreo para cadenas de frío
        - Normativas HACCP, ISO 22000 y regulaciones sobre cadenas de frío
        - Análisis de datos, tendencias y predicción de fallos en compresores, evaporadores y condensadores
        - Mantenimiento preventivo y correctivo de sistemas de refrigeración
        - Alertas y notificaciones en caso de desviaciones de temperatura
        - Eficiencia energética en sistemas de refrigeración industrial
        
        ## CUANDO RESPONDAS:
        1. Analiza si la consulta está relacionada con: diagnóstico de problemas, configuración de equipos, interpretación de datos, mantenimiento preventivo o normativas.
        2. Usa terminología técnica adecuada para profesionales del sector.
        3. Prioriza la seguridad del sistema y la preservación de la cadena de frío.
        4. Sé conciso pero completo, respetando los protocolos industriales.
        5. Cuando sea apropiado, pregunta por datos específicos como: lecturas de sensores, modelos de equipos o registros de alarmas.
        6. Incluye referencias a posibles parámetros críticos que deben verificarse.
        7. No debes usar formato markdown
        
        ## CONSULTA DEL USUARIO:
        {input}
        
        ## RESPUESTA TÉCNICA:
        """
        
        prompt = PromptTemplate(template=template, input_variables=["input"])
        
        # Instanciar el cliente Ollama asíncrono
        ollama_async = AsyncOllama(model_name="gemma3")
        
        # Preparar el prompt completo
        prompt_final = prompt.format(input=texto)
        
        # Generar respuesta del modelo
        respuesta = await ollama_async.generate(prompt_final)
        
        return respuesta.strip()
    except Exception as e:
        print(f"Error procesando con LangChain: {e}")
        return f"Lo siento, hubo un error al procesar tu consulta técnica: {str(e)}"

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
                use_ai = datos.get("use_ai", True)  # Opción para usar o no la IA
                
                if not texto:
                    respuesta = {"error": "No se proporcionó texto para procesar"}
                    await websocket.send(json.dumps(respuesta))
                    continue
                
                # Buscar documentos relevantes en la base de conocimiento
                documentos_relevantes = buscar_documentos_relevantes(texto)
                
                # Procesar con IA si está habilitado
                texto_procesado = texto
                if use_ai:
                    print(f"🧠 Procesando consulta técnica con IA: {texto}")
                    texto_procesado = await procesar_con_langchain(texto)
                    print(f"🧠 Respuesta técnica de IA: {texto_procesado}")
                
                # Generar audio con el texto procesado
                resultado_audio = await generar_audio(texto_procesado, voz)
                respuesta = {
                    "tipo": "tts_respuesta",
                    "texto_original": texto,
                    "texto_procesado": texto_procesado,
                    "documentos": documentos_relevantes,  # Agregar documentos relevantes a la respuesta
                    **resultado_audio
                }
                
                await websocket.send(json.dumps(respuesta))
                print(f"📤 Respuesta enviada: {'Audio generado correctamente' if respuesta.get('success', False) else respuesta}")
                
                if documentos_relevantes:
                    print(f"📚 Documentos relevantes encontrados: {len(documentos_relevantes)}")
                    for doc in documentos_relevantes:
                        print(f"   - {doc['titulo']}")
            
            except json.JSONDecodeError:
                respuesta = {"error": "JSON inválido"}
                await websocket.send(json.dumps(respuesta))
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔴 Cliente desconectado ({e.code}): {e.reason}")

async def main():
    """Inicia el servidor WebSocket."""
    print("🔊 Asistente IIoT de Refrigeración Industrial - Servidor iniciado")
    print("🧊 FRÍO-BOT: Sistema de soporte técnico para cadenas de frío")
    print("📚 Base de conocimiento cargada con", len(BASE_CONOCIMIENTO), "documentos")
    print("🚀 Ejecutándose en ws://localhost:8000")
    
    # Comprobar que Ollama está disponible
    try:
        ollama = AsyncOllama()
        test_response = await ollama.generate("Prueba de conexión")
        print(f"✅ Ollama está funcionando correctamente")
    except Exception as e:
        print(f"⚠️ No se pudo conectar con Ollama: {e}")
        print("⚠️ Asegúrate de que Ollama está instalado y ejecutándose")
        print("⚠️ También verifica que el modelo 'gemma3' está disponible en Ollama")
        print("⚠️ Puedes instalarlo con: ollama pull gemma3")
        print("⚠️ El servidor continuará, pero las funciones de IA no funcionarán")
    
    # Utilizando la API actualizada de websockets
    async with websockets.serve(responder, "localhost", 8000):
        await asyncio.Future()  # Mantener el servidor activo indefinidamente

if __name__ == "__main__":
    asyncio.run(main())