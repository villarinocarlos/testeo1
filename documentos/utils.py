from django.template.loader import render_to_string
from xhtml2pdf import pisa
import tempfile
import os
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings
def generar_pdf_xhtml2pdf(alumno, proyecto, empresa):
    """
    Renderiza la plantilla 'carta_template.html' con los datos del alumno, proyecto y empresa,
    y genera un PDF usando xhtml2pdf.
    Retorna la ruta temporal del PDF generado.
    """
    html_string = render_to_string("carta_template.html", {
        "alumno": alumno,
        "proyecto": proyecto,
        "empresa": empresa,
    })
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        pisa_status = pisa.CreatePDF(html_string, dest=output)
        if pisa_status.err:
            raise Exception("Error al generar el PDF con xhtml2pdf.")
        pdf_path = output.name
    return pdf_path


def subir_pdf_a_storage(pdf_path, destino):
    """
    Guarda el PDF ubicado en pdf_path en el almacenamiento local (MEDIA_ROOT)
    y retorna la URL de acceso construida con MEDIA_URL.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, destino)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(pdf_path, "rb") as f:
        file_content = File(f)
        saved_path = default_storage.save(destino, file_content)
    
    url = settings.MEDIA_URL + saved_path
    return url