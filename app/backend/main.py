# app/backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import datetime
import os
import re
from typing import List, Optional, Dict, Any

# --- Imports de Config, Modelos y Servicios ---
try: from app.core.config import settings
except ImportError: settings = None # Definir como None si falla
from app.backend.api_models import ( # Asegúrate que este archivo exista y defina estos + los nuevos de Marketing
     ResearchAPIRequest, ResearchAPIResponse, ResearchMemoryItem,
     MarketingContentRequest, MarketingContentResponse # <-- NUEVOS
)
from app.services.gdrive_service import GDriveService
from app.services.persistence_service import PersistenceService

# --- Imports de Crews ---
try: from app.crews.research_crew_definitions import create_research_crew_and_kickoff as research_crew_exec
except ImportError: research_crew_exec = None # Marcar como None si falla
try: from app.crews.marketing_crew_definitions import create_marketing_content_crew_and_kickoff as marketing_crew_exec
except ImportError: marketing_crew_exec = None # Marcar como None si falla

# --- Logger y Servicios Globales ---
logger = logging.getLogger("app.backend.main")
logger.setLevel(logging.INFO)
gdrive_service_instance: Optional[GDriveService] = None
persistence_service_instance: Optional[PersistenceService] = None
try: # Instanciación global (con manejo básico de errores)
    if GDriveService: gdrive_service_instance = GDriveService()
    if not gdrive_service_instance or not gdrive_service_instance.service: logger.error("GDriveService global falló.")
    if PersistenceService: persistence_service_instance = PersistenceService()
    if not persistence_service_instance or not persistence_service_instance.collection: logger.error("PersistenceService global falló.")
except Exception as e: logger.error(f"Excepción instanciando servicios globales: {e}", exc_info=True)

# --- Dependencias FastAPI ---
def get_gdrive_service_dependency() -> Optional[GDriveService]: return gdrive_service_instance
def get_persistence_service_dependency() -> Optional[PersistenceService]: return persistence_service_instance

# --- App FastAPI ---
app = FastAPI(
    title="Suite Agentes Inteligentes - v0.4 (Marketing Contenido)",
    description="API para Agente de Investigación y Agente de Marketing de Contenidos.",
    version="0.4.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Eventos Startup ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI startup...")
    # Verificar dependencias críticas
    if not research_crew_exec: logger.critical("Función 'research_crew_exec' NO DISPONIBLE.")
    if not marketing_crew_exec: logger.critical("Función 'marketing_crew_exec' NO DISPONIBLE.")
    # (Verificaciones de servicios...)

# --- Endpoints ---
@app.get("/", tags=["General"])
async def read_root(): return {"message": "API Suite Agentes Inteligentes v0.4"}

def _sanitize_filename_for_api(filename_base: str) -> str: # Helper
    # ... (código de sanitización como antes)
    if not filename_base: return "documento_sin_titulo"
    s=filename_base.replace(' ','_');s=re.sub(r'[^\w.\-]','',s);s=re.sub(r'_{2,}','_',s);s=re.sub(r'\.{2,}','.',s);s=s.strip('_.-');return s[:100] if s else"doc_procesado"


@app.post("/research/conduct", response_model=ResearchAPIResponse, tags=["Investigación (CrewAI + Web + Editor)"])
async def conduct_research_with_crew_endpoint( # Endpoint de Investigación existente
    request: ResearchAPIRequest,
    gdrive_svc: Optional[GDriveService] = Depends(get_gdrive_service_dependency),
    persistence_svc: Optional[PersistenceService] = Depends(get_persistence_service_dependency)
):
    logger.info(f"POST /research/conduct | Tema: '{request.topic[:50]}...' | Contenido: {bool(request.content_to_analyze)}")
    if not research_crew_exec: raise HTTPException(status_code=503, detail="Servicio de Investigación no disponible.")

    final_report_content: Optional[str] = None
    try:
        final_report_content = research_crew_exec(topic=request.topic, content_to_analyze=request.content_to_analyze)
        if isinstance(final_report_content, str) and ("Error crítico:" in final_report_content or "Error:" in final_report_content[:150]):
            logger.error(f"Crew de Investigación devolvió error: {final_report_content}")
            raise HTTPException(status_code=502, detail=f"Error procesando investigación: {final_report_content}")
    except Exception as e_exec: logger.error(f"Error ejecución crew invest: {e_exec}", exc_info=True); raise HTTPException(500, f"Error interno crew invest: {e_exec}")

    if not isinstance(final_report_content, str) or not final_report_content.strip():
        raise HTTPException(status_code=500, detail="Investigación no produjo informe válido.")

    logger.info(f"Investigación OK (len: {len(final_report_content)}). Procesando post-crew...")
    # ... (resto de la lógica: extraer resumen, guardar GDrive, persistir ChromaDB, buscar memoria) ...
    # (Esta lógica puede permanecer muy similar a como estaba en tu última versión funcional)
    # Solo asegúrate de usar 'final_report_content'
    report_summary_for_db = final_report_content[:500] + "..." # Simplificado para el ejemplo
    gdrive_link, gdrive_id, local_fallback_path = None, None, None
    if gdrive_svc:
         filename = f"InformeEditado_{_sanitize_filename_for_api(request.topic)}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.md"
         res = gdrive_svc.upload_text_as_md(final_report_content, filename)
         if not res.get("error"): gdrive_link, gdrive_id = res.get("webViewLink"), res.get("id")
         else: logger.error("Fallo GDrive en /research"); # Podría haber fallback aquí
    if persistence_svc and gdrive_id:
        try: persistence_svc.add_research_document(topic=request.topic, summary=report_summary_for_db, gdrive_id=gdrive_id, gdrive_link=gdrive_link or "")
        except Exception as e: logger.error(f"Fallo ChromaDB en /research: {e}")
    # ... búsqueda de memoria relevante ...
    relevant_past = []

    return ResearchAPIResponse(
        message="Investigación+Edición completada y guardada.", topic=request.topic,
        report_gdrive_link=gdrive_link, report_gdrive_id=gdrive_id,
        report_summary_for_db=report_summary_for_db, full_report_content=final_report_content,
        local_fallback_path=local_fallback_path, relevant_past_research=relevant_past
    )

