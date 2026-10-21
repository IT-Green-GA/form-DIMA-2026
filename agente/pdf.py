# Generador de PDF para el agente de Telegram.
#
# Produce un documento con encabezado y pie fijos. El encabezado y el pie los
# escribe este modulo, nunca el modelo: asi es imposible que falten.
#
# Encabezado: Arturo Hernandez Hernandez
# Pie:        CHTM GRACIAS

import io
import os
import time

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer)

ENCABEZADO = "Arturo Hernández Hernández"
PIE = "CHTM GRACIAS"

# Carpeta donde se guardan los PDF generados.
CARPETA_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")

ANCHO_MAX_IMAGEN = 15 * cm
# Alto util de la pagina, descontando margenes y el espacio que ocupan el
# encabezado y el pie. Una foto de celular en vertical puede exceder esto.
ALTO_MAX_IMAGEN = 17 * cm


def _estilos():
    """Estilos base del documento."""
    estilos = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=estilos["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=20, spaceAfter=6, alignment=TA_CENTER,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=estilos["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=colors.HexColor("#71717a"),
            alignment=TA_CENTER, spaceAfter=14,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=estilos["Heading2"], fontName="Helvetica-Bold",
            fontSize=11.5, leading=14, textColor=colors.HexColor("#18181b"),
            spaceBefore=10, spaceAfter=4,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=estilos["BodyText"], fontName="Helvetica",
            fontSize=10, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=8,
        ),
    }


def _decorar(canvas, doc, estilos):
    """Dibuja el encabezado en cada pagina y el pie en la ultima.

    El pie se dibuja con un 'callback' que se ejecuta al cerrar el PDF,
    cuando ya se conoce el total de paginas.
    """
    ancho, alto = LETTER

    # Encabezado: presente en todas las paginas.
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColor(colors.HexColor("#18181b"))
    canvas.drawCentredString(ancho / 2, alto - 1.4 * cm, ENCABEZADO)

    canvas.setStrokeColor(colors.HexColor("#d4d4d8"))
    canvas.setLineWidth(0.6)
    canvas.line(2.2 * cm, alto - 1.72 * cm, ancho - 2.2 * cm, alto - 1.72 * cm)
    canvas.restoreState()

    # El pie se difiere: se dibuja al final, en la ultima pagina.
    canvas._pie_pendiente = True


def _dibujar_pie_final(canvas, doc):
    """Se ejecuta al cerrar el documento: dibuja el pie en la ultima pagina."""
    ancho, _ = LETTER
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4d4d8"))
    canvas.setLineWidth(0.6)
    canvas.line(2.2 * cm, 1.75 * cm, ancho - 2.2 * cm, 1.75 * cm)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#18181b"))
    canvas.drawCentredString(ancho / 2, 1.25 * cm, PIE)
    canvas.restoreState()


class _CanvasFinal:
    """Envuelve al canvas de ReportLab para dibujar el pie al cerrar el PDF.

    Cuando el documento termina, se sabe cuantas paginas hubo: ese es el
    momento de dibujar el pie en la ultima.
    """

    def __init__(self, *args, **kwargs):
        self._canvas = canvas.Canvas(*args, **kwargs)
        self._paginas = 0

    def __getattr__(self, nombre):
        return getattr(self._canvas, nombre)

    def showPage(self):
        self._paginas += 1
        self._canvas.showPage()

    def save(self):
        if self._paginas > 0:
            # Ultima pagina: aqui va el pie.
            _dibujar_pie_final(self._canvas, None)
        self._canvas.save()


def generar_pdf(titulo, cuerpo, imagenes=None, ruta_destino=None):
    """Crea el PDF y devuelve la ruta donde se guardo.

    titulo   : texto del titulo del documento
    cuerpo   : texto del cuerpo (puede traer saltos de linea con \\n)
    imagenes : lista de rutas de imagenes a incrustar
    """
    os.makedirs(CARPETA_PDF, exist_ok=True)

    if ruta_destino is None:
        marca = time.strftime("%Y%m%d-%H%M%S")
        ruta_destino = os.path.join(CARPETA_PDF, f"reporte-{marca}.pdf")

    estilos = _estilos()
    documento = SimpleDocTemplate(
        ruta_destino, pagesize=LETTER,
        leftMargin=2.4 * cm, rightMargin=2.4 * cm,
        topMargin=2.4 * cm, bottomMargin=2.6 * cm,
        title=titulo or "Reporte",
        author=ENCABEZADO,
    )

    historia = []

    # Titulo
    if titulo:
        historia.append(Paragraph(_escapar(titulo), estilos["titulo"]))

    # Marca de tiempo
    historia.append(Paragraph(
        f"Generado el {time.strftime('%d/%m/%Y a las %H:%M')}", estilos["subtitulo"]))

    # Cuerpo: se parte en parrafos por linea en blanco.
    bloques = (cuerpo or "").split("\n\n")
    for bloque in bloques:
        texto = bloque.strip()
        if not texto:
            continue
        # Lineas sueltas con "## " se tratan como subtitulo de seccion.
        if texto.startswith("## "):
            historia.append(Paragraph(_escapar(texto[3:].strip()), estilos["seccion"]))
        else:
            historia.append(Paragraph(_escapar(texto), estilos["cuerpo"]))

    # Imagenes
    for ruta in (imagenes or []):
        if not os.path.isfile(ruta):
            continue
        try:
            ancho, alto = _medir_imagen(ruta)
            historia.append(Spacer(1, 8))
            historia.append(Image(ruta, width=ancho, height=alto))
        except Exception as e:  # una imagen mala no debe tumbar el PDF
            historia.append(Paragraph(
                _escapar(f"[No se pudo incrustar la imagen: {e}]"), estilos["cuerpo"]))

    documento.build(
        historia,
        canvasmaker=_CanvasFinal,
        onFirstPage=lambda c, d: _decorar(c, d, estilos),
        onLaterPages=lambda c, d: _decorar(c, d, estilos),
    )
    return ruta_destino


def _medir_imagen(ruta):
    """Calcula el tamano final de la imagen respetando la caja de la pagina.

    Escala por el ancho o por el alto, el que se pase primero. Sin esto, una
    foto vertical de celular desborda la pagina y ReportLab aborta la
    construccion del documento.
    """
    try:
        from PIL import Image as PILImage
        with PILImage.open(ruta) as imagen:
            ancho, alto = imagen.size
    except Exception:
        return ANCHO_MAX_IMAGEN, ANCHO_MAX_IMAGEN / 4

    if ancho <= 0 or alto <= 0:
        return ANCHO_MAX_IMAGEN, ANCHO_MAX_IMAGEN / 4

    escala = min(ANCHO_MAX_IMAGEN / ancho, ALTO_MAX_IMAGEN / alto, 1.0)
    return ancho * escala, alto * escala


def _escapar(texto):
    """Escapa los caracteres especiales de XML que usa ReportLab."""
    return (str(texto)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def listar_pdfs():
    """Devuelve los PDF generados, del mas nuevo al mas viejo."""
    if not os.path.isdir(CARPETA_PDF):
        return []
    archivos = []
    for nombre in os.listdir(CARPETA_PDF):
        if not nombre.lower().endswith(".pdf"):
            continue
        ruta = os.path.join(CARPETA_PDF, nombre)
        try:
            info = os.stat(ruta)
        except OSError:
            continue
        archivos.append({
            "nombre": nombre,
            "ruta": ruta,
            "tamano": info.st_size,
            "fecha": time.strftime("%d/%m/%Y %H:%M", time.localtime(info.st_mtime)),
        })
    archivos.sort(key=lambda a: a["nombre"], reverse=True)
    return archivos
