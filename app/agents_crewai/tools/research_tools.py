# app/agents_crewai/tools/research_tools.py

# Importar el decorador '@tool'
try:
    from crewai_tools import tool
    print("DEBUG research_tools.py: Decorador '@tool' importado OK.")
except ImportError as e:
     print(f"ERROR CRITICO research_tools.py: Fallo al importar '@tool' desde 'crewai_tools'. Error: {e}")
     # Definir un decorador dummy para que el archivo no falle al cargar, pero la herramienta no se registrará
     def tool(*args, **kwargs):
         def decorator(func):
             return func
         return decorator


# Otros imports necesarios
import openai
# Ya NO necesitamos Pydantic aquí si no usamos args_schema
# from pydantic.v1 import BaseModel, Field

# Importar 'settings' para acceder a la API Key de OpenAI
try:
    from app.core.config import settings
    if not settings or not settings.OPENAI_API_KEY:
        print("ERROR CRITICO research_tools.py (@tool approach): La clave API de OpenAI NO está configurada o settings no cargó.")
        openai.api_key = None
    else:
        openai.api_key = settings.OPENAI_API_KEY
        print(f"DEBUG research_tools.py (@tool approach): OpenAI API Key configurada: {bool(openai.api_key)}")

except ImportError:
    print("ERROR CRITICO research_tools.py (@tool approach): No se pudo importar 'settings' desde 'app.core.config'.")
    openai.api_key = None


# Ya NO definimos la clase Pydantic 'ContentAnalysisInputSchema'
# class ContentAnalysisInputSchema(BaseModel):
#     ...


# Definir la herramienta usando el decorador @tool SIN args_schema
@tool("Herramienta de Análisis de Contenido y Generación de Informes Estratégicos") # <--- SIN args_schema=...
def content_analyzer(topic: str, content_to_analyze: str) -> str:
    """
    Analiza un contenido textual proporcionado ('content_to_analyze') sobre un tema específico ('topic')
    y genera un informe estructurado en Markdown con un resumen ejecutivo y vías de acción.
    Utiliza esta herramienta para procesar texto y obtener análisis estratégico y recomendaciones.
    Los argumentos OBLIGATORIOS son 'topic' (un string que describe el tema) y
    'content_to_analyze' (un string con el texto detallado a analizar).
    La función devuelve el informe generado como un string Markdown.
    """
    # La docstring ahora es MÁS importante para que el LLM entienda los parámetros.

    print(f"DEBUG content_analyzer (@tool): Iniciando para tema='{topic[:50]}...'")

    if not openai.api_key:
        error_msg = "Error Config: OpenAI API Key no disponible."
        print(f"ERROR content_analyzer (@tool): {error_msg}")
        return error_msg

    if not topic or not content_to_analyze:
        error_msg = "Error Input: 'topic' y 'content_to_analyze' son requeridos y no deben estar vacíos."
        print(f"ERROR content_analyzer (@tool): {error_msg}")
        return error_msg

    def _generate_prompt(t, c):
        return f"""
Eres un consultor estratégico...

**Tema de Investigación:** {t}
**Contenido a Analizar:**
---
{c}
---
**Formato de Respuesta Solicitado (USA MARKDOWN):**
# Informe de Investigación: {t}
## Resumen Ejecutivo
[...]
## Vías de Acción Sugeridas
[...]
(Prompt completo como antes)
"""
    prompt = _generate_prompt(topic, content_to_analyze)

    try:
        print(f"DEBUG content_analyzer (@tool): Llamando a OpenAI...")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "system", "content": "Eres un analista experto."}, {"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=2500
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            report = response.choices[0].message.content.strip()
            print(f"DEBUG content_analyzer(@tool): OpenAI OK (longitud: {len(report)}).")
            return report
        else:
            print("ERROR content_analyzer (@tool): Respuesta inesperada/vacía de OpenAI.")
            return "Error: Respuesta inesperada/vacía de OpenAI."
    except openai.AuthenticationError as e:
        error_msg = f"Error OpenAI Auth: {e}"
        print(f"ERROR content_analyzer (@tool): {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"Error Interno en herramienta llamando a OpenAI: {type(e).__name__} - {e}"
        print(f"ERROR content_analyzer(@tool): {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg