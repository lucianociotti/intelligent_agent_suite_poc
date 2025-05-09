# app/crews/marketing_crew_definitions.py
# VERSIÓN CORREGIDA: Error de print() con exc_info solucionado.

from crewai import Task, Crew, Process
from typing import Optional, Dict, Any # Importar Dict y Any
import logging # Importar logging

logger = logging.getLogger(__name__) # Usar el logger del módulo
logger.setLevel(logging.INFO) # O DEBUG para más detalle

try:
    from app.agents_crewai.crew_agents import marketing_content_agent
    logger.debug("marketing_crew_definitions.py: Importando 'marketing_content_agent'...")
    if not marketing_content_agent or "ERROR" in marketing_content_agent.role:
         logger.warning("marketing_crew_definitions.py: 'marketing_content_agent' importado en estado de error o no definido.")
    elif not marketing_content_agent.tools:
         logger.warning("marketing_crew_definitions.py: 'marketing_content_agent' importado sin herramientas.")
    else:
        tool_names = [t.name for t in marketing_content_agent.tools if hasattr(t, 'name')]
        logger.debug(f"marketing_crew_definitions.py: 'marketing_content_agent' importado con herramientas: {tool_names}")
except ImportError as e:
    logger.critical(f"marketing_crew_definitions.py: No se pudo importar 'marketing_content_agent'. Error: {e}", exc_info=True)
    marketing_content_agent = None
except Exception as e_agent_load: # Captura general si algo más falla al cargar el agente
    logger.critical(f"marketing_crew_definitions.py: Excepción inesperada importando 'marketing_content_agent'. Error: {e_agent_load}", exc_info=True)
    marketing_content_agent = None


# Asumir que DallETool tiene este nombre si se instancia correctamente desde crewai_tools
DALL_E_TOOL_NAME = "DALL-E Tool" # Nombre por defecto de DallETool de crewai_tools


