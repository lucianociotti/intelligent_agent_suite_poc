# app/agents_crewai/crew_agents.py
# VERSIÓN CORREGIDA Y COMPLETA - 9 MAY 2025 (2)

from crewai import Agent
import sys
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # O DEBUG


# --- Herramientas ---
# Inicializar listas y variables
content_analyzer_tool = None # Variable para la instancia (si se crea) o clase
tavily_search_tool = None
available_researcher_tools = []

marketing_ideas_tool = None
write_post_tool = None
suggest_prompt_tool = None
available_marketing_tools = []


# 1. Cargar Herramienta de Análisis de Contenido (Clase + Instancia)
try:
    # Importar la CLASE BaseTool y nuestra Clase custom
    from langchain_core.tools import BaseTool
    from app.agents_crewai.tools.research_tools import ContentAnalysisTool

    if issubclass(ContentAnalysisTool, BaseTool): # Verificar herencia
        print("DEBUG crew_agents.py: CLASE 'ContentAnalysisTool' importada y hereda de BaseTool.")
        # Creamos la INSTANCIA
        content_analyzer_tool = ContentAnalysisTool()
        available_researcher_tools.append(content_analyzer_tool) # Añadir la INSTANCIA
        print(f"DEBUG crew_agents.py: INSTANCIA '{content_analyzer_tool.name}' creada y añadida.")
    else:
        print("ERROR CRITICO crew_agents.py: ContentAnalysisTool no hereda de BaseTool?")

except ImportError as e:
    print(f"ERROR CRITICO crew_agents.py: Importando ContentAnalysisTool o BaseTool. Error: {e}")
except Exception as e_cat_inst:
    print(f"ERROR CRITICO crew_agents.py: Instanciando 'ContentAnalysisTool'. Error: {e_cat_inst}")

# 2. Cargar e Instanciar Tavily Search Tool
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    from app.core.config import settings
    if settings and settings.TAVILY_API_KEY:
        tavily_search_tool = TavilySearchResults(max_results=5, name="Tavily Search Results") # Añadir nombre explícito
        available_researcher_tools.append(tavily_search_tool)
        print(f"DEBUG crew_agents.py: INSTANCIA '{tavily_search_tool.name}' creada y añadida.")
    else: print("WARN crew_agents.py: TAVILY_API_KEY ausente, Tavily tool no creada.")
except ImportError as e: print(f"ERROR CRITICO crew_agents.py: Importando Tavily. Error: {e}")
except Exception as e: print(f"ERROR CRITICO crew_agents.py: Instanciando Tavily. Error: {e}")


# 3. Cargar Herramientas de Marketing (Funciones decoradas con @tool)
try:
    from app.agents_crewai.tools.marketing_tools import (
        generate_marketing_ideas, write_social_post, suggest_image_prompt
    )
    marketing_tools_to_check = {
        "generate_marketing_ideas": generate_marketing_ideas,
        "write_social_post": write_social_post,
        "suggest_image_prompt": suggest_image_prompt
    }
    for tool_name, tool_func in marketing_tools_to_check.items():
        # Verificar si es un objeto utilizable por CrewAI (wrapper de @tool)
        # Una verificación simple es ver si tiene un atributo 'name' que le pone el decorador
        if hasattr(tool_func, 'name') and hasattr(tool_func, 'description') and hasattr(tool_func, 'run'):
            available_marketing_tools.append(tool_func) # Añadir la función/wrapper decorada
            print(f"DEBUG crew_agents.py: Herramienta Marketing '{tool_func.name}' cargada OK.")
        else:
            # Si no parece una herramienta CrewAI válida (posiblemente el import de @tool falló antes)
            print(f"WARN crew_agents.py: '{tool_name}' cargada pero no parece herramienta CrewAI válida.")

    print(f"DEBUG crew_agents.py: Cargadas {len(available_marketing_tools)} herramientas de marketing válidas.")

except ImportError as e: print(f"ERROR CRITICO crew_agents.py: Fallo importando una o más marketing_tools. Error: {e}")
except Exception as e_mkt: print(f"ERROR CRITICO crew_agents.py: Excepción cargando marketing_tools. Error: {e_mkt}")


# --- Definición Agente Investigador ---
if not available_researcher_tools:
     researcher_agent = Agent(role="Investigador (ERROR)", goal="Reportar fallo", tools=[], verbose=True)
     print("ERROR CRITICO crew_agents.py: researcher_agent creado SIN herramientas.")
else:
    researcher_agent = Agent(
        role="Investigador y Analista Estratégico Senior",
        goal="Buscar web (Tavily) y analizar contenido para generar informes.",
        backstory="Experto combinando búsqueda y análisis para estrategia.",
        tools=available_researcher_tools, # Lista con INSTANCIAS
        allow_delegation=False,
        verbose=True
    )
    # CORRECCIÓN del log para obtener nombre (acceder directo a .name)
    tool_names_res = [t.name for t in available_researcher_tools if hasattr(t, 'name')]
    print(f"DEBUG crew_agents.py: 'researcher_agent' definido con herramientas: {tool_names_res}")


# --- Definición Agente Editor (Sin cambios) ---
editor_agent = Agent(
    role="Editor Profesional Senior",
    goal="Revisar y pulir borradores de informes para mejorar claridad y estilo.",
    backstory="Experto en comunicación escrita con ojo para el detalle.",
    tools=[],
    allow_delegation=False,
    verbose=True
)
print("DEBUG crew_agents.py: 'editor_agent' definido.")


# --- Definición Agente Marketing ---
if not available_marketing_tools:
     marketing_content_agent = Agent(role="Marketing (ERROR)", goal="Reportar fallo", tools=[], verbose=True)
     print("ERROR CRITICO crew_agents.py: marketing_content_agent creado SIN herramientas de marketing.")
else:
    marketing_content_agent = Agent(
        role="Especialista Marketing Contenidos IA",
        goal="Generar ideas, posts y prompts de imagen para redes sociales.",
        backstory="Experto creativo IA en copywriting y visuales.",
        tools=available_marketing_tools, # Lista con funciones @tool
        allow_delegation=False,
        verbose=True
    )
    # CORRECCIÓN del log para obtener nombre
    tool_names_mkt = [t.name for t in available_marketing_tools if hasattr(t, 'name')]
    print(f"DEBUG crew_agents.py: 'marketing_content_agent' definido con herramientas: {tool_names_mkt}")

print("INFO crew_agents.py: Módulo cargado.")