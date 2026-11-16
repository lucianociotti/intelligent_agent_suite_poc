# Intelligent Agent Suite PoC - v0.4.0

Prueba de Concepto (PoC) para una suite de agentes inteligentes colaborativos, diseñados para automatizar tareas de investigación y marketing.

**Arquitectura Principal:**
*   **Backend:** API RESTful con FastAPI.
*   **Frontend:** Interfaz de usuario con Streamlit.
*   **Orquestación de Agentes:** CrewAI.
*   **Modelos IA:** OpenAI GPT-3.5-Turbo (para texto). *(Próximamente DALL-E para imágenes).*
*   **Búsqueda Web:** Tavily Search API.
*   **Almacenamiento Persistente:**
    *   Informes (Investigación): Google Drive.
    *   Memoria Vectorial (resúmenes/metadatos de investigación): ChromaDB (local).

---

## Funcionalidades Implementadas (v0.4.0)

### 1. Flujo de Investigación + Edición
*   Un **Agente Investigador** (`researcher_agent`) recibe un *tema* y opcionalmente *contenido adicional*.
*   Utiliza la herramienta **Tavily Search** para buscar información actualizada en la web.
*   Analiza los resultados de la búsqueda y el contenido adicional (si se proporcionó) usando su LLM base y la herramienta **`ContentAnalysisTool`** para un análisis más profundo.
*   Genera un **borrador** de informe en formato Markdown (Resumen Ejecutivo y Vías de Acción).
*   Un **Agente Editor** (`editor_agent`) recibe el borrador y lo **revisa/pule** para mejorar claridad y estilo.
*   El **informe final editado** se guarda en Google Drive y se referencia en ChromaDB.

### 2. Flujo de Creación de Contenido de Marketing
*   Un **Agente Creador de Contenido de Marketing** (`marketing_content_agent`) recibe un *tema/producto*, una *plataforma* destino (ej. Instagram) y *contexto adicional* opcional.
*   Utiliza las siguientes herramientas basadas en LLM secuencialmente:
    1.  **`Generador de Ideas de Marketing`**: Brainstorming de conceptos, tipos de post, hashtags y CTAs.
    2.  **`Redactor de Posts para Redes Sociales`**: Crea el texto del post adaptado a la plataforma, usando las ideas generadas.
    3.  **`Generador de Prompts para DALL-E`**: Sugiere un prompt detallado para crear una imagen visualmente alineada con el post.
*   El resultado es un conjunto de ideas, el texto del post y un prompt para imagen. *(La generación de imagen se añadirá próximamente).*

### Características Comunes
*   **Interfaz en Streamlit:** Permite iniciar los flujos y ver los resultados.
*   **Memoria (Investigación):** Los informes de investigación se pueden buscar por similitud.

---

## Configuración del Entorno Local

Sigue estos pasos para poner en marcha el proyecto:

1.  **Clona este repositorio:**
    ```bash
    git clone https://github.com/lucianociotti/intelligent_agent_suite_poc.git
    cd intelligent_agent_suite_poc
    ```

2.  **Crea y activa un entorno virtual Python (v3.10+ recomendado):**
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instala/Actualiza Pip e Instala Dependencias:**
    ```bash
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    ```
    *(`requirements.txt` ya usa versiones actualizadas de `crewai`/`crewai-tools` 1.x, que no dependen de `langchain`. Requiere Python 3.10 a 3.13, recomendado 3.11 o superior. Probado: instalación, importación de módulos y armado de agentes con Python 3.10; no se probó contra las APIs reales.)*

4.  **Configura las Variables de Entorno (`.env`):**
    *   Copia `.env.example` a `.env`.
    *   Edita `.env` y añade tus claves/IDs reales para:
        *   `OPENAI_API_KEY="sk-..."`
        *   `GOOGLE_APPLICATION_CREDENTIALS="gdrive_credentials.json"`
        *   `GOOGLE_DRIVE_FOLDER_ID="..."`
        *   `TAVILY_API_KEY="tvly-..."`
    *   Asegúrate de que el archivo `gdrive_credentials.json` (ver paso siguiente) esté en la raíz del proyecto y que `.env` esté en `.gitignore`.

5.  **Configuración de Google Drive API (Cuenta de Servicio):**
    *   (Si aún no lo has hecho)
        1.  Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/).
        2.  Habilita la **Google Drive API**.
        3.  Crea una **Cuenta de Servicio** (IAM y Admin > Cuentas de servicio).
        4.  Descarga su **clave JSON**, renómbrala a `gdrive_credentials.json` y colócala en la raíz del proyecto.
        5.  Obtén el **ID de la Carpeta** de Drive para los informes y configúralo en `.env`.
        6.  **Comparte** esa carpeta de Drive con el email de la cuenta de servicio (con permisos de "Editor").

6.  **Configuración de Tavily Search API:**
    *   Regístrate en [Tavily.com](https://tavily.com/) y obtén tu API Key.
    *   Añádela a `TAVILY_API_KEY` en `.env`.

---

## Ejecución de la Aplicación PoC

Necesitarás dos terminales (con `venv` activado y en la raíz del proyecto).

1.  **Terminal 1: Backend (FastAPI + Uvicorn)**
    ```bash
    uvicorn app.backend.main:app --reload --port 8000
    ```
    *   Verifica `INFO: Application startup complete.` y la carga correcta de agentes/servicios en los logs.

2.  **Terminal 2: Frontend (Streamlit)**
    ```bash
    streamlit run frontend/streamlit_app.py
    ```
    *   Accede a `http://localhost:8501`.

3.  **Uso:**
    *   **Investigación:** Usa la pestaña "🔎 Investigación". Proporciona tema y (opcionalmente) contenido base.
    *   **Marketing:** Usa la pestaña "📢 Marketing Contenido". Proporciona tema, plataforma y (opcionalmente) contexto.
    *   **Memoria:** Usa la pestaña "📚 Memoria" para buscar informes de investigación.

---

## Próximos Pasos Planificados (v0.5+)

*   Integración de generación de imágenes con DALL-E en el flujo de Marketing.
*   Refinamiento de la calidad y profundidad de la investigación (tuning de prompts y herramientas).
*   Desarrollo de Agente de Estrategia de Marketing (análisis de competencia).
*   Mejoras en Logging, UI, y posible contenerización.

---