def create_marketing_content_crew_and_kickoff(
    topic: str,
    platform: str,
    context: Optional[str] = None,
    generate_image: bool = False,
) -> Dict[str, Any]: # Devuelve Dict para estructura clara
    """
    Crea y ejecuta el crew de contenido de marketing.
    Devuelve un diccionario con artefactos: ideas, post, prompt_imagen, [url_imagen], o error.
    """
    logger.info(f"create_marketing_content_crew: Iniciando para '{topic[:30]}' en '{platform}', Generar Imagen: {generate_image}")

    if not marketing_content_agent or "ERROR" in marketing_content_agent.role or not marketing_content_agent.tools:
        error_msg = "Error crítico: Agente de Marketing no está disponible, en estado de error, o no tiene herramientas funcionales."
        logger.error(f"create_marketing_content_crew: {error_msg}")
        return {"error": error_msg, "ideas": None, "post_text": None, "image_prompt": None, "generated_image_url": None}

    tool_names_in_agent = [t.name for t in marketing_content_agent.tools if hasattr(t, 'name')]
    required_text_tools = [
        "Generador de Ideas de Marketing",
        "Redactor de Posts para Redes Sociales",
        "Generador de Prompts para DALL-E"
    ]
    if not all(req_tool in tool_names_in_agent for req_tool in required_text_tools):
        error_msg = f"Error: Agente marketing no tiene tools de texto requeridas. Necesita: {required_text_tools}. Tiene: {tool_names_in_agent}"
        logger.error(f"create_marketing_content_crew: {error_msg}")
        return {"error": error_msg, "ideas": None, "post_text": None, "image_prompt": None, "generated_image_url": None}
    
    dalle_tool_is_loaded = DALL_E_TOOL_NAME in tool_names_in_agent
    if generate_image and not dalle_tool_is_loaded:
         logger.warning(f"create_marketing_content_crew: Se solicitó imagen, pero DallETool ('{DALL_E_TOOL_NAME}') no está en agente. Se omitirá generación de imagen.")
         generate_image = False

    # --- Definir Tareas ---
    tasks_for_crew = []
    try:
        task_inputs_ideas = {'topic': topic}
        if context: task_inputs_ideas['context'] = context

        generate_ideas_task = Task(
            description=f"Realizar un brainstorming exhaustivo de ideas de marketing (conceptos de contenido, tipos de post, hashtags relevantes, llamadas a la acción efectivas) para el tema/producto principal: '{topic}'. Si se proporciona 'contexto adicional', debe ser utilizado para refinar y enfocar estas ideas. Producir una lista clara y accionable.",
            expected_output="Una lista formateada con al menos 5 ideas de marketing distintas y bien detalladas, cada una incluyendo: Ángulo/Concepto, Tipo de Contenido Sugerido, Hashtags Propuestos y CTA Sugerido.",
            agent=marketing_content_agent,
            tools=[tool for tool in marketing_content_agent.tools if getattr(tool,'name', '') == "Generador de Ideas de Marketing"]
        )
        tasks_for_crew.append(generate_ideas_task)

        write_post_task = Task(
            description=f"Utilizando las ideas de marketing generadas en la tarea anterior y el tema original ('{topic}'), redactar un borrador de post atractivo y optimizado para la plataforma de red social: '{platform}'. Asegurarse de adaptar el tono, la longitud y el formato del texto a las mejores prácticas de '{platform}'. Incluir emojis y hashtags si es pertinente. El contexto original es: {context if context else 'No se proporcionó contexto adicional.'}",
            expected_output=f"El texto completo y listo para ser utilizado del post para la plataforma '{platform}'.",
            agent=marketing_content_agent,
            context=[generate_ideas_task],
            tools=[tool for tool in marketing_content_agent.tools if getattr(tool,'name', '') == "Redactor de Posts para Redes Sociales"]
        )
        tasks_for_crew.append(write_post_task)

        suggest_prompt_task = Task(
            description="A partir del texto del post de red social redactado en la tarea anterior, generar un prompt altamente descriptivo y efectivo para ser utilizado con un modelo de IA de generación de imágenes como DALL-E. El prompt debe capturar la esencia visual del mensaje y guiar a la IA para crear una imagen impactante y relevante.",
            expected_output="Un único string que contenga el prompt sugerido y optimizado para la generación de imágenes.",
            agent=marketing_content_agent,
            context=[write_post_task],
            tools=[tool for tool in marketing_content_agent.tools if getattr(tool,'name', '') == "Generador de Prompts para DALL-E"]
        )
        tasks_for_crew.append(suggest_prompt_task)

        if generate_image and dalle_tool_is_loaded:
            generate_image_task = Task(
                description=(
                    "Utilizar el prompt de DALL-E generado en la tarea anterior (output de 'suggest_prompt_task') "
                    "para crear una imagen. Utiliza la herramienta DALL-E. El resultado debe ser la URL o la representación de la imagen."
                ),
                expected_output="La URL directa de la imagen generada por DALL-E. Si ocurre un error durante la generación, devolver un mensaje descriptivo del error.",
                agent=marketing_content_agent,
                context=[suggest_prompt_task],
                tools=[tool for tool in marketing_content_agent.tools if getattr(tool, 'name', '') == DALL_E_TOOL_NAME]
            )
            tasks_for_crew.append(generate_image_task)
            logger.info("create_marketing_content_crew: Tarea de Generación de Imagen DALL-E AÑADIDA al plan.")
        
        logger.debug("create_marketing_content_crew: Todas las tareas de marketing definidas.")
    except Exception as e_task_def_mk:
        logger.error(f"Error definiendo tareas marketing: {e_task_def_mk}", exc_info=True)
        return {"error": f"Error definiendo tareas marketing: {e_task_def_mk}"}


    # --- Crear y Ejecutar el Crew ---
    try:
        marketing_crew = Crew(agents=[marketing_content_agent], tasks=tasks_for_crew, process=Process.sequential, verbose=True)
        logger.info(f"Crew de marketing creado con {len(tasks_for_crew)} tareas.")
    except Exception as e_crew_cr_mk:
        logger.error(f"Error creando Crew de marketing: {e_crew_cr_mk}", exc_info=True)
        return {"error": f"Error creando Crew de marketing: {e_crew_cr_mk}"}

    final_crew_output_dict: Dict[str, Any] = { # Inicializar diccionario de resultados
        "ideas": None, "post_text": None, "image_prompt": None, "generated_image_url": None, "error": None
    }
    try:
        logger.info(f"Ejecutando kickoff marketing crew. Inputs iniciales para 1ra tarea: {task_inputs_ideas}")
        # kickoff devuelve el resultado de la ÚLTIMA tarea en un proceso secuencial.
        # Los outputs de tareas intermedias se acceden a través de las instancias de Task.
        crew_kickoff_result = marketing_crew.kickoff(inputs=task_inputs_ideas)
        logger.info(f"Kickoff Marketing Crew finalizado. El output de la última tarea fue de tipo: {type(crew_kickoff_result)}")

        # Extraer los outputs de CADA tarea después del kickoff
        final_crew_output_dict["ideas"] = generate_ideas_task.output.raw_output if generate_ideas_task.output else "No se generaron ideas."
        final_crew_output_dict["post_text"] = write_post_task.output.raw_output if write_post_task.output else "No se generó texto de post."
        final_crew_output_dict["image_prompt"] = suggest_prompt_task.output.raw_output if suggest_prompt_task.output else "No se generó prompt de imagen."
        
        if generate_image and dalle_tool_is_loaded and 'generate_image_task' in locals():
            image_task_output = tasks_for_crew[-1].output # Acceder a la última tarea (la de imagen)
            if image_task_output and image_task_output.raw_output:
                 final_crew_output_dict["generated_image_url"] = image_task_output.raw_output
                 logger.info(f"URL de imagen recuperada de la tarea DALL-E: {image_task_output.raw_output}")
            else:
                 logger.warning("Tarea de imagen DALL-E ejecutada pero no se encontró 'raw_output' válido.")
                 final_crew_output_dict["generated_image_url"] = "Fallo al recuperar URL de imagen."
        
        # Por si acaso, el crew_kickoff_result es el output de la última tarea
        # Podríamos añadirlo o compararlo. Aquí lo usamos para debug
        logger.debug(f"Output directo de crew.kickoff (última tarea): {str(crew_kickoff_result)[:200]}...")

        return final_crew_output_dict

    except Exception as e_kickoff_mk: # CORREGIDO AQUÍ: Usar logger.error
        error_msg = f"Error durante marketing_crew.kickoff(): {type(e_kickoff_mk).__name__} - {e_kickoff_mk}"
        logger.error(f"create_marketing_content_crew: {error_msg}", exc_info=True)
        final_crew_output_dict["error"] = error_msg
        return final_crew_output_dict