# app/backend/api_models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ResearchAPIRequest(BaseModel):
    topic: str = Field(..., min_length=3, description="El tema principal de la investigación.")
    content_to_analyze: str = Field(..., min_length=20, description="El contenido textual que el agente debe analizar.") # Reducido min_length para pruebas

class ResearchMemoryItem(BaseModel):
    id: str
    document_stored: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    similarity_score: Optional[float] = None # Podría ser 1 - distancia
    distance: Optional[float] = None


class ResearchAPIResponse(BaseModel):
    message: str
    topic: Optional[str] = None # Hacer opcional si puede fallar antes
    report_gdrive_link: Optional[str] = None
    report_gdrive_id: Optional[str] = None
    report_summary_for_db: Optional[str] = None
    full_report_content: Optional[str] = None
    local_fallback_path: Optional[str] = None
    error_details: Optional[str] = None
    relevant_past_research: Optional[List[ResearchMemoryItem]] = None