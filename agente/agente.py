# Agente de Telegram que recibe texto, audio e imagenes y genera un PDF.
#
# Flujo:
#   1. Telegram entrega un mensaje (texto, nota de voz o foto).
#   2. El agente descarga los adjuntos y arma un mensaje multimodal.
#   3. Se consulta a OpenRouter con un tool declarado: generar_pdf.
#   4. Si el modelo pide el tool, se genera el PDF con pdf.py y se envia a
#      Telegram con sendDocument.
#
# El encabezado (Arturo Hernandez Hernandez) y el pie (CHTM GRACIAS) los
# escribe pdf.py, no el modelo.
#
# Solo usa la libreria estandar de Python, salvo reportlab para el PDF.

import base64
import json
import mimetypes
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pdf as modulo_pdf

AQUI = os.path.dirname(os.path.abspath(__file__))
API_TELEGRAM = "https://api.telegram.org"
API_IA = "https://openrouter.ai/api/v1/chat/completions"
CARPETA_ADJUNTOS = os.path.join(AQUI, "adjuntos")


def cargar_env():
    """Lee el .env de la carpeta del script sin pisar lo ya exportado."""
    ruta = os.path.join(AQUI, ".env")
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor


def leer_system_prompt():
    """Lee el bloque de texto entre ``` del archivo SYSTEM_PROMPT.md."""
    ruta = os.path.join(AQUI, "SYSTEM_PROMPT.md")
    if not os.path.isfile(ruta):
        return ("Eres un ingeniero mecatronico. Redactas reportes en espanol, "
                "de forma formal y directa.")
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    bloques = re.findall(r"```text\s*(.*?)```", contenido, re.S)
    if bloques:
        return bloques[0].strip()
    return contenido.strip()


cargar_env()

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
OPENROUTER = os.environ.get("OPENROUTER_API_KEY", "").strip()
MODELO = os.environ.get("MODELO", "qwen/qwen3.8-omni-flash").strip()
MODELO_TEXTO = os.environ.get("MODELO_TEXTO", "deepseek/deepseek-v4.1-flash-1017").strip()
PORT = int(os.environ.get("PUERTO", "3000"))
MAX_ORACIONES = int(os.environ.get("MAX_ORACIONES", "3"))
MAX_IMAGENES = int(os.environ.get("MAX_IMAGENES", "3"))

lock = threading.Lock()
ultimo_update = 0
mensajes_web = []

# Tool que el modelo puede pedir para generar el PDF.
TOOL_GENERAR_PDF = {
    "type": "function",
    "function": {
        "name": "generar_pdf",
        "description": (
            "Genera un PDF con el contenido del reporte. Usala cuando el "
            "usuario pida un reporte, un documento, un PDF o que se documente "
            "la informacion recibida."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "titulo": {
                    "type": "string",
                    "description": "Titulo del documento.",
                },
                "cuerpo": {
                    "type": "string",
                    "description": (
                        "Cuerpo del documento. Usa lineas en blanco entre "
                        "parrafos y '## ' al inicio de una linea para un "
                        "subtitulo de seccion."
                    ),
                },
            },
            "required": ["titulo", "cuerpo"],
        },
    },
}


def tg_metodo(metodo, datos=None):
    """Llama a un metodo de la API de Telegram. Devuelve (ok, resultado)."""
    url = f"{API_TELEGRAM}/bot{TOKEN}/{metodo}"
    cuerpo = None
    cabeceras = {}
    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=90) as r:
            respuesta = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")
        return False, f"HTTP {e.code}: {detalle}"
    except Exception as e:
        return False, f"error de red: {e}"
    if not respuesta.get("ok"):
        return False, respuesta.get("description", "error desconocido")
    return True, respuesta.get("result")


def registrar(de, texto):
    """Guarda un mensaje en el historial que muestra la web."""
    with lock:
        mensajes_web.append({
            "de": de,
            "texto": texto,
            "hora": time.strftime("%H:%M:%S"),
        })
        if len(mensajes_web) > 100:
            del mensajes_web[:-100]


