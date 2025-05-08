# app/agents_crewai/crew_agents.py
from crewai import Agent

# Reiniciamos la lógica de importación y definición aquí, confiando en que el import funciona.

researcher_agent = None # Inicializar a None

try:
    # Importar la FUNCIÓN decorada directamente desde research_tools
    from app.agents_crewai.tools.research_tools import content_analyzer
    print("DEBUG crew_agents.py: Intentando importar 'content_analyzer'...")

    # ELIMINAMOS la verificación 'callable()' explícita. Si el import no lanzó
    # una excepción, asumimos que es la función decorada y la usamos.
    
    print("DEBUG crew_agents.py: 'content_analyzer' importado, procediendo a definir agente...")

    # Definición normal del Agente de Investigación para CrewAI
    researcher_agent = Agent(
        role="Consultor Estratégico e Investigador Senior",
        goal=(
            "Analizar a fondo el contenido proporcionado sobre un tema específico, "
            "identificar insights clave, y generar un informe estructurado y accionable."
        ),
        backstory=(
            "Eres un experimentado consultor de gestión e investigador con una habilidad especial "
            "para destilar información compleja en resúmenes ejecutivos claros y proponer vías "
            "de acción estratégicas. Tu trabajo ayuda a los líderes a tomar decisiones informadas."
        ),
        # Pasar la FUNCIÓN decorada directamente a la lista 'tools'
        tools=[content_analyzer],
        allow_delegation=False,
        verbose=True,
        # Opcional: Especificar el LLM
        # from langchain_openai import ChatOpenAI
        # llm=ChatOpenAI(model_name="gpt-3.5-turbo-0125", temperature=0.7),
    )
    print("DEBUG crew_agents.py: 'researcher_agent' definido correctamente.")

except ImportError as e:
    print(f"ERROR CRITICO crew_agents.py: No se pudo importar 'content_analyzer'. Error: {e}")
    # Si el import falla, definimos el agente de error como antes
    researcher_agent = Agent(role="Agente de Investigación (ERROR)", goal="Reportar error", backstory="Herramienta no importada.", tools=[], verbose=True)
    print("WARN crew_agents.py: 'researcher_agent' definido con configuración de ERROR debido a ImportError.")
except Exception as e_general:
    # Capturar cualquier otro error inesperado durante la definición del agente
    print(f"ERROR CRITICO crew_agents.py: Excepción inesperada definiendo agente. Error: {e_general}", exc_info=True)
    researcher_agent = Agent(role="Agente de Investigación (ERROR General)", goal="Reportar error", backstory="Error inesperado durante inicialización.", tools=[], verbose=True)
    print("WARN crew_agents.py: 'researcher_agent' definido con configuración de ERROR General.")


# Verificación final (útil para depuración)
if not researcher_agent:
    print("ERROR CRITICO crew_agents.py: researcher_agent sigue siendo None después del bloque try-except.")
elif "ERROR" in researcher_agent.role:
    print("WARN crew_agents.py: Finalizando la carga del módulo con researcher_agent en estado de ERROR.")
else:
    print("INFO crew_agents.py: Módulo cargado, researcher_agent parece estar OK.")