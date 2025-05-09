# app/crews/research_crew_definitions.py
from crewai import Task, Crew, Process
from typing import Optional

try:
    # Importar AMBOS agentes definidos
    from app.agents_crewai.crew_agents import researcher_agent, editor_agent
    print("DEBUG research_crew_definitions.py: Importando 'researcher_agent' y 'editor_agent'...")

    # Verificaciones rápidas de que los agentes se importaron mínimamente
    agents_ok = True
    if not researcher_agent or "ERROR" in researcher_agent.role:
         print("WARN research_crew_definitions.py: 'researcher_agent' importado en estado de error o no definido.")
         agents_ok = False
    if not editor_agent: # Verificar solo existencia, ya que no tiene dependencias complejas
        print("ERROR CRITICO research_crew_definitions.py: 'editor_agent' no definido después de importar.")
        agents_ok = False
    
    if agents_ok:
        print(f"DEBUG research_crew_definitions.py: Agentes investigador (herramientas: {len(getattr(researcher_agent,'tools',[]))}) y editor importados.")
    else:
         print("ERROR research_crew_definitions.py: Problemas al importar uno o ambos agentes.")

except ImportError as e:
     print(f"ERROR CRITICO research_crew_definitions.py: No se pudo importar uno o ambos agentes. Error: {e}")
     researcher_agent = None
     editor_agent = None


def create_research_crew_and_kickoff(topic: str, content_to_analyze: Optional[str] = None) -> Optional[str]:
    """
    Crea y ejecuta el crew SECUENCIAL: Investigador -> Editor.
    Devuelve el informe FINAL EDITADO o un mensaje de error.
    """
    print(f"DEBUG create_research_crew...: Iniciando flujo Investigador->Editor para '{topic[:30]}...'")

    # Verificar que ambos agentes estén disponibles y operativos
    if not researcher_agent or "ERROR" in researcher_agent.role or not researcher_agent.tools:
        error_msg = "Error crítico: Agente Investigador no operativo (sin herramientas o error previo)."
        print(f"ERROR create_research_crew...: {error_msg}")
        return error_msg
    if not editor_agent:
        error_msg = "Error crítico: Agente Editor no disponible."
        print(f"ERROR create_research_crew...: {error_msg}")
        return error_msg

    # --- Definición de Tareas ---
    try:
        # Tarea 1: Investigación (como la teníamos antes)
        task1_description_parts = [
             f"1. Realizar una BÚSQUEDA WEB EXHAUSTIVA sobre: '{topic}'. Usa Tavily.",
             "2. Analizar resultados de búsqueda.",
        ]
        if content_to_analyze: task1_description_parts.append(f"3. Integrar y analizar CONTENIDO ADICIONAL: {content_to_analyze[:100]}...")
        else: task1_description_parts.append("3. (Sin contenido adicional proporcionado).")
        task1_description_parts.append("4. Generar un borrador de informe en Markdown con '## Resumen Ejecutivo' y '## Vías de Acción Sugeridas'.")
        
        research_task = Task(
            description="\n".join(task1_description_parts),
            expected_output="Un borrador de informe bien investigado y estructurado en Markdown.",
            agent=researcher_agent,
            # output_file="informe_borrador.md" # Opcional: guardar salida intermedia
        )
        print("DEBUG create_research_crew...: Tarea 1 'research_task' creada.")

        # Tarea 2: Edición (depende del resultado de la Tarea 1)
        # El resultado de research_task estará disponible en el contexto para editor_agent.
        editing_task = Task(
            description=(
                "1. Revisa CUIDADOSAMENTE el borrador del informe de investigación que te ha sido proporcionado (output de la tarea anterior).\n"
                "2. Edítalo para mejorar la claridad, la fluidez, la gramática y el estilo.\n"
                "3. Asegúrate de que el formato Markdown sea impecable y que las secciones (Resumen Ejecutivo, Vías de Acción) estén bien definidas.\n"
                "4. NO añadas nueva información ni cambies las conclusiones o vías de acción fundamentales, solo mejora la presentación y el lenguaje.\n"
                "5. El resultado final debe ser el informe pulido y listo para presentar."
            ),
            expected_output="El informe final de investigación, editado profesionalmente y formateado en Markdown.",
            agent=editor_agent,
            context=[research_task], # Indicar explícitamente que esta tarea usa el output de la anterior
            # output_file="informe_final_editado.md" # Opcional: guardar salida final
        )
        print("DEBUG create_research_crew...: Tarea 2 'editing_task' creada.")

    except Exception as e_task_def:
        error_msg = f"Error definiendo una de las tareas: {e_task_def}"
        print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
        return error_msg

    # --- Crear y Ejecutar el Crew con AMBOS Agentes y Tareas ---
    try:
        # Incluir ambos agentes y ambas tareas en el crew
        research_crew = Crew(
            agents=[researcher_agent, editor_agent], # Lista de agentes en orden si importa para selección automática (no en secuencial)
            tasks=[research_task, editing_task],     # Lista de tareas en orden de ejecución
            process=Process.sequential, # ASEGURAR que el proceso es secuencial
            verbose=True, # Mantener True para ver el proceso
        )
        print("DEBUG create_research_crew...: Crew SECUENCIAL (Investigador->Editor) creado.")
    except Exception as e_crew_def:
         error_msg = f"Error creando la instancia del Crew con 2 agentes/tareas: {e_crew_def}"
         print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
         return error_msg

    # Ejecutar el Crew
    crew_final_result: Optional[str] = None
    try:
        print(f"DEBUG create_research_crew...: Ejecutando crew.kickoff() (2 tareas). Input inicial 'topic'={topic[:30]}...")
        crew_inputs = {'topic': topic} # El input inicial es para la primera tarea (investigación)
        # El 'content_to_analyze' está embebido en la descripción de la primera tarea ahora.
        
        crew_final_result = research_crew.kickoff(inputs=crew_inputs)
        
        print(f"DEBUG create_research_crew...: Kickoff (2 tareas) finalizado.")
    except Exception as e_kickoff_seq:
        error_msg = f"Error durante crew.kickoff() (flujo secuencial): {type(e_kickoff_seq).__name__} - {e_kickoff_seq}"
        print(f"ERROR create_research_crew...: {error_msg}", exc_info=True)
        return error_msg

    # Devolver el resultado final (que debería ser el output de la Tarea 2: editing_task)
    if isinstance(crew_final_result, str) and crew_final_result.strip():
        print(f"DEBUG create_research_crew...: Devolviendo resultado FINAL EDITADO (len:{len(crew_final_result)}).")
        return crew_final_result
    else:
        print(f"WARN create_research_crew...: Kickoff finalizó sin un resultado de texto válido ({type(crew_final_result)}).")
        # Devolver un error o el último resultado parcial si CrewAI lo expusiera (más complejo)
        return "Error: El Crew finalizó pero no produjo el informe editado esperado."