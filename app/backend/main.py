# app/backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging # Usar logging en lugar de print para el backend
from typing import List, Optional, Dict, Any # <--- ASEGÚRATE QUE 'List' ESTÉ AQUÍ

# Asegurarse de que la config se cargue y esté disponible ANTES que otros módulos de 'app'
try:
    from app.core.config import settings
    print(f"DEBUG main.py: Settings cargadas desde app.core.config. OPENAI_API_KEY is set: {bool(settings.OPENAI_API_KEY)}")
except ImportError as e:
    print(f"ERROR CRITICO en main.py: No se pudo importar 'settings' desde 'app.core.config'. Error: {e}. ¿Está app/core/config.py presente y correcto?")
    settings = None # Para evitar más errores si la importación falla
except AttributeError as e_attr:
    print(f"ERROR CRITICO en main.py: 'settings' importado pero falta un atributo (ej. .env no leído bien). Error: {e_attr}")
    settings = None


from app.backend.api_models import ResearchAPIRequest, ResearchAPIResponse, ResearchMemoryItem
from app.agents.research_agent import ResearchAgent
from app.services.gdrive_service import GDriveService
from app.services.persistence_service import PersistenceService

# Configurar logging básico
logging.basicConfig(level=logging.INFO) # Cambia a logging.DEBUG para más detalle
logger = logging.getLogger(__name__)

# --- Instancias de servicios (Singleton pattern simple para PoC) ---
# Se crean una vez cuando el módulo se carga.
# Para producción, considera patrones de inyección de dependencias más avanzados.
try:
    gdrive_service_instance = GDriveService()
    if not gdrive_service_instance.service:
        logger.error(f"GDriveService no se inicializó correctamente. Error: {gdrive_service_instance.initialization_error}")
        # No lanzar excepción aquí, permitir que la app inicie pero el endpoint falle si se usa GDrive.
except Exception as e_gd_init:
    logger.error(f"Excepción CRÍTICA al inicializar GDriveService globalmente: {e_gd_init}")
    gdrive_service_instance = None # Marcar como no disponible

try:
    persistence_service_instance = PersistenceService()
    if not persistence_service_instance.collection:
        logger.error(f"PersistenceService no se inicializó correctamente. Error: {persistence_service_instance.initialization_error}")
except Exception as e_ps_init:
    logger.error(f"Excepción CRÍTICA al inicializar PersistenceService globalmente: {e_ps_init}")
    persistence_service_instance = None

try:
    if gdrive_service_instance and persistence_service_instance : # Solo si ambos están ok (o al menos instanciados)
        research_agent_instance = ResearchAgent(
            gdrive_service=gdrive_service_instance,
            persistence_service=persistence_service_instance
        )
        logger.info("ResearchAgent instanciado globalmente.")
    else:
        research_agent_instance = None
        logger.error("ResearchAgent no pudo ser instanciado globalmente porque GDriveService o PersistenceService fallaron.")
except Exception as e_ra_init:
    logger.error(f"Excepción CRÍTICA al inicializar ResearchAgent globalmente: {e_ra_init}")
    research_agent_instance = None

# --- Funciones Depends para FastAPI (mejora para obtener instancias) ---
def get_gdrive_service_dependency():
    if not gdrive_service_instance or not gdrive_service_instance.service:
        logger.error("Dependencia: GDriveService no disponible o no inicializado correctamente.")
        # Aquí podrías lanzar HTTPException si el servicio es absolutamente crítico para el endpoint
        # raise HTTPException(status_code=503, detail="Servicio de Google Drive no disponible.")
    return gdrive_service_instance

def get_persistence_service_dependency():
    if not persistence_service_instance or not persistence_service_instance.collection:
        logger.error("Dependencia: PersistenceService no disponible o no inicializado correctamente.")
    return persistence_service_instance

def get_research_agent_dependency():
    if not research_agent_instance:
        logger.error("Dependencia: ResearchAgent no disponible (falló la instanciación global).")
        # Debería lanzar error si el agente es necesario para el endpoint.
        raise HTTPException(status_code=503, detail="Servicio del Agente de Investigación no disponible.")
    return research_agent_instance

# --- Aplicación FastAPI ---
app = FastAPI(
    title="Suite de Agentes Inteligentes API - PoC",
    description="API para interactuar con el Agente de Investigación IA y otros futuros agentes.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cambiar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application startup...")
    if not settings:
        logger.critical("Las configuraciones (settings) no están disponibles al inicio de la app. Revisa config.py y .env.")
    if not gdrive_service_instance or not gdrive_service_instance.service:
        logger.warning("GDriveService no está operativo al inicio de la aplicación.")
    if not persistence_service_instance or not persistence_service_instance.collection:
        logger.warning("PersistenceService (ChromaDB) no está operativo al inicio de la aplicación.")
    if not research_agent_instance:
         logger.warning("ResearchAgent no está operativo al inicio de la aplicación.")


