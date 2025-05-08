# Intelligent Agent Suite PoC - v0.3

Prueba de Concepto (PoC) para una suite de agentes inteligentes colaborativos, diseñados para automatizar tareas de investigación, marketing y análisis.

**Arquitectura Principal:**
*   **Backend:** API RESTful con FastAPI.
*   **Frontend:** Interfaz de usuario con Streamlit.
*   **Orquestación de Agentes:** CrewAI.
*   **Modelos IA:** Principalmente OpenAI (GPT para texto, DALL-E opcional para imágenes).
*   **Búsqueda Web:** Tavily Search API.
*   **Almacenamiento Persistente:**
    *   Informes: Google Drive.
    *   Memoria Vectorial (resúmenes/metadatos): ChromaDB (local).
*   **Gestión de Dependencias:** Pip y `requirements.txt`.

---

## Funcionalidades Implementadas (v0.3)

*   **Flujo de Investigación + Edición:**
    1.  Un **Agente Investigador** (`researcher_agent`) recibe un *tema* y opcionalmente *contenido adicional*.
    2.  Utiliza la herramienta **Tavily Search** para buscar información actualizada en la web sobre el tema.
    3.  Analiza los resultados de la búsqueda y el contenido adicional (si se proporcionó) usando su LLM base y la herramienta `content_analyzer`.
    4.  Genera un **borrador** de informe en formato Markdown incluyendo un Resumen Ejecutivo y Vías de Acción Sugeridas.
    5.  Un **Agente Editor** (`editor_agent`) recibe el borrador del investigador.
    6.  Utiliza su LLM base para **revisar y pulir** el informe, mejorando claridad, gramática y estilo (sin alterar el contenido fundamental).
    7.  El **informe final editado** es el resultado del proceso.
*   **Integración con Servicios Externos:**
    *   El informe final se guarda automáticamente en una carpeta designada de **Google Drive**.
    *   Un resumen y metadatos del informe se guardan en una base de datos vectorial local **ChromaDB** para permitir búsquedas de similitud posteriores ("Memoria").
*   **Interfaz de Usuario:**
    *   Una interfaz básica en **Streamlit** permite:
        *   Iniciar nuevas investigaciones (proporcionando tema y opcionalmente contenido).
        *   Ver el informe final generado.
        *   Consultar la memoria (ChromaDB) por investigaciones anteriores relevantes.

---

## Configuración del Entorno Local

Sigue estos pasos para poner en marcha el proyecto en tu máquina:

1.  **Clona este repositorio:**
    ```bash
    git clone https://github.com/lucianociotti/intelligent_agent_suite_poc.git
    cd intelligent_agent_suite_poc
    ```

2.  **Crea y activa un entorno virtual:**
    *Se recomienda Python 3.10 o superior.*
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```
    *Verás `(venv)` al inicio de tu prompt.*

3.  **Instala las dependencias:**
    *Asegúrate de que tu archivo `requirements.txt` contenga las versiones fijadas (como `crewai==0.28.8`, `pydantic==2.6.1`, etc.) que resolvieron los conflictos.*
    ```bash
    pip install -r requirements.txt
    ```
    *(Opcional recomendado)* Actualiza pip: `python -m pip install --upgrade pip`

4.  **Configura las Variables de Entorno:**
    *   Copia el archivo `.env.example` a un nuevo archivo llamado `.env` en la raíz del proyecto.
        ```bash
        # Windows:
        copy .env.example .env
        # macOS/Linux:
        cp .env.example .env
        ```
    *   **Edita el archivo `.env`** y añade tus claves y IDs reales:
        ```env
        OPENAI_API_KEY="sk-..." # Tu clave de API de OpenAI
        GOOGLE_APPLICATION_CREDENTIALS="gdrive_credentials.json" # Nombre (o ruta) de tu archivo de credenciales JSON
        GOOGLE_DRIVE_FOLDER_ID="..." # El ID de la carpeta en Google Drive para guardar informes
        TAVILY_API_KEY="tvly-..." # Tu clave de API de Tavily Search
        ```
    *   **¡Importante!** Asegúrate de que el archivo `.env` esté listado en tu `.gitignore`.

5.  **Configuración de Google Drive API (Cuenta de Servicio):**
    *   Si aún no lo has hecho, sigue estos pasos cruciales:
        1.  Ve a [Google Cloud Console](https://console.cloud.google.com/) y selecciona/crea un proyecto.
        2.  Habilita la **Google Drive API**.
        3.  Ve a "IAM y administración" > "Cuentas de servicio" y **Crea una Cuenta de Servicio**.
        4.  **Descarga la clave** de esta cuenta en formato **JSON**.
        5.  **Renombra el archivo JSON descargado** a `gdrive_credentials.json` (o el nombre que pusiste en `.env`) y **colócalo en la raíz de este proyecto**. (¡Asegúrate de que esté en `.gitignore`!).
        6.  Crea/elige una carpeta en tu Google Drive personal para los informes. Obtén su **ID de Carpeta** (la parte final de la URL) y ponlo en `GOOGLE_DRIVE_FOLDER_ID` en tu `.env`.
        7.  **COMPARTE** esa carpeta de Google Drive con la **dirección de correo electrónico de la cuenta de servicio** que creaste (ej. `nombre-cuenta@tu-proyecto.iam.gserviceaccount.com`), dándole permisos de **"Editor"**.

6.  **Configuración de Tavily Search API:**
    *   Ve a [Tavily.com](https://tavily.com/), regístrate y obtén tu API Key.
    *   Añade la clave a tu archivo `.env` bajo la variable `TAVILY_API_KEY`.

---

## Ejecución de la Aplicación PoC

Necesitarás dos terminales separadas, ambas con el entorno virtual (`venv`) activado y en la raíz del proyecto (`intelligent_agent_suite_poc/`).

1.  **Terminal 1: Iniciar Backend (FastAPI con Uvicorn)**
    ```bash
    uvicorn app.backend.main:app --reload --port 8000
    ```
    *   Observa la salida. Busca `INFO: Application startup complete.` y asegúrate de que no haya errores críticos durante la inicialización de los servicios (GDrive, ChromaDB) o la carga de los agentes/crews.

2.  **Terminal 2: Iniciar Frontend (Streamlit)**
    ```bash
    streamlit run frontend/streamlit_app.py
    ```
    *   Esto debería abrir automáticamente la interfaz web en tu navegador (`http://localhost:8501`).

3.  **Uso:**
    *   Usa la pestaña "🔎 Nueva Investigación" en la interfaz de Streamlit.
    *   Proporciona un "Tema Principal".
    *   *(Opcional)* Proporciona "Contenido Base (Input)" si quieres que se analice junto con la búsqueda web.
    *   Haz clic en "🚀 Iniciar Investigación y Generar Informe".
    *   Observa la salida en la interfaz y el informe generado (enlace a Google Drive).
    *   Revisa los logs de Uvicorn (Terminal 1) para ver la actividad detallada de los agentes de CrewAI.
    *   Usa la pestaña "📚 Consultar Memoria" para buscar informes anteriores guardados en ChromaDB.

---

## Próximos Pasos Planificados

*   Implementación del Agente de Marketing de Contenidos.
*   Implementación del Agente de Estrategia de Marketing.
*   Integración de análisis de competencia (scraping/APIs).
*   Publicación/Programación en redes sociales.
*   Mejoras en Logging, manejo de errores y UI.
*   Autenticación de usuarios.

---