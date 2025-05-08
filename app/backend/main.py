# app/backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import datetime # Importar datetime
import os       # Importar os
import re       # Importar re para la sanitización de nombres de archivo aquí también

# Importar typing para 'List' y otros
from typing import List, Optional, Dict, Any

# --- Configuración Inicial y Servicios Globales ---
# Es crucial que 'settings' se importe y esté disponible.
try:
    from app.core.config import settings
    if not settings or not settings.OPENAI_API_KEY: # Una verificación temprana
        print("WARN app/backend/main.py: OPENAI_API_KEY en settings es None o vacío al cargar main.py, o settings es None.")
except ImportError as e_conf:
    print(f"ERROR CRITICO en main.py: No se pudo importar 'settings' desde 'app.core.config'. Error: {e_conf}. Asegúrate de que el archivo exista y sea correcto.")
    # Crear un mock de settings para que la app no falle inmediatamente en los imports,
    # pero los servicios que dependen de él probablemente fallarán.
    class SettingsMock: OPENAI_API_KEY = None; GOOGLE_APPLICATION_CREDENTIALS=None; GOOGLE_DRIVE_FOLDER_ID=None; REPORTS_DIR="reports"; CHROMA_DB_PATH="chroma_db_store"
    settings = SettingsMock()


from app.backend.api_models import ResearchAPIRequest, ResearchAPIResponse, ResearchMemoryItem
# Los servicios se instanciarán globalmente al cargar este módulo.
from app.services.gdrive_service import GDriveService
from app.services.persistence_service import PersistenceService

# Importar la función para crear y ejecutar el crew de investigación
try:
    from app.crews.research_crew_definitions import create_research_crew_and_kickoff
except ImportError as e_crew_def:
    print(f"ERROR CRITICO en main.py: No se pudo importar 'create_research_crew_and_kickoff' desde 'app.crews.research_crew_definitions'. Error: {e_crew_def}")
    # Definir una función mock para que la app no falle al definir el endpoint,
    # pero las llamadas al endpoint fallarán.
    def create_research_crew_and_kickoff(topic: str, content_to_analyze: str) -> str:
        # Esta función mock asegura que la app no falle al iniciar si hay un problema con el import,
        # pero cualquier llamada a /research/conduct resultará en este error.
        error_message = "Error crítico: La funcionalidad de investigación principal (Crew) no está disponible debido a un problema de importación previo."
        # Loguear el error si un logger está disponible, o imprimirlo
        # logger.critical(error_message) # Si logger está definido
        print(f"CRITICAL: {error_message}")
        raise ImportError(error_message)


# Configurar logging básico
# Usaremos el logger de Uvicorn (root logger se configurará) si es una app de Uvicorn,
# o un logger estándar si se ejecuta main.py directamente.
logger = logging.getLogger("app.backend.main") # Nombre específico para este módulo
logger.setLevel(logging.INFO) # O logging.DEBUG para más detalle

# --- Instancias de servicios globales (patrón simple para PoC) ---
gdrive_service_instance: Optional[GDriveService] = None
persistence_service_instance: Optional[PersistenceService] = None

try:
    if settings: # Solo intentar si settings se cargó (no es el mock vacío)
        gdrive_service_instance = GDriveService()
        if not gdrive_service_instance or not gdrive_service_instance.service:
            logger.error(f"GDriveService (instancia global) no se inicializó correctamente. Error: {getattr(gdrive_service_instance, 'initialization_error', 'Desconocido o settings no disponibles')}")
except Exception as e_gd_init_global:
    logger.error(f"Excepción CRÍTICA al instanciar GDriveService globalmente: {e_gd_init_global}", exc_info=True)

try:
    if settings:
        persistence_service_instance = PersistenceService()
        if not persistence_service_instance or not persistence_service_instance.collection:
            logger.error(f"PersistenceService (instancia global) no se inicializó correctamente. Error: {getattr(persistence_service_instance, 'initialization_error', 'Desconocido o settings no disponibles')}")