@app.get("/", tags=["General"])
async def read_root():
    return {"message": "Bienvenido a la API de la Suite de Agentes Inteligentes."}

@app.post("/research/conduct", response_model=ResearchAPIResponse, tags=["Agente de Investigación"])
async def conduct_research_endpoint(
    request: ResearchAPIRequest,
    agent: ResearchAgent = Depends(get_research_agent_dependency), # Usar la nueva dependencia
    persistence_svc: PersistenceService = Depends(get_persistence_service_dependency) # Para memoria
):
    logger.info(f"Recibida petición /research/conduct para el tema: {request.topic}")

    # Verificar servicios críticos obtenidos por Depends
    if not agent: # Redundante si get_research_agent_dependency lanza error, pero seguro.
        raise HTTPException(status_code=503, detail="Agente de Investigación no está disponible.")
    if not agent.gdrive_service or not agent.gdrive_service.service :
        logger.error("GDriveService no está disponible dentro del ResearchAgent al procesar la solicitud.")
        raise HTTPException(status_code=503, detail="Servicio crítico de Google Drive no operativo.")

    relevant_past_research_data = []
    if persistence_svc and persistence_svc.collection:
        try:
            query_for_memory = f"Información o investigación sobre {request.topic}"
            logger.debug(f"Consultando memoria con: '{query_for_memory}'")
            similar_items = persistence_svc.query_similar_research(query_for_memory, n_results=2)
            if similar_items:
                for item in similar_items:
                    relevant_past_research_data.append(ResearchMemoryItem(**item))
                logger.info(f"Encontrados {len(relevant_past_research_data)} items relevantes en memoria.")
        except Exception as e_mem_query:
            logger.error(f"Error consultando la memoria de investigación: {e_mem_query}")
            # No detener la investigación principal por esto, solo loguear.
    
    try:
        result = agent.conduct_research(topic=request.topic, content_to_analyze=request.content_to_analyze)
    except Exception as e_conduct:
        logger.error(f"Excepción no manejada durante agent.conduct_research: {e_conduct}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar la investigación: {e_conduct}")


    if result.get("error"):
        logger.error(f"Error devuelto por el agente: {result['error']}")
        # Adaptar el código de estado si es posible. Ej. si es error de OpenAI -> 502, GDrive -> 503
        raise HTTPException(status_code=500, detail=f"Error del agente: {result['error']}")
    
    logger.info(f"Investigación completada para el tema: {request.topic}. Enlace GDrive: {result.get('report_gdrive_link')}")
    return ResearchAPIResponse(
        message=result.get("message", "Investigación procesada."),
        topic=result.get("topic", request.topic), # Asegurarse de que topic siempre se devuelve
        report_gdrive_link=result.get("report_gdrive_link"),
        report_gdrive_id=result.get("report_gdrive_id"),
        report_summary_for_db=result.get("report_summary_for_db"),
        full_report_content=result.get("full_report_content"),
        local_fallback_path=result.get("local_fallback_path"),
        relevant_past_research=relevant_past_research_data if relevant_past_research_data else None,
        error_details=result.get("error") # Pasar el error si es un error "manejado" por el agente
    )

@app.get("/research/memory", response_model=List[ResearchMemoryItem], tags=["Agente de Investigación"])
async def query_research_memory_endpoint(
    query: str,
    persistence_svc: PersistenceService = Depends(get_persistence_service_dependency)
):
    logger.info(f"Recibida petición /research/memory con query: '{query}'")
    if not persistence_svc or not persistence_svc.collection:
        logger.warning("Intento de consultar memoria, pero PersistenceService no está operativo.")
        raise HTTPException(status_code=503, detail="Servicio de persistencia (ChromaDB) no disponible.")
    
    try:
        similar_items = persistence_svc.query_similar_research(query_text=query, n_results=5)
    except Exception as e_mem_query_ep:
        logger.error(f"Excepción no manejada durante persistence_svc.query_similar_research: {e_mem_query_ep}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al consultar la memoria: {e_mem_query_ep}")

    if not similar_items:
        logger.info("Consulta a memoria no devolvió resultados.")
        return [] # Devolver lista vacía es un resultado válido
    
    response_items = [ResearchMemoryItem(**item) for item in similar_items]
    logger.info(f"Devolviendo {len(response_items)} items desde la memoria.")
    return response_items