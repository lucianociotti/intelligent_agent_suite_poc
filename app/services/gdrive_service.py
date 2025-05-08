# app/services/gdrive_service.py
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings # Importa la instancia 'settings'
import os

class GDriveService:
    def __init__(self):
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        self.credentials_path_from_env = settings.GOOGLE_APPLICATION_CREDENTIALS
        self.service = None
        self.initialization_error = None # Para almacenar el error si ocurre

        # La raíz del proyecto, calculada desde la ubicación de ESTE archivo (gdrive_service.py)
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        print(f"DEBUG GDriveService init: Project root = {self.project_root}")
        print(f"DEBUG GDriveService init: Credentials path from env = {self.credentials_path_from_env}")

        # Validar si los paths de credenciales son Nones o vacíos primero
        if not self.credentials_path_from_env:
            self.initialization_error = "La ruta a las credenciales de Google Drive (GOOGLE_APPLICATION_CREDENTIALS) no está configurada en .env."
            print(f"ERROR GDriveService: {self.initialization_error}")
            return # No continuar si no hay ruta de credenciales

        # Construir la ruta absoluta al archivo de credenciales
        # Si la ruta en .env es ya absoluta, os.path.join se comporta bien.
        # Si es relativa, se asume relativa a la raíz del proyecto.
        if os.path.isabs(self.credentials_path_from_env):
            self.absolute_credentials_path = self.credentials_path_from_env
        else:
            self.absolute_credentials_path = os.path.join(self.project_root, self.credentials_path_from_env)
        
        print(f"DEBUG GDriveService init: Absolute credentials path = {self.absolute_credentials_path}")

        if not os.path.exists(self.absolute_credentials_path):
            self.initialization_error = (
                f"Archivo de credenciales de Google Drive no encontrado en '{self.absolute_credentials_path}'. "
                "Verifica la variable GOOGLE_APPLICATION_CREDENTIALS en .env y que el archivo exista en la raíz del proyecto."
            )
            print(f"ERROR GDriveService: {self.initialization_error}")
            return # No continuar si el archivo no existe
        
        if not self.folder_id:
            self.initialization_error = "El ID de la carpeta de Google Drive (GOOGLE_DRIVE_FOLDER_ID) no está configurado en .env."
            print(f"ERROR GDriveService: {self.initialization_error}")
            return

        try:
            self.creds = Credentials.from_service_account_file(
                self.absolute_credentials_path, # Usar la ruta absoluta
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=self.creds)
            print("INFO GDriveService: Servicio de Google Drive inicializado correctamente.")
        except Exception as e:
            self.initialization_error = f"Error al inicializar Google Drive Service: {e}"
            print(f"ERROR GDriveService: {self.initialization_error}")
            # self.service permanece None

    def upload_text_as_md(self, content: str, filename_on_drive: str) -> dict:
        if not self.service:
            error_msg = f"El servicio de Google Drive no está inicializado. Error durante init: {self.initialization_error or 'Desconocido'}"
            print(f"ERROR GDriveService upload: {error_msg}")
            return {"error": error_msg, "id": None, "webViewLink": None}
            
        if not filename_on_drive.endswith(".md"):
            filename_on_drive += ".md"

        # Usar un directorio temporal dentro de 'reports' para el archivo antes de subirlo.
        # Asegurar que 'reports' existe (debería haber sido creado por config.py, pero re-verificar es seguro)
        local_temp_dir = os.path.join(self.project_root, settings.REPORTS_DIR)
        os.makedirs(local_temp_dir, exist_ok=True)
        local_filepath = os.path.join(local_temp_dir, f"temp_{filename_on_drive}")

        try:
            with open(local_filepath, "w", encoding="utf-8") as f:
                f.write(content)

            file_metadata = {
                'name': filename_on_drive,
                'parents': [self.folder_id]
            }
            media = MediaFileUpload(local_filepath, mimetype='text/markdown', resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()
            
            print(f"INFO GDriveService: Archivo '{file.get('name')}' subido a Google Drive con ID: {file.get('id')}")
            
            return {
                "id": file.get('id'),
                "name": file.get('name'),
                "webViewLink": file.get('webViewLink'),
                "webContentLink": file.get('webContentLink'),
                "error": None
            }
        except Exception as e:
            error_msg = f"Error al subir archivo '{filename_on_drive}' a Google Drive: {e}"
            print(f"ERROR GDriveService upload: {error_msg}")
            return {"error": error_msg, "id": None, "webViewLink": None}
        finally:
            # Limpiar archivo temporal después de intentar subir
            if os.path.exists(local_filepath):
                try:
                    os.remove(local_filepath)
                    print(f"DEBUG GDriveService: Archivo temporal '{local_filepath}' eliminado.")
                except Exception as e_clean:
                    print(f"WARN GDriveService: Error limpiando archivo temporal '{local_filepath}': {e_clean}")


if __name__ == '__main__':
    print("DEBUG GDriveService: Ejecutando prueba de GDriveService (main block)...")
    # Este bloque de prueba solo se ejecuta si el archivo se llama directamente
    # python -m app.services.gdrive_service (desde la raíz del proyecto)
    
    # La instancia settings ya debería estar cargada porque el archivo importa desde app.core.config
    if not settings.OPENAI_API_KEY: # Una verificación simple de que settings cargó algo
        print("ERROR GDriveService (main test): Settings no parecen estar cargadas (OPENAI_API_KEY falta). Verifica .env y config.py")
    else:
        print("INFO GDriveService (main test): Settings parecen estar cargadas.")
        try:
            gdrive_service_instance = GDriveService()
            if gdrive_service_instance.service:
                test_content = "# Prueba de Informe desde GDriveService\n\nEste es un informe de prueba generado automáticamente por gdrive_service.py."
                test_filename = f"informe_de_prueba_gdrive_service_main_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                print(f"INFO GDriveService (main test): Intentando subir '{test_filename}'...")
                upload_result = gdrive_service_instance.upload_text_as_md(test_content, test_filename)
                
                if upload_result.get("error"):
                    print(f"ERROR GDriveService (main test): Error en la prueba de subida: {upload_result['error']}")
                else:
                    print("INFO GDriveService (main test): Prueba de subida exitosa:")
                    print(f"  ID: {upload_result.get('id')}")
                    print(f"  Nombre: {upload_result.get('name')}")
                    print(f"  Enlace: {upload_result.get('webViewLink')}")
            elif gdrive_service_instance.initialization_error:
                print(f"ERROR GDriveService (main test): No se pudo inicializar GDriveService para la prueba. Error: {gdrive_service_instance.initialization_error}")
            else:
                print("ERROR GDriveService (main test): GDriveService.service es None, pero no hay initialization_error. Estado inesperado.")

        except Exception as e:
            print(f"ERROR GDriveService (main test): Error inesperado durante la prueba: {e}")
            import traceback
            traceback.print_exc()
    print("DEBUG GDriveService: Fin de la prueba de GDriveService (main block).")