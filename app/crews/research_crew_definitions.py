# app/crews/research_crew_definitions.py
from crewai import Task, Crew, Process
from typing import Optional # Importar Optional

try:
    # Intentar importar el agente que DEBERÍA estar definido arriba
    from app.agents_crewai.crew_agents import researcher_agent
    print("DEBUG research_crew_definitions.py: Importando 'researcher_agent'...")
    if not researcher_agent: # Si la importación no trae nada (error previo)
         print("ERROR CRITICO research_crew_definitions.py: 'researcher_agent' es None después de importar.")
    elif "ERROR" in researcher_agent.role: # Si es el agente de error
         print("WARN research_crew_definitions.py: 'researcher_agent' importado en estado de error.")
    else:
        print("DEBUG research_crew_definitions.py: 'researcher_agent' importado OK.")
except ImportError as e:
     print(f"ERROR CRITICO research_crew_definitions.py: No se pudo importar 'researcher_agent'. Error: {e}")
     researcher_agent = None # Marcar como no disponible


def create_research_crew_and_kickoff(topic: str, content_to_analyze: str) -> Optional[str]:
    """Crea y ejecuta el crew de investigación."""
    print(f"DEBUG create_research_crew...: Iniciando para '{topic[:30]}...'")

    if not researcher_agent or "ERROR" in researcher_agent.role:
        error_msg = "Error crítico: Agente de investigación no está disponible o está en estado de error (falló la importación previa de herramientas/agente)."
        print(f"ERROR create_research_crew...: {error_msg}")
        # Devolver el mensaje de error para que la API lo maneje
        # En lugar de lanzar excepción aquí, devolvemos string que la API interpretará.
        return error_msg

    # Definir la Tarea
    try:
        # El contexto se pasa via kickoff, la descripción se enfoca en el 'qué hacer'
        research_task = Task(
            description=(
                f"Realiza un análisis exhaustivo sobre el tema '{topic}', basándote PRINCIPALMENTE en el "
                f"'content_to_analyze' proporcionado. "
                "Genera un informe completo y profesional en formato Markdown. "
                "El informe DEBE incluir una sección clara '## Resumen Ejecutivo' "
                "y OBLIGATORIAMENTE una sección '## Vías de Acción Sugeridas' con al menos 3 acciones detalladas."
            ),
            expected_output=(
                "Un único string conteniendo el informe completo en formato Markdown, "
                "correctamente estructurado con '# Informe de Investigación: <TEMA>', "
                "'## Resumen Ejecutivo', y '## Vías de Acción Sugeridas'."
            ),
            agent=researcher_agent, # Usar el agente importado
            # Nota: No pasamos inputs directamente a la Tarea aquí;
            # se proporcionan al método kickoff del Crew.
        )
        print("DEBUG create_research_crew...: Tarea 'research_task' creada.")
    except Exception as e_task:
        error_msg = f"Error creando la instancia de Task: {e_task}"
        print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
        return error_msg # Devolver el error

    # Crear el Crew
    try:
        research_crew = Crew(
            agents=[researcher_agent], # Lista con nuestro único agente
            tasks=[research_task],    # Lista con nuestra única tarea
            process=Process.sequential, # Proceso simple: una tarea después de otra (si hubiera más)
            verbose=True, # Usar Booleano True para verbosidad alta (detalles del agente)
                           # False para menos, o int 0, 1, 2 para niveles específicos si la versión lo soporta y está documentado así
        )
        print("DEBUG create_research_crew...: Crew creado con verbose=True.")
    except Exception as e_crew_create:
         error_msg = f"Error creando la instancia de Crew: {e_crew_create}"
         print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
         return error_msg

    # Ejecutar el Crew
    crew_result: Optional[str] = None
    try:
        print(f"DEBUG create_research_crew...: Ejecutando crew.kickoff() con inputs: topic='{topic[:30]}...', content_to_analyze (longitud: {len(content_to_analyze)})")
        # Los inputs aquí estarán disponibles para el contexto de las tareas vía {nombre_del_input}
        # en sus descripciones, y para las herramientas si el LLM decide pasarlos.
        crew_inputs = {'topic': topic, 'content_to_analyze': content_to_analyze}
        crew_result = research_crew.kickoff(inputs=crew_inputs)
        print(f"DEBUG create_research_crew...: Kickoff finalizado. Tipo de resultado: {type(crew_result)}")
        if isinstance(crew_result, str):
            print(f"DEBUG create_research_crew...: Resultado (primeros 100 chars): {crew_result[:100]}...")
        elif crew_result is None:
             print("WARN create_research_crew...: Kickoff devolvió None.")
        else:
             print(f"WARN create_research_crew...: Kickoff devolvió un tipo inesperado: {type(crew_result)}")
    except Exception as e_kickoff:
        error_msg = f"Error durante crew.kickoff(): {type(e_kickoff).__name__} - {e_kickoff}"
        print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
        return error_msg # Devolver el string de error

    # Asegurarse de devolver un string o None
    if isinstance(crew_result, str):
        return crew_result
    elif crew_result is None:
        return "Error: El proceso del Crew finalizó sin devolver un resultado de texto."
    else:
        # Intentar convertir a string si es un objeto complejo, aunque lo ideal es que devuelva string
        try:
            return str(crew_result)
        except:
            return "Error: El proceso del Crew devolvió un resultado de tipo inesperado."