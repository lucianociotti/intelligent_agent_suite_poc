# app/core/config.py
import os
from dotenv import load_dotenv

# Asegurar que la carga de .env ocurra ANTES de definir Settings
# .env debe estar en la raíz del proyecto (dos niveles arriba de 'core')
project_root_from_config = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root_from_config, '.env')
try:
    load_dotenv(dotenv_path=dotenv_path)
    print(f"DEBUG config.py: .env cargado desde: {dotenv_path}")
except Exception as e_dotenv:
    print(f"WARN config.py: No se pudo cargar .env desde {dotenv_path}. Error: {e_dotenv}")

class Settings:
    # Cargar variables, usar None como default si no existen
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_DRIVE_FOLDER_ID: str | None = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY") # <-- Añadido

    REPORTS_DIR: str = "reports"
    CHROMA_DB_PATH: str = "chroma_db_store"

    # Validaciones/Advertencias al inicio
    if not OPENAI_API_KEY: print("WARN config.py: OPENAI_API_KEY no configurada en .env.")
    if not GOOGLE_APPLICATION_CREDENTIALS: print("WARN config.py: GOOGLE_APPLICATION_CREDENTIALS no configurada en .env.")
    if not GOOGLE_DRIVE_FOLDER_ID: print("WARN config.py: GOOGLE_DRIVE_FOLDER_ID no configurado en .env.")
    if not TAVILY_API_KEY: print("WARN config.py: TAVILY_API_KEY no configurada en .env.") # <-- Añadido

# Instanciar settings DESPUÉS de la definición de la clase
settings = Settings()

# Logging inicial de la configuración cargada (más seguro después de instanciar)
print(f"DEBUG config.py: Settings loaded.")
print(f"  - OpenAI Key: {'Sí' if settings.OPENAI_API_KEY else 'No'}")
print(f"  - GDrive Creds Path: {settings.GOOGLE_APPLICATION_CREDENTIALS or 'No definida'}")
print(f"  - GDrive Folder ID: {settings.GOOGLE_DRIVE_FOLDER_ID or 'No definido'}")
print(f"  - Tavily API Key: {'Sí' if settings.TAVILY_API_KEY else 'No'}") # <-- Añadido

# --- Crear directorios si no existen ---
reports_full_path = os.path.join(project_root_from_config, settings.REPORTS_DIR)
try:
    os.makedirs(reports_full_path, exist_ok=True)
    print(f"DEBUG config.py: Directorio Reports path verificado/creado: {reports_full_path}")
except OSError as e_dir1:
     print(f"ERROR config.py: No se pudo crear el directorio de informes {reports_full_path}. Error: {e_dir1}")

chroma_full_path = os.path.join(project_root_from_config, settings.CHROMA_DB_PATH)
try:
    os.makedirs(chroma_full_path, exist_ok=True)
    print(f"DEBUG config.py: Directorio ChromaDB path verificado/creado: {chroma_full_path}")
except OSError as e_dir2:
     print(f"ERROR config.py: No se pudo crear el directorio de ChromaDB {chroma_full_path}. Error: {e_dir2}")