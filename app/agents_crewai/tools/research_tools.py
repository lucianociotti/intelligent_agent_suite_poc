# app/agents_crewai/tools/research_tools.py
# VERSIÓN COMPLETA Y CORRECTA - 10 MAYO (TypeError OpenAI y Prompt Restaurado)

from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field
import openai
import logging

logger = logging.getLogger("research_tools")
logger.setLevel(logging.INFO) # O DEBUG para más detalle

# Configuración de API Key de OpenAI
openai_api_key_configured_status = False
try:
    from app.core.config import settings
    if settings and settings.OPENAI_API_KEY:
        openai.api_key = settings.OPENAI_API_KEY
        openai_api_key_configured_status = True
        logger.debug("ResearchTools: OpenAI API Key asignada y lista.")
    else:
        logger.error("ResearchTools: OpenAI API Key NO ESTÁ en settings o settings no disponible.")
except ImportError:
    logger.error("ResearchTools: Fallo importando 'settings' (OpenAI API Key).")
except Exception as e_conf:
    logger.error(f"ResearchTools: Excepción config API Key OpenAI: {e_conf}")

class ContentAnalysisToolInput(BaseModel):
    """Inputs para ContentAnalysisTool. Usa Pydantic v1."""
    topic: str = Field(..., description="Tema principal que contextualiza el análisis.")
    content_to_analyze: str = Field(..., min_length=50, description="Texto detallado a analizar para el informe.")

class ContentAnalysisTool(BaseTool):
    """
    Analiza texto ('content_to_analyze') bajo un 'topic', generando un informe Markdown
    con 'Resumen Ejecutivo' y 'Vías de Acción Sugeridas'. No busca web, se basa en el texto provisto.
    """
    name: str = "Analizador Profundo de Contenido y Generador de Informes Estratégicos"
    description: str = (
        "Toma 'topic' (string) y 'content_to_analyze' (string extenso). Analiza el "
        "'content_to_analyze' según el 'topic' y produce un informe Markdown profesional con "
        "'## Resumen Ejecutivo' y '## Vías de Acción Sugeridas' (3-5 acciones). Usar cuando "
        "se necesita un análisis profundo de un texto ya recopilado."
    )
    args_schema: type[BaseModel] = ContentAnalysisToolInput

    def _get_analysis_prompt(self, topic: str, content_to_analyze: str) -> str:
        """
        Genera el prompt completo y detallado para la tarea de análisis.
        Este prompt es el que habíamos afinado para la herramienta.
        """
        # --- INICIO DEL PROMPT DETALLADO ---
        return f"""
Actúa como un analista estratégico y consultor senior. Tu misión es destilar el siguiente "Contenido a Analizar" en un informe estructurado y accionable, contextualizado por el "Tema de Investigación".

**Tema de Investigación:** {topic}

**Contenido a Analizar (Fuente Principal de Información):**
---
{content_to_analyze}
---

**Instrucciones Detalladas para el Formato del Informe (Usa Markdown Estricto):**

1.  **Título del Informe:** Comienza con `# Informe de Investigación: {topic}`.
2.  **Resumen Ejecutivo:** Bajo un encabezado `## Resumen Ejecutivo`. Debe ser:
    *   Conciso pero completo.
    *   Extraído y sintetizado ÚNICAMENTE del "Contenido a Analizar".
    *   Destacar los puntos cruciales, hallazgos y conclusiones del texto.
    *   Fácil de entender por sí mismo.
    *   Longitud ideal: 2-4 párrafos bien redactados.
3.  **Vías de Acción Sugeridas:** Bajo un encabezado `## Vías de Acción Sugeridas`. Debe:
    *   Proponer entre 3 y 5 acciones concretas, lógicas y bien fundamentadas.
    *   Cada acción debe derivarse directamente del "Resumen Ejecutivo" y del análisis del "Contenido a Analizar".
    *   Para cada vía de acción, usar un sub-encabezado `### <Número>. **Nombre de la Acción en Negrita**` (ejemplo: `### 1. **Optimizar la Estrategia de Contenidos**`) seguido de una explicación detallada de la acción, su justificación basada en el análisis y el impacto esperado.

**Consideraciones Adicionales:**
*   Mantén un tono profesional, objetivo y analítico.
*   La calidad del análisis y la claridad de las recomendaciones son primordiales.
*   NO introduzcas información externa, opiniones personales o suposiciones que no estén directamente respaldadas por el "Contenido a Analizar" proporcionado.
*   El informe final debe ser directamente útil para la toma de decisiones estratégicas.
*   Tu respuesta debe comenzar INMEDIATAMENTE con `# Informe de Investigación: ...` y no incluir frases introductorias como "Claro, aquí tienes el informe..." o conclusiones generales fuera de las secciones solicitadas.
"""
        # --- FIN DEL PROMPT DETALLADO ---

    def _run(self, topic: str, content_to_analyze: str) -> str:
        logger.info(f"ContentAnalysisTool._run: Tema: '{topic[:40]}...', Longitud contenido: {len(content_to_analyze)}")
        
        if not openai_api_key_configured_status: # Verifica la flag del módulo
            return "Error Crítico Config (ContentAnalysisTool): OpenAI API Key no disponible."
        
        if not topic or not isinstance(topic, str) or not topic.strip():
            return "Error Input (ContentAnalysisTool): El 'topic' es obligatorio y debe ser un string no vacío."
        if not content_to_analyze or not isinstance(content_to_analyze, str) or len(content_to_analyze) < 20: # Un mínimo para tener algo que analizar
            return "Error Input (ContentAnalysisTool): 'content_to_analyze' es requerido y debe tener al menos 20 caracteres."

        analysis_prompt = self._get_analysis_prompt(topic, content_to_analyze)

        try:
            logger.debug("ContentAnalysisTool._run: Llamando a OpenAI ChatCompletions...")
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",      # Keyword argument
                messages=[                       # Keyword argument
                    {"role": "system", "content": "Eres un asistente IA altamente competente en análisis profundo de texto y generación de informes estratégicos estructurados."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.4,                 # Keyword argument (un poco menos creativo para análisis)
                max_tokens=2048                  # Keyword argument
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                report = response.choices[0].message.content.strip()
                logger.info(f"ContentAnalysisTool._run: Informe generado por IA (Longitud: {len(report)}).")
                return report
            else:
                logger.error("ContentAnalysisTool._run: Respuesta de OpenAI vacía o con formato inesperado.")
                return "Error (ContentAnalysisTool): La respuesta de OpenAI fue vacía o no contenía el mensaje esperado."
        except openai.AuthenticationError as e:
            logger.error(f"ContentAnalysisTool - OpenAI AuthenticationError: {e}", exc_info=True)
            return f"Error de Autenticación con OpenAI. Revisa tu API Key. Detalle: {e}"
        except openai.RateLimitError as e:
            logger.error(f"ContentAnalysisTool - OpenAI RateLimitError: {e}", exc_info=True)
            return f"Error: Límite de Tasa de OpenAI alcanzado. Intenta más tarde. Detalle: {e}"
        except Exception as e:
            logger.error(f"ContentAnalysisTool - Excepción llamando a OpenAI: {type(e).__name__} - {e}", exc_info=True)
            return f"Error Interno en ContentAnalysisTool al contactar OpenAI: {type(e).__name__}"

# La clase ContentAnalysisTool será importada y luego instanciada en crew_agents.py