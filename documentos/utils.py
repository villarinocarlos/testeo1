from django.template.loader import render_to_string
from xhtml2pdf import pisa
import tempfile
import os
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings

def generar_pdf_xhtml2pdf(alumno, proyecto, empresa, template_name="carta_aceptacion.html", extra_context=None):
    if extra_context is None:
        extra_context = {}
    context = {
        "alumno": alumno,
        "proyecto": proyecto,
        "empresa": empresa,
    }
    context.update(extra_context)
    
    html_string = render_to_string(template_name, context)
    
    # Usamos un archivo temporal para crear el PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pisa_status = pisa.CreatePDF(html_string, dest=tmp_file)
        tmp_file.flush()
        tmp_file.seek(0)
        pdf_path = tmp_file.name
    
    if pisa_status.err:
        return None
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