except Exception as e_ps_init_global:
    logger.error(f"Excepción CRÍTICA al instanciar PersistenceService globalmente: {e_ps_init_global}", exc_info=True)


# --- Funciones Depends para FastAPI ---
def get_gdrive_service_dependency() -> Optional[GDriveService]:
    if not gdrive_service_instance or not gdrive_service_instance.service:
        logger.warning("Dependencia: GDriveService no está disponible u operativo al ser solicitado por un endpoint.")
    return gdrive_service_instance

def get_persistence_service_dependency() -> Optional[PersistenceService]:
    if not persistence_service_instance or not persistence_service_instance.collection:
        logger.warning("Dependencia: PersistenceService no está disponible u operativo al ser solicitado por un endpoint.")
    return persistence_service_instance

# --- Aplicación FastAPI ---
app = FastAPI(
    title="Suite de Agentes Inteligentes API - PoC con CrewAI",
    description="API para interactuar con el Agente de Investigación IA orquestado por CrewAI.",
    version="0.2.1" # Pequeño incremento por revisiones
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application startup... Verificando servicios globales.")
    if not settings or not settings.OPENAI_API_KEY:
        logger.critical("Configuración (settings) o OPENAI_API_KEY no disponible. Funcionalidad limitada.")
    
    # Verificar GDriveService
    if gdrive_service_instance and gdrive_service_instance.service:
        logger.info("GDriveService parece estar operativo al inicio.")
    else:
        logger.warning(f"GDriveService NO está operativo al inicio. Error de init: {getattr(gdrive_service_instance, 'initialization_error', 'No instanciado o settings no disponibles') if gdrive_service_instance else 'No instanciado'}")

    # Verificar PersistenceService
    if persistence_service_instance and persistence_service_instance.collection:
        logger.info("PersistenceService (ChromaDB) parece estar operativo al inicio.")
    else:
        logger.warning(f"PersistenceService (ChromaDB) NO está operativo al inicio. Error de init: {getattr(persistence_service_instance, 'initialization_error', 'No instanciado o settings no disponibles') if persistence_service_instance else 'No instanciado'}")
    
    # Verificar la función del Crew (para dar una alerta temprana si falló el import)
    if 'create_research_crew_and_kickoff' not in globals() or not callable(globals().get('create_research_crew_and_kickoff')):
        logger.critical("Función 'create_research_crew_and_kickoff' no está definida correctamente. Los endpoints del crew fallarán.")
    else:
        logger.info("Función 'create_research_crew_and_kickoff' parece estar disponible.")


@app.get("/", tags=["General"])
async def read_root():
    return {"message": "API de la Suite de Agentes Inteligentes con CrewAI funcionando."}

# --- Helper para sanitizar nombres de archivo ---
def _sanitize_filename_for_api(filename_base: str) -> str:
    if not filename_base: return "documento_sin_titulo"
    s = filename_base.replace(' ', '_')
    s = re.sub(r'[^\w.\-]', '', s) 
    s = re.sub(r'_{2,}', '_', s)
    s = re.sub(r'\.{2,}', '.', s)
    s = s.strip('_.')
    if not s: s = "documento_procesado"
    return s[:100]


@app.post("/research/conduct", response_model=ResearchAPIResponse, tags=["Agente de Investigación (CrewAI)"])
async def conduct_research_with_crew_endpoint(
    request: ResearchAPIRequest,
    gdrive_svc: Optional[GDriveService] = Depends(get_gdrive_service_dependency),
    persistence_svc: Optional[PersistenceService] = Depends(get_persistence_service_dependency)
):
    logger.info(f"POST /research/conduct (CrewAI) para tema: '{request.topic[:60]}...'")

    # 1. Ejecutar el Crew de Investigación
    generated_report_content: Optional[str] = None
    try:
        logger.info("Invocando create_research_crew_and_kickoff...")
        generated_report_content = create_research_crew_and_kickoff( # Llama a la función importada
            topic=request.topic,
            content_to_analyze=request.content_to_analyze
        )
        
        if generated_report_content and "Error:" in generated_report_content[:150]:
            logger.error(f"El Crew devolvió un mensaje de error: {generated_report_content}")
            raise HTTPException(status_code=502, detail=f"Error en el procesamiento del agente: {generated_report_content}")

    except ImportError as e_imp_crew: 
        logger.critical(f"No se puede ejecutar la investigación, dependencia 'create_research_crew_and_kickoff' falló al importarse: {e_imp_crew}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error crítico de configuración del servidor: Módulo del Crew no disponible.")
    except Exception as e_crew_exec:
        logger.error(f"Error durante la ejecución de create_research_crew_and_kickoff: {e_crew_exec}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al ejecutar el crew: {str(e_crew_exec)}")

    if not generated_report_content: # Si es None o string vacío
        logger.error("El crew de investigación devolvió un contenido vacío o None, lo cual es inesperado.")
        raise HTTPException(status_code=500, detail="El proceso de investigación no generó un informe (resultado vacío del crew).")

    logger.info(f"Informe generado por el Crew (longitud: {len(generated_report_content)}).")

    # 2. Extraer resumen para la BD vectorial
    report_summary_for_db = "No se pudo extraer el resumen ejecutivo." # Default
    try:
        # Intenta encontrar "## Resumen Ejecutivo" y luego "## Vías de Acción Sugeridas"
        re_summary = re.search(r"## Resumen Ejecutivo\s*(.*?)\s*(?=## Vías de Acción Sugeridas|$)", generated_report_content, re.DOTALL | re.IGNORECASE)
        if re_summary and re_summary.group(1):
            report_summary_for_db = re_summary.group(1).strip()
        else: # Fallback si no se encuentra el patrón exacto
            report_summary_for_db = generated_report_content.split('\n\n', 1)[0] # Primer párrafo como fallback
        report_summary_for_db = report_summary_for_db[:1000] # Limitar longitud
    except Exception as e_parse:
        logger.warning(f"No se pudo parsear el resumen ejecutivo del informe (CrewAI): {e_parse}")
        report_summary_for_db = generated_report_content[:1000]


    # 3. Guardar el informe en Google Drive
    gdrive_link: Optional[str] = None
    gdrive_id: Optional[str] = None
    local_fallback_path: Optional[str] = None

    if not gdrive_svc or not gdrive_svc.service:
        logger.warning("GDriveService no está disponible u operativo. No se guardará el informe en Google Drive.")
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_topic_fn = _sanitize_filename_for_api(request.topic)
        filename = f"InformeCrewAI_{sanitized_topic_fn}_{timestamp}.md"
        
        logger.info(f"Intentando guardar '{filename}' en Google Drive...")
        upload_result = gdrive_svc.upload_text_as_md(generated_report_content, filename)

        if upload_result.get("error"):
            logger.error(f"Error al guardar informe (CrewAI) en Google Drive: {upload_result['error']}")
            current_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            reports_dir_val = settings.REPORTS_DIR if settings else "reports_fallback"
            reports_full_path_val = os.path.join(current_project_root, reports_dir_val)
            os.makedirs(reports_full_path_val, exist_ok=True)
            local_fallback_path = os.path.join(reports_full_path_val, filename)
            try:
                with open(local_fallback_path, "w", encoding="utf-8") as f: f.write(generated_report_content)
                logger.info(f"Informe (CrewAI) guardado como fallback en: {local_fallback_path}")
            except Exception as e_fb_save:
                logger.error(f"Falló guardado local (CrewAI) de fallback para '{local_fallback_path}': {e_fb_save}")
                local_fallback_path = None
        else:
            gdrive_link = upload_result.get("webViewLink")
            gdrive_id = upload_result.get("id")
            logger.info(f"Informe (CrewAI) '{filename}' guardado en Google Drive: {gdrive_link}")

    # 4. Persistir en ChromaDB
    if persistence_svc and persistence_svc.collection and gdrive_id:
        try:
            persistence_svc.add_research_document(
                topic=request.topic, summary=report_summary_for_db,
                gdrive_id=gdrive_id, gdrive_link=gdrive_link or "",
                content_preview=request.content_to_analyze[:500]
            )
            logger.info(f"Metadatos del informe (CrewAI) para '{request.topic[:30]}...' guardados en ChromaDB.")
        except Exception as e_chroma_save:
            logger.error(f"Error guardando metadatos (CrewAI) en ChromaDB: {e_chroma_save}", exc_info=True)
    elif not (persistence_svc and persistence_svc.collection):
         logger.warning("PersistenceService no disponible para guardar metadatos del informe (CrewAI).")
    elif not gdrive_id:
         logger.warning("No hay gdrive_id (GDrive falló o no se usó), no se guardarán metadatos (CrewAI) en ChromaDB.")

    # 5. Consultar memoria para devolver con la respuesta (opcional)
    relevant_past_research_data: List[ResearchMemoryItem] = []
    if persistence_svc and persistence_svc.collection:
        try:
            similar_items = persistence_svc.query_similar_research(f"Investigación sobre {request.topic}", n_results=2)
            if similar_items: relevant_past_research_data = [ResearchMemoryItem(**item) for item in similar_items]
        except Exception as e_mem_final: logger.warning(f"Error consultando memoria para respuesta final: {e_mem_final}")


    return ResearchAPIResponse(
        message="Investigación completada por el Crew de Agentes e informe generado.",
        topic=request.topic,
        report_gdrive_link=gdrive_link,
        report_gdrive_id=gdrive_id,
        report_summary_for_db=report_summary_for_db,
        full_report_content=generated_report_content,
        local_fallback_path=local_fallback_path,
        relevant_past_research=relevant_past_research_data if relevant_past_research_data else [] # Asegurar que sea una lista
    )

@app.get("/research/memory", response_model=List[ResearchMemoryItem], tags=["Memoria de Investigación"])
async def query_research_memory_endpoint(
    query: str,
    persistence_svc: Optional[PersistenceService] = Depends(get_persistence_service_dependency)
):
    logger.info(f"GET /research/memory con query: '{query}'")
    if not persistence_svc or not persistence_svc.collection:
        logger.warning("Intento de consultar memoria, pero PersistenceService no está operativo.")
        raise HTTPException(status_code=503, detail="Servicio de persistencia (ChromaDB) no disponible.")
    
    try:
        similar_items = persistence_svc.query_similar_research(query_text=query, n_results=5)
    except Exception as e_mem_ep:
        logger.error(f"Excepción en persistence_svc.query_similar_research: {e_mem_ep}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor consultando la memoria: {str(e_mem_ep)}")

    if not similar_items: # similar_items puede ser None si la query falló o lista vacía si no hay resultados
        logger.info("Consulta a memoria no devolvió resultados para la query.")
        return [] # Devolver lista vacía si no hay resultados o la función devuelve None
    
    response_items = [ResearchMemoryItem(**item) for item in similar_items]
    logger.info(f"Devolviendo {len(response_items)} items desde la memoria.")
    return response_items

# --- Bloque para ejecución directa (principalmente para desarrollo/prueba rápida sin uvicorn CLI) ---
if __name__ == "__main__":
    # Este bloque se ejecuta cuando haces 'python app/backend/main.py'
    # Es menos común para FastAPI, usualmente se usa 'uvicorn app.backend.main:app --reload'
    logger.info("Ejecutando FastAPI app directamente desde if __name__ == '__main__' (modo de desarrollo).")
    # Configurar un logger básico si no se está corriendo bajo uvicorn (que ya configura root logger)
    if not logging.getLogger().hasHandlers(): # Evitar añadir handlers múltiples si uvicorn ya lo hizo
        logging.basicConfig(level=logging.INFO)
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) # No uses --reload aquí, uvicorn lo maneja diferente cuando se llama así.