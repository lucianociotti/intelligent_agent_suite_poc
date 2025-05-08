# app/core/config.py
import os
from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env que está en la raíz del proyecto
# (un nivel arriba de 'app', dos niveles arriba de 'core')
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Para Google Drive
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    # Directorios (relativos a la raíz del proyecto)
    REPORTS_DIR: str = "reports"
    CHROMA_DB_PATH: str = "chroma_db_store"

    # Validación básica de configuraciones críticas
    if not OPENAI_API_KEY:
        print("ADVERTENCIA: La variable de entorno OPENAI_API_KEY no está configurada en .env.")
        # raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.") # Podrías hacerlo fallar si prefieres
    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("ADVERTENCIA: La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada en .env.")
    # No podemos verificar la existencia del archivo aquí de forma fiable si la ruta es solo el nombre,
    # ya que la 'raíz del proyecto' se determina mejor en tiempo de ejecución desde la raíz.
    # Esta verificación se hace mejor al instanciar el GDriveService o al inicio de la app.
    if not GOOGLE_DRIVE_FOLDER_ID:
        print("ADVERTENCIA: La variable de entorno GOOGLE_DRIVE_FOLDER_ID no está configurada en .env.")


settings = Settings()
print(f"DEBUG config.py: Settings cargadas. OPENAI_API_KEY is set: {bool(settings.OPENAI_API_KEY)}")
print(f"DEBUG config.py: GOOGLE_APPLICATION_CREDENTIALS: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
print(f"DEBUG config.py: GOOGLE_DRIVE_FOLDER_ID: {settings.GOOGLE_DRIVE_FOLDER_ID}")


# --- Crear directorios si no existen (relativos a la raíz del proyecto) ---
# Estas rutas se resuelven desde la ubicación de este archivo config.py
project_root_from_config = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
print(f"DEBUG config.py: Project root (desde config.py) = {project_root_from_config}")


reports_full_path = os.path.join(project_root_from_config, settings.REPORTS_DIR)
if not os.path.exists(reports_full_path):
    os.makedirs(reports_full_path, exist_ok=True)
    print(f"DEBUG config.py: Directorio de informes creado/verificado en: {reports_full_path}")

chroma_full_path = os.path.join(project_root_from_config, settings.CHROMA_DB_PATH)
if not os.path.exists(chroma_full_path):
    os.makedirs(chroma_full_path, exist_ok=True)
    print(f"DEBUG config.py: Directorio de ChromaDB creado/verificado en: {chroma_full_path}")

# NO establezcas os.environ['GOOGLE_APPLICATION_CREDENTIALS'] aquí globalmente de esta forma.
# Es mejor que la librería de Google lo resuelva a partir de la variable de entorno
# o que se pase explícitamente al crear las credenciales si es necesario.
# Si el archivo gdrive_credentials.json está en la raíz Y GOOGLE_APPLICATION_CREDENTIALS="gdrive_credentials.json"
# la librería cliente de Google debería encontrarlo si el directorio de trabajo es la raíz del proyecto.
