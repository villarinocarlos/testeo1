1. Instalación y Configuración
 Clonar el Repositorio
Abre una terminal y ejecuta:

git clone https://github.com/villarinocarlos/testeo1.git
cd testeo1
2. Crear y Activar un Entorno Virtual
Es recomendable usar un entorno virtual para evitar conflictos de dependencias.

Editar
# En macOS / Linux
python3 -m venv venv
source venv/bin/activate

# En Windows
python -m venv venv
venv\Scripts\activate

3. Instalar Dependencias
Instala las librerías necesarias con:
 pip install -r requirements.txt

4. Aplicar Migraciones y Ejecutar el Servidor

python manage.py migrate
python manage.py runserver

localhost:8000 o    http://127.0.0.1:8000/