def descargar_adjunto(file_id, extension):
    """Descarga un archivo de Telegram y lo guarda en disco.

    Devuelve la ruta local, o None si no se pudo.
    """
    ok, archivo = tg_metodo("getFile", {"file_id": file_id})
    if not ok or not archivo or "file_path" not in archivo:
        print(f"[adjunto] no se pudo obtener: {archivo}", flush=True)
        return None
    url = f"{API_TELEGRAM}/file/bot{TOKEN}/{archivo['file_path']}"
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            datos = r.read()
    except Exception as e:
        print(f"[adjunto] error al descargar: {e}", flush=True)
        return None

    os.makedirs(CARPETA_ADJUNTOS, exist_ok=True)
    nombre = f"{int(time.time() * 1000)}-{os.path.basename(archivo['file_path'])}"
    if extension:
        nombre = os.path.splitext(nombre)[0] + extension
    ruta = os.path.join(CARPETA_ADJUNTOS, nombre)
    with open(ruta, "wb") as f:
        f.write(datos)
    return ruta


def a_data_uri(ruta, tipo_mime):
    """Codifica un archivo local como data URI para el modelo."""
    with open(ruta, "rb") as f:
        datos = f.read()
    return f"data:{tipo_mime};base64," + base64.b64encode(datos).decode()


def a_audio_base64(ruta):
    """Codifica un audio como base64 y devuelve (base64, formato)."""
    extension = os.path.splitext(ruta)[1].lower().lstrip(".")
    formatos = {"ogg": "ogg", "oga": "ogg", "mp3": "mp3", "m4a": "m4a",
                "wav": "wav", "webm": "webm", "opus": "ogg"}
    formato = formatos.get(extension, "ogg")
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode(), formato


def construir_contenido(mensaje):
    """Arma la parte 'content' del mensaje para el modelo.

    Incluye texto, fotos y notas de voz.
    """
    partes = []
    texto = mensaje.get("text") or ""
    if texto:
        partes.append({"type": "text", "text": texto})

    Adjuntos_imagenes = []

    # Fotos (pueden venir como 'photo' con distintos tamanos).
    for foto in mensaje.get("photo") or []:
        if len(Adjuntos_imagenes) >= MAX_IMAGENES:
            break
        ruta = descargar_adjunto(foto["file_id"], ".jpg")
        if ruta:
            Adjuntos_imagenes.append(ruta)
            tipo = mimetypes.guess_type(ruta)[0] or "image/jpeg"
            partes.append({
                "type": "image_url",
                "image_url": {"url": a_data_uri(ruta, tipo)},
            })

    # Nota de voz o audio.
    voz = mensaje.get("voice") or mensaje.get("audio")
    if voz:
        extension = ".ogg" if voz.get("mime_type", "").endswith("ogg") else ".mp3"
        ruta = descargar_adjunto(voz["file_id"], extension)
        if ruta:
            datos, formato = a_audio_base64(ruta)
            partes.append({
                "type": "input_audio",
                "input_audio": {"data": datos, "format": formato},
            })

    # Documento enviado como archivo (por ejemplo un PDF previo).
    documento = mensaje.get("document")
    if documento and len(Adjuntos_imagenes) < MAX_IMAGENES:
        nombre = documento.get("file_name", "")
        if nombre.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            ruta = descargar_adjunto(documento["file_id"], os.path.splitext(nombre)[1])
            if ruta:
                Adjuntos_imagenes.append(ruta)
                tipo = mimetypes.guess_type(ruta)[0] or "image/jpeg"
                partes.append({
                    "type": "image_url",
                    "image_url": {"url": a_data_uri(ruta, tipo)},
                })

    if not partes:
        partes.append({"type": "text", "text": "(mensaje sin contenido textual)"})

    return partes, Adjuntos_imagenes


