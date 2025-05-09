# app/backend/api_models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# --- Modelos para Investigación ---
class ResearchAPIRequest(BaseModel):
    topic: str = Field(..., min_length=3, description="El tema principal a investigar.")
    content_to_analyze: Optional[str] = Field( # Opcional ahora
        None, min_length=10, description="(Opcional) Contenido textual adicional para analizar."
    )

class ResearchMemoryItem(BaseModel):
    id: str
    document_stored: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    similarity_score: Optional[float] = None
    distance: Optional[float] = None

class ResearchAPIResponse(BaseModel):
    message: str
    topic: Optional[str] = None
    report_gdrive_link: Optional[str] = None
    report_gdrive_id: Optional[str] = None
    report_summary_for_db: Optional[str] = None
    full_report_content: Optional[str] = None # Contenido final (editado)
    local_fallback_path: Optional[str] = None
    error_details: Optional[str] = None
    relevant_past_research: List[ResearchMemoryItem] = [] # Default a lista vacía


# --- Modelos para Marketing (NUEVOS) ---
class MarketingContentRequest(BaseModel):
    topic: str = Field(..., description="Tema central o producto para la campaña/post.")
    platform: str = Field(..., description="Plataforma destino (ej. Instagram, LinkedIn, Twitter/X).")
    context: Optional[str] = Field(None, description="Contexto adicional (audiencia, objetivos, resultados de investigación previa, etc.).")
    # style_preferences: Optional[str] = Field(None, description="Preferencias de estilo para imagen (opcional).") # Añadir si implementas DALL-E Tool

class MarketingContentResponse(BaseModel):
    message: str
    topic: str
    platform: str
    marketing_ideas: Optional[str] = None # Texto con ideas, hashtags, CTAs
    post_text: Optional[str] = None      # Texto redactado para el post
    image_prompt: Optional[str] = None   # Prompt sugerido para DALL-E
    # generated_image_url: Optional[str] = None # Añadir si implementas DALL-E Tool
    error_details: Optional[str] = None # Para errores específicos