# --- NUEVO ENDPOINT PARA MARKETING ---
@app.post("/marketing/generate-content", response_model=MarketingContentResponse, tags=["Marketing (CrewAI)"])
async def generate_marketing_content_endpoint(
    request: MarketingContentRequest, # Necesitamos definir este modelo en api_models.py
):
    logger.info(f"POST /marketing/generate-content | Tema: '{request.topic[:50]}...' | Plataforma: {request.platform}")
    if not marketing_crew_exec: raise HTTPException(status_code=503, detail="Servicio de Marketing no disponible.")

    results_dict: Optional[dict] = None
    try:
        results_dict = marketing_crew_exec(
            topic=request.topic,
            platform=request.platform,
            context=request.context # Pasamos el contexto opcional
        )
        # Verificar si el diccionario devuelto contiene un error clave
        if isinstance(results_dict, dict) and results_dict.get("error"):
            error_msg = results_dict["error"]
            logger.error(f"Crew de Marketing devolvió error: {error_msg}")
            raise HTTPException(status_code=502, detail=f"Error procesando marketing: {error_msg}")

    except Exception as e_exec_mk:
        logger.error(f"Error ejecución crew marketing: {e_exec_mk}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno crew marketing: {str(e_exec_mk)}")

    if not isinstance(results_dict, dict) or not results_dict.get("post_text"): # Verificar si al menos el texto del post se generó
         logger.error(f"El crew de marketing devolvió resultado inesperado/incompleto: {results_dict}")
         raise HTTPException(status_code=500, detail="El proceso de marketing no generó contenido válido.")
    
    logger.info("Generación de contenido de marketing OK por Crew.")
    
    # Construir la respuesta API desde el diccionario devuelto por el crew
    return MarketingContentResponse(
         message="Contenido de marketing generado.",
         topic=request.topic,
         platform=request.platform,
         marketing_ideas=results_dict.get("ideas"),
         post_text=results_dict.get("post_text"),
         image_prompt=results_dict.get("image_prompt")
    )


# --- Endpoint de Memoria (Sin cambios necesarios) ---
@app.get("/research/memory", response_model=List[ResearchMemoryItem], tags=["Memoria de Investigación"])
async def query_research_memory_endpoint( # ... código como antes ...
    query: str,
    persistence_svc: Optional[PersistenceService] = Depends(get_persistence_service_dependency)
 ):
     # ... (lógica existente para buscar en ChromaDB)
    logger.info(f"GET /research/memory | query: '{query}'")
    if not persistence_svc or not persistence_svc.collection: raise HTTPException(503,"Servicio persistencia no disponible.")
    try:
        items = persistence_svc.query_similar_research(query_text=query, n_results=5)
        if not items: return []
        return [ResearchMemoryItem(**item) for item in items]
    except Exception as e: logger.error(f"Error en GET /memory: {e}"); raise HTTPException(500, "Error consultando memoria")


# --- Main para dev ---
if __name__ == "__main__":
    # ... (código uvicorn.run como antes) ...
    if not logging.getLogger().hasHandlers(): logging.basicConfig(level=logging.INFO)
    logger.info("Ejecutando FastAPI desde if __name__ == '__main__'")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)