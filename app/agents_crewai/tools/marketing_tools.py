# app/agents_crewai/tools/marketing_tools.py
# VERSIÓN CORREGIDA Y COMPLETA - 9 MAY 2025

# Importar el decorador '@tool'
try:
    from crewai_tools import tool
    print("DEBUG marketing_tools.py: Decorador '@tool' importado OK.")
except ImportError as e:
     print(f"ERROR CRITICO marketing_tools.py: Fallo al importar '@tool' desde 'crewai_tools'. Error: {e}")
     # Decorador dummy para que el archivo cargue pero las tools fallen si se usan
     def tool(*args, **kwargs):
         def decorator(func):
             # Podríamos añadir una advertencia si se llama a una función 'decorada' con el dummy
             def wrapper(*a, **k):
                 print(f"ERROR: Herramienta '{func.__name__}' no operativa debido a fallo de import de @tool.")
                 return f"Error: Decorador @tool no encontrado."
             return wrapper
         return decorator


# Otros imports necesarios
import openai
# Pydantic V1 para schema inferido si @tool lo necesita (no lo usamos explícitamente ahora)
from pydantic.v1 import BaseModel, Field
import logging

logger = logging.getLogger(__name__)
# Cambiar a DEBUG si necesitas más detalle aquí
logger.setLevel(logging.INFO)

# API Key Setup
openai_api_key_status = False
try:
    from app.core.config import settings
    if settings and settings.OPENAI_API_KEY:
        openai.api_key = settings.OPENAI_API_KEY
        openai_api_key_status = True
        logger.debug("MarketingTools: OpenAI API Key OK.")
    else:
        logger.error("MarketingTools: OpenAI API Key NO encontrada en settings.")
except ImportError:
    logger.error("MarketingTools: Fallo al importar settings para API Key.")


# --- Herramienta 1: Generar Ideas de Marketing ---
@tool("Generador de Ideas de Marketing") # SIN args_schema
def generate_marketing_ideas(topic: str, context: str | None = None) -> str:
    """
    Genera ideas de marketing (ángulos, tipos post, hashtags, CTAs) basadas en 'topic' (REQ) y 'context' (OPT).
    Ideal para brainstorming inicial. Describe claramente los parámetros en la docstring.
    'topic': El tema central (string).
    'context': Información adicional para refinar ideas (string, opcional).
    """
    logger.info(f"Tool Exec: generate_marketing_ideas para '{topic[:30]}...'")
    if not openai_api_key_status: return "Error Configuración: Clave OpenAI no disponible."
    if not topic: return "Error Input: El parámetro 'topic' es obligatorio."

    prompt_parts = [
        f"Eres un especialista MUY CREATIVO en marketing digital. Genera ideas CONCRETAS y ATRACTIVAS para: '{topic}'.",
        "Objetivos: interés, educación, interacción, conversión."
    ]
    if context:
        prompt_parts.append(f"Considera este CONTEXTO:\n{context}")
    prompt_parts.append(
        "Proporciona 5+ ideas distintas. Cada una debe incluir: "
        "1. Ángulo/Concepto Principal. "
        "2. Tipo Contenido Sugerido (Post Instagram, Video corto, Artículo blog...). "
        "3. Hashtags Propuestos (#relevante #nicho). "
        "4. CTA Sugerido (Visita link, Comenta...). "
        "Formato: Lista clara."
    )
    prompt = "\n".join(prompt_parts)

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "Asistente brainstorming marketing."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, max_tokens=1000
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            ideas = response.choices[0].message.content.strip()
            logger.info(f"Tool OK: generate_marketing_ideas generó {len(ideas)} chars.")
            return ideas
        else:
            logger.error("Tool Error: generate_marketing_ideas - OpenAI devolvió respuesta vacía.")
            return "Error: No se recibieron ideas válidas de OpenAI."
    except Exception as e:
        logger.error(f"Tool Error: generate_marketing_ideas - Excepción OpenAI: {e}", exc_info=True)
        return f"Error Interno (Ideas Tool): {type(e).__name__}"


# --- Herramienta 2: Escribir Texto para Post Social ---
@tool("Redactor de Posts para Redes Sociales") # SIN args_schema
def write_social_post(topic_or_idea: str, platform: str, context: str | None = None) -> str:
    """
    Redacta texto (copy) para un post social sobre 'topic_or_idea' (REQ)
    para una 'platform' específica (REQ: Instagram, LinkedIn, Twitter/X, Facebook, General).
    Usa 'context' (OPT) para refinar. Adapta tono y formato. Devuelve SÓLO el texto del post.
    'topic_or_idea': Tema o idea base (string).
    'platform': Plataforma destino (string).
    'context': Contexto adicional (string, opcional).
    """
    logger.info(f"Tool Exec: write_social_post para '{topic_or_idea[:30]}...' en '{platform}'")
    if not openai_api_key_status: return "Error Configuración: Clave OpenAI no disponible."
    if not topic_or_idea or not platform: return "Error Input: 'topic_or_idea' y 'platform' son obligatorios."

    valid_platforms = ['instagram', 'linkedin', 'twitter/x', 'facebook', 'general']
    platform_lower = platform.strip().lower()
    if platform_lower not in valid_platforms:
        return f"Error: Plataforma '{platform}' inválida. Usar: {', '.join(valid_platforms)}."

    prompt_parts = [
        f"Eres un copywriter experto en redes sociales. Redacta un post efectivo para '{platform}' sobre: '{topic_or_idea}'.",
        f"Adapta longitud, tono (ej: {'casual/visual' if platform_lower=='instagram' else 'profesional' if platform_lower=='linkedin' else 'conciso'}), emojis y formato a '{platform}'."
    ]
    if context:
        prompt_parts.append(f"Considera este CONTEXTO:\n{context}")
    prompt_parts.append("Incluye hashtags relevantes si aplica. Añade CTA si encaja. DEVOLVER SÓLO TEXTO DEL POST FINAL.")
    prompt = "\n".join(prompt_parts)

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": f"Copywriter experto para {platform}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=600 # Más corto para posts
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            post_text = response.choices[0].message.content.strip()
            logger.info(f"Tool OK: write_social_post generó texto (len: {len(post_text)}).")
            return post_text
        else:
            logger.error("Tool Error: write_social_post - OpenAI devolvió respuesta vacía.")
            return "Error: No se recibió texto de post válido de OpenAI."
    except Exception as e:
        logger.error(f"Tool Error: write_social_post - Excepción OpenAI: {e}", exc_info=True)
        return f"Error Interno (Post Tool): {type(e).__name__}"


# --- Herramienta 3: Sugerir Prompt para Imagen (DALL-E) ---
@tool("Generador de Prompts para DALL-E") # SIN args_schema
def suggest_image_prompt(post_concept_or_text: str, style_preferences: str | None = None) -> str:
    """
    Genera un prompt detallado para IA de imágenes (DALL-E, etc.) basado en 'post_concept_or_text' (REQ).
    Puede usar 'style_preferences' (OPT, ej: fotorrealista, abstracto).
    Devuelve SÓLO el prompt optimizado.
    'post_concept_or_text': Idea clave o texto del post (string).
    'style_preferences': Estilo visual deseado (string, opcional).
    """
    logger.info(f"Tool Exec: suggest_image_prompt para '{post_concept_or_text[:30]}...'")
    if not openai_api_key_status: return "Error Configuración: Clave OpenAI no disponible."
    if not post_concept_or_text: return "Error Input: 'post_concept_or_text' es obligatorio."

    prompt_parts = [
        f"Eres Director de Arte IA experto en prompts para DALL-E/Midjourney. Crea prompt para imagen basada en:\n{post_concept_or_text}\n",
        "Describe sujeto, acción, entorno, estilo, luz, color, composición. Sé detallado y evocador."
    ]
    if style_preferences:
        prompt_parts.append(f"Estilo preferido: '{style_preferences}'.")
    else:
        prompt_parts.append("Sugiere un estilo visual apropiado.")
    prompt_parts.append("Escribe SÓLO el prompt, sin comillas ni texto adicional.")
    prompt = "\n".join(prompt_parts)

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "Experto en prompts para IA de imágenes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=350
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            image_prompt = response.choices[0].message.content.strip()
            # Limpiar comillas iniciales/finales si existen
            if image_prompt.startswith(('"', "'")) and image_prompt.endswith(('"', "'")):
                 image_prompt = image_prompt[1:-1]
            logger.info(f"Tool OK: suggest_image_prompt generó: {image_prompt[:70]}...")
            return image_prompt
        else:
             logger.error("Tool Error: suggest_image_prompt - OpenAI devolvió respuesta vacía.")
             return "Error: No se recibió prompt de imagen válido de OpenAI."
    except Exception as e:
        logger.error(f"Tool Error: suggest_image_prompt - Excepción OpenAI: {e}", exc_info=True)
        return f"Error Interno (Image Prompt Tool): {type(e).__name__}"

# NOTA: La herramienta opcional DallETool no se incluye aquí para simplificar.
# Si la necesitas, la añadiríamos de forma similar, importando de crewai_tools si está disponible.