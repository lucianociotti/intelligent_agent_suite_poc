# Intelligent Agent Suite Poc

Prueba de Concepto para una Suite de Agentes Inteligentes.

## Configuración Inicial

1.  **Clona este repositorio (si aplica).**
2.  **Crea y activa un entorno virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configura las variables de entorno:**
    *   Copia `.env.example` a `.env`.
    *   Edita `.env` con tus claves y rutas:
        *   `OPENAI_API_KEY`: Tu clave de API de OpenAI.
        *   `GOOGLE_APPLICATION_CREDENTIALS`: Ruta al archivo JSON de credenciales de tu cuenta de servicio de Google Cloud. Este archivo debe existir en la ruta especificada. Colócalo preferiblemente en la raíz del proyecto (e.g., `gdrive_credentials.json`) y asegúrate de que esté en `.gitignore`.
        *   `GOOGLE_DRIVE_FOLDER_ID`: El ID de la carpeta en Google Drive donde se guardarán los informes. Para obtenerlo, abre la carpeta en Google Drive y copia la última parte de la URL (después de 'folders/').

5.  **Configuración de Google Drive API:**
    *   Ve a [Google Cloud Console](https://console.cloud.google.com/).
    *   Crea un nuevo proyecto o selecciona uno existente.
    *   Habilita la API de **Google Drive** para tu proyecto.
    *   Ve a 'IAM y administración' > 'Cuentas de servicio'.
    *   Crea una cuenta de servicio. Asígnale un nombre (ej. 'agente-investigacion-gdrive').
    *   Descarga la clave de la cuenta de servicio en formato JSON. Renombra este archivo a `gdrive_credentials.json` (o el nombre que pongas en `GOOGLE_APPLICATION_CREDENTIALS`) y colócalo en la raíz de tu proyecto.
    *   Crea una carpeta en tu Google Drive donde se guardarán los informes. Abre la carpeta, y su ID es la parte final de la URL. Copia este ID.
    *   **Importante:** Comparte esta carpeta de Google Drive con la dirección de correo electrónico de la cuenta de servicio que creaste (la encontrarás en los detalles de la cuenta de servicio, ej. `nombre-cuenta@tu-proyecto.iam.gserviceaccount.com`). Dale permisos de 'Editor'.

## Ejecución

1.  **Iniciar el Backend (FastAPI):**
    ```bash
    # Desde la raíz del proyecto '{project_name}'
    uvicorn app.backend.main:app --reload --port 8000
    ```
2.  **Iniciar el Frontend (Streamlit):**
    En otra terminal:
    ```bash
    # Desde la raíz del proyecto '{project_name}'
    streamlit run frontend/streamlit_app.py
    ```
    Esto abrirá la interfaz en `http://localhost:8501`.

3.  **Prueba por consola (Opcional):**
    ```bash
    # Desde la raíz del proyecto '{project_name}'
    python app/agents/research_agent.py
    ```
    (Asegúrate de que la sección `if __name__ == '__main__':` en `research_agent.py` esté configurada para una prueba útil).