def consultar_ia(contenido):
    """Llama al modelo con el tool generar_pdf.

    Devuelve (respuesta_texto, peticion_pdf_o_None).
    """
    if not OPENROUTER:
        return "El bot no tiene configurada la llave de OpenRouter.", None

    cuerpo = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": leer_system_prompt()},
            {"role": "user", "content": contenido},
        ],
        "tools": [TOOL_GENERAR_PDF],
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    peticion = urllib.request.Request(
        API_IA,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER}",
            "HTTP-Referer": "https://equipo01.179-236-73-82.sslip.io",
            "X-OpenRouter-Title": "Bot DIMA 2026",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=180) as r:
            respuesta = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")
        return f"No se pudo consultar el modelo (HTTP {e.code}).", None
    except Exception:
        return "No se pudo consultar el modelo: fallo de red.", None

    try:
        mensaje = respuesta["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return "El modelo devolvio una respuesta vacia.", None

    # El modelo pidio el tool: se genera el PDF.
    for llamada in mensaje.get("tool_calls") or []:
        if llamada.get("function", {}).get("name") == "generar_pdf":
            try:
                argumentos = json.loads(llamada["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                argumentos = {}
            return "", {
                "titulo": str(argumentos.get("titulo") or "Reporte"),
                "cuerpo": str(argumentos.get("cuerpo") or ""),
            }

    texto = mensaje.get("content") or ""
    return recortar(texto), None


def recortar(oraciones):
    """Deja como maximo N oraciones."""
    if not oraciones:
        return ""
    partes = [p.strip() for p in re.split(r"(?<=[.!?])\s+", oraciones.strip()) if p.strip()]
    if len(partes) <= MAX_ORACIONES:
        return " ".join(partes)
    return " ".join(partes[:MAX_ORACIONES])


def enviar_pdf(chat_id, datos_pdf, imagenes):
    """Genera el PDF y lo envia a Telegram."""
    try:
        ruta = modulo_pdf.generar_pdf(
            titulo=datos_pdf["titulo"],
            cuerpo=datos_pdf["cuerpo"],
            imagenes=imagenes,
        )
    except Exception as e:
        print(f"[pdf] error al generar: {e}", flush=True)
        tg_metodo("sendMessage", {"chat_id": chat_id,
                                  "text": f"No se pudo generar el PDF: {e}"})
        return None

    with open(ruta, "rb") as f:
        contenido = f.read()

    # Telegram requiere enviar el archivo con multipart/form-data.
    boundary = "----FormBoundary" + os.urandom(8).hex()
    partes = []
    partes.append(f"--{boundary}".encode())
    partes.append(b'Content-Disposition: form-data; name="chat_id"')
    partes.append(b"")
    partes.append(str(chat_id).encode())
    partes.append(f"--{boundary}".encode())
    partes.append(
        f'Content-Disposition: form-data; name="document"; filename="{os.path.basename(ruta)}"'.encode())
    partes.append(b"Content-Type: application/pdf")
    partes.append(b"")
    partes.append(contenido)
    partes.append(f"--{boundary}--".encode())
    cuerpo = b"\r\n".join(partes)

    url = f"{API_TELEGRAM}/bot{TOKEN}/sendDocument"
    peticion = urllib.request.Request(
        url, data=cuerpo,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=180) as r:
            respuesta = json.loads(r.read().decode("utf-8"))
        if respuesta.get("ok"):
            print(f"[pdf] enviado: {ruta}", flush=True)
            return ruta
        print(f"[pdf] Telegram no acepto el archivo: {respuesta}", flush=True)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")
        print(f"[pdf] error al enviar: HTTP {e.code} {detalle}", flush=True)
    except Exception as e:
        print(f"[pdf] error al enviar: {e}", flush=True)
    return None


def procesar_mensaje(chat_id, mensaje, chat_nombre):
    """Atiende un mensaje de Telegram: responde y/o genera el PDF."""
    contenido, imagenes = construir_contenido(mensaje)
    texto_usuario = mensaje.get("text") or "(archivo)"
    print(f"[telegram] {chat_nombre}: {texto_usuario}", flush=True)

    respuesta, peticion_pdf = consultar_ia(contenido)

    if peticion_pdf:
        # El modelo pidio el tool: se genera y envia el PDF.
        registrar("ia", f"Generando PDF: {peticion_pdf['titulo']}")
        ruta = enviar_pdf(chat_id, peticion_pdf, imagenes)
        if ruta:
            registrar("ia", f"PDF generado: {os.path.basename(ruta)}")
            tg_metodo("sendMessage", {
                "chat_id": chat_id,
                "text": f"Listo, generé el PDF \"{peticion_pdf['titulo']}\". "
                        f"Lo tienes en el archivo adjunto y en la web.",
            })
        return

    if respuesta:
        tg_metodo("sendMessage", {"chat_id": chat_id, "text": respuesta})
        registrar("ia", respuesta)


def escuchar_telegram():
    """Revisa Telegram y atiende cada mensaje."""
    global ultimo_update
    ok, _ = tg_metodo("getUpdates", {"offset": -1, "limit": 1})
    if ok:
        ultimo_update = 0

    while True:
        ok, resultado = tg_metodo("getUpdates", {
            "offset": ultimo_update,
            "timeout": 25,
            "allowed_updates": ["message"],
        })
        if not ok:
            print(f"[telegram] {resultado}", flush=True)
            time.sleep(5)
            continue
        for actualizacion in resultado or []:
            ultimo_update = actualizacion["update_id"] + 1
            mensaje = actualizacion.get("message") or {}
            chat = mensaje.get("chat") or {}
            if "id" not in chat:
                continue
            chat_id = str(chat["id"])
            nombre = chat.get("first_name") or "Alguien"

            # Un hilo por chat para no saturar la API.
            hilo = threading.Thread(
                target=procesar_mensaje,
                args=(chat_id, mensaje, nombre),
                daemon=True,
            )
            hilo.start()


class Manejador(BaseHTTPRequestHandler):
    def responder(self, codigo, tipo, cuerpo):
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def servir_estatico(self, ruta):
        base = os.path.join(AQUI, "static")
        nombre = "index.html" if ruta in ("/", "") else ruta.lstrip("/")
        destino = os.path.normpath(os.path.join(base, nombre))
        if not destino.startswith(os.path.normpath(base)):
            return self.responder(403, "text/plain; charset=utf-8", b"Prohibido")
        if not os.path.isfile(destino):
            return self.responder(404, "text/plain; charset=utf-8", b"No encontrado.")
        with open(destino, "rb") as f:
            contenido = f.read()
        tipos = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }
        self.responder(200, tipos.get(os.path.splitext(destino)[1], "application/octet-stream"), contenido)

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path).path

        if ruta == "/api/prompt":
            return self.responder(200, "text/plain; charset=utf-8", leer_system_prompt())

        if ruta == "/api/estado":
            ok, resultado = tg_metodo("getMe")
            estado = {
                "bot": f"@{resultado.get('username', '?')}" if ok else "",
                "conectado": bool(ok),
                "ia": bool(OPENROUTER),
                "modelo": MODELO,
                "max_oraciones": MAX_ORACIONES,
            }
            if not ok:
                estado["error"] = str(resultado)
            if not OPENROUTER:
                estado["error_ia"] = "Falta OPENROUTER_API_KEY en .env"
            return self.responder(200, "application/json; charset=utf-8", estado)

        if ruta == "/api/mensajes":
            with lock:
                copia = list(mensajes_web)
            return self.responder(200, "application/json; charset=utf-8", {"mensajes": copia})

        if ruta == "/api/pdfs":
            return self.responder(200, "application/json; charset=utf-8",
                                  {"pdfs": modulo_pdf.listar_pdfs()})

        # Descarga de un PDF generado.
        if ruta.startswith("/pdfs/"):
            nombre = os.path.basename(ruta)
            destino = os.path.join(modulo_pdf.CARPETA_PDF, nombre)
            if not os.path.isfile(destino):
                return self.responder(404, "text/plain; charset=utf-8", b"No encontrado.")
            with open(destino, "rb") as f:
                contenido = f.read()
            self.responder(200, "application/pdf", contenido)
            return

        self.servir_estatico(ruta)

    def do_POST(self):
        ruta = urllib.parse.urlparse(self.path).path
        largo = int(self.headers.get("Content-Length", "0"))

        if ruta == "/api/limpiar":
            with lock:
                borrados = len(mensajes_web)
                mensajes_web.clear()
            return self.responder(200, "application/json; charset=utf-8",
                                  {"ok": True, "borrados": borrados})

        if ruta != "/api/preguntar":
            return self.responder(404, "text/plain; charset=utf-8", b"No encontrado.")
        try:
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self.responder(400, "application/json; charset=utf-8", {"error": "JSON invalido"})
        pregunta = str(cuerpo.get("pregunta") or "").strip()
        if not pregunta:
            return self.responder(400, "application/json; charset=utf-8", {"error": "Pregunta vacia"})
        if not OPENROUTER:
            return self.responder(503, "application/json; charset=utf-8",
                                  {"error": "El bot no tiene llave de OpenRouter."})
        respuesta, _ = consultar_ia([{"type": "text", "text": pregunta}])
        return self.responder(200, "application/json; charset=utf-8", {"respuesta": respuesta})

    def log_message(self, formato, *args):
        pass  # Silencia el log de cada peticion.


def principal():
    if not TOKEN:
        print("Falta TELEGRAM_TOKEN en el archivo .env", flush=True)
        return
    ok, resultado = tg_metodo("getMe")
    if not ok:
        print(f"El bot no responde: {resultado}", flush=True)
        return
    print(f"Bot @{resultado.get('username')} escuchando en http://0.0.0.0:{PORT}", flush=True)
    if OPENROUTER:
        print(f"IA activa con {MODELO} (texto: {MODELO_TEXTO})", flush=True)
    else:
        print("Sin OPENROUTER_API_KEY: el bot no podra responder", flush=True)
    threading.Thread(target=escuchar_telegram, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Manejador).serve_forever()


if __name__ == "__main__":
    principal()
