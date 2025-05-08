# app/agents/research_agent.py
import openai
import os
import datetime
import re # <--- IMPORTANTE: Añadir import re
from app.core.config import settings
from app.services.gdrive_service import GDriveService
from app.services.persistence_service import PersistenceService

# Verificar que settings.OPENAI_API_KEY tiene un valor antes de asignarlo
if not settings.OPENAI_API_KEY:
    print("ERROR CRÍTICO research_agent.py: La clave API de OpenAI no está configurada en settings.")
    openai.api_key = None # Asegurar que es None si no está configurado
else:
    openai.api_key = settings.OPENAI_API_KEY
    print(f"DEBUG research_agent.py: OpenAI API Key configurada: {bool(openai.api_key)}")


class ResearchAgent:
    def __init__(self, gdrive_service: GDriveService, persistence_service: PersistenceService):
        self.gdrive_service = gdrive_service
        self.persistence_service = persistence_service
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        print(f"DEBUG ResearchAgent init: Project root calculado como: {self.project_root}")

    def _sanitize_filename(self, filename_base: str) -> str:
        """
        Limpia una cadena para que sea un nombre de archivo válido,
        reemplazando caracteres no permitidos y espacios.
        """
        if not filename_base: # Manejar cadena vacía
            return "documento_sin_titulo"
        # Reemplazar espacios y múltiples guiones bajos/puntos problemáticos primero
        s = filename_base.replace(' ', '_')
        # Eliminar caracteres no alfanuméricos excepto guiones bajos, puntos e hifen
        # \w incluye letras, números y guion bajo.
        s = re.sub(r'[^\w.\-]', '', s)
        # Reemplazar múltiples guiones bajos o puntos con uno solo
        s = re.sub(r'_{2,}', '_', s) # 2 o más _ con uno solo
        s = re.sub(r'\.{2,}', '.', s) # 2 o más . con uno solo
        # Eliminar guiones bajos o puntos al principio o al final de la cadena
        s = s.strip('_.')
        # Si después de sanitizar queda vacío (ej. solo tenía "???"), dar un nombre por defecto.
        if not s:
            s = "documento_procesado"
        # Limitar la longitud para evitar nombres de archivo excesivamente largos
        return s[:100] # Limitar a 100 caracteres (ajustable)

    def _generate_research_prompt(self, topic: str, content_to_analyze: str) -> str:
        return f"""
Eres un consultor estratégico y analista de investigación senior. Tu tarea es analizar el contenido proporcionado sobre un tema específico y generar un informe conciso que incluya un resumen ejecutivo y vías de acción claras.

**Tema de Investigación:** {topic}

**Contenido a Analizar:**
---
{content_to_analyze}
---

**Formato de Respuesta Solicitado (USA MARKDOWN):**

# Informe de Investigación: {topic}

## Resumen Ejecutivo
[Proporciona aquí un resumen claro, conciso y bien estructurado del contenido analizado. Destaca los puntos más importantes y las conclusiones clave. Debe ser comprensible por sí solo.]

## Vías de Acción Sugeridas
[Basándote en el tema y el resumen ejecutivo, identifica y describe entre 3 y 5 vías de acción concretas, estrategias o áreas de enfoque recomendadas. Para cada vía de acción, incluye un título descriptivo y una breve explicación de su relevancia y potencial impacto.]

**Ejemplo de Vía de Acción:**
### 1. **Nombre de la Vía de Acción 1:**
   [Descripción detallada de la vía de acción, por qué es importante y qué se podría hacer.]

### 2. **Nombre de la Vía de Acción 2:**
   [Descripción detallada...]

(Y así sucesivamente)

Asegúrate de que el informe sea profesional, esté bien organizado y sea directamente utilizable para la toma de decisiones.
"""

    def conduct_research(self, topic: str, content_to_analyze: str) -> dict:
        print(f"INFO ResearchAgent: Iniciando investigación sobre '{topic}'...")

        prompt = self._generate_research_prompt(topic, content_to_analyze)
        if not openai.api_key: # Doble chequeo, por si acaso.
            error_msg = "Error de configuración: La clave API de OpenAI no está asignada al cliente de OpenAI."
            print(f"ERROR ResearchAgent: {error_msg}")
            return {"error": error_msg, "report_gdrive_link": None, "report_summary_for_db": None}
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Eres un asistente de investigación de alta calidad."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=2000
            )
            generated_report_content = response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = f"Error al contactar OpenAI: {e}"
            print(f"ERROR ResearchAgent: {error_msg}")
            return {"error": error_msg, "report_gdrive_link": None, "report_summary_for_db": None}

        print("INFO ResearchAgent: Informe generado por IA.")

        report_summary_for_db = "No se pudo extraer el resumen ejecutivo." # Default
        try:
            if "## Resumen Ejecutivo" in generated_report_content:
                summary_start_idx = generated_report_content.find("## Resumen Ejecutivo") + len("## Resumen Ejecutivo")
                vias_accion_idx = generated_report_content.find("## Vías de Acción Sugeridas", summary_start_idx)
                
                if vias_accion_idx != -1: # Si se encuentra "Vías de Acción"
                    report_summary_for_db = generated_report_content[summary_start_idx:vias_accion_idx].strip()
                else: # Si no, tomar todo lo que sigue a "Resumen Ejecutivo"
                    report_summary_for_db = generated_report_content[summary_start_idx:].strip()
            else: # Fallback si "Resumen Ejecutivo" no está
                report_summary_for_db = generated_report_content.split('\n\n', 1)[0] # Tomar el primer párrafo
            report_summary_for_db = report_summary_for_db[:1000] # Limitar para la BD vectorial
        except Exception as parse_e:
            print(f"WARN ResearchAgent: No se pudo parsear el resumen ejecutivo del informe: {parse_e}")
            report_summary_for_db = generated_report_content[:1000]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_topic = self._sanitize_filename(topic) # <--- USAR LA FUNCIÓN DE SANITIZACIÓN
        
        # Nombre de archivo para Google Drive y también para el fallback local
        base_filename = f"Informe_{sanitized_topic}_{timestamp}.md"
        print(f"DEBUG ResearchAgent: Nombre de archivo base sanitizado: {base_filename}")

        if not self.gdrive_service or not self.gdrive_service.service:
             error_msg = f"Servicio de Google Drive no disponible. No se pudo guardar el informe. Error GDrive Init: {getattr(self.gdrive_service, 'initialization_error', 'No disponible') if self.gdrive_service else 'Servicio no instanciado'}"
             print(f"ERROR ResearchAgent: {error_msg}")
             return {"error": error_msg, "report_gdrive_link": None, "report_summary_for_db": report_summary_for_db}

        gdrive_upload_result = self.gdrive_service.upload_text_as_md(generated_report_content, base_filename)

        local_fallback_path = None # Inicializar
        if gdrive_upload_result.get("error"):
            error_msg = f"Error al guardar informe en Google Drive: {gdrive_upload_result['error']}"
            print(f"ERROR ResearchAgent: {error_msg}")
            
            local_fallback_path = os.path.join(self.project_root, settings.REPORTS_DIR, base_filename) # Usar el nombre base sanitizado
            try:
                with open(local_fallback_path, "w", encoding="utf-8") as f:
                    f.write(generated_report_content)
                print(f"INFO ResearchAgent: Informe guardado localmente como fallback en: {local_fallback_path}")
            except Exception as e_fallback:
                print(f"ERROR ResearchAgent: Falló también el guardado local de fallback ('{local_fallback_path}'): {e_fallback}")
                local_fallback_path = None # Resetear si falla el guardado local
            
            return {
                "error": error_msg, 
                "report_gdrive_link": None, 
                "local_fallback_path": local_fallback_path, 
                "report_summary_for_db": report_summary_for_db
            }
        
        gdrive_link = gdrive_upload_result.get("webViewLink")
        gdrive_id = gdrive_upload_result.get("id")
        print(f"INFO ResearchAgent: Informe '{base_filename}' guardado en Google Drive: {gdrive_link}")

        if self.persistence_service and self.persistence_service.collection:
            print("DEBUG ResearchAgent: Intentando guardar en PersistenceService...")
            self.persistence_service.add_research_document(
                topic=topic, # Guardar el topic original, no el sanitizado, para búsquedas
                summary=report_summary_for_db,
                gdrive_id=gdrive_id,
                gdrive_link=gdrive_link,
                content_preview=content_to_analyze[:500]
            )
            print("INFO ResearchAgent: Metadatos del informe guardados en la base de datos de vectores.")
        elif not self.persistence_service:
             print("WARN ResearchAgent: PersistenceService no fue provisto al agente.")
        elif not self.persistence_service.collection:
             print(f"WARN ResearchAgent: PersistenceService.collection no está disponible (Error ChromaDB Init: {getattr(self.persistence_service, 'initialization_error', 'No disponible')}).")
        
        return {
            "message": "Investigación completada e informe guardado en Google Drive.",
            "topic": topic,
            "full_report_content": generated_report_content,
            "report_gdrive_link": gdrive_link,
            "report_gdrive_id": gdrive_id,
            "report_summary_for_db": report_summary_for_db,
            "error": None
        }

# --- Bloque de prueba para ejecución por consola ---
if __name__ == '__main__':
    print("DEBUG research_agent.py: Entrando en el bloque if __name__ == '__main__'")
    print("Ejecutando prueba del Agente de Investigación...")
    
    gdrive_serv = None
    persistence_serv = None
    agent = None

    try:
        print("DEBUG research_agent.py (main): Intentando instanciar GDriveService...")
        gdrive_serv = GDriveService()
        print(f"DEBUG research_agent.py (main): GDriveService instanciado. Servicio: {'OK' if gdrive_serv and gdrive_serv.service else 'FALLÓ o no inicializado completamente'}")
        if gdrive_serv and not gdrive_serv.service and hasattr(gdrive_serv, 'initialization_error'):
             print(f"DEBUG research_agent.py (main): Error de inicialización GDrive: {gdrive_serv.initialization_error}")
    except FileNotFoundError as e_fnf:
        print(f"ERROR CRÍTICO DE CONFIGURACIÓN (FileNotFoundError) en research_agent.py (main): {e_fnf}")
        print("Asegúrate de que el archivo de credenciales de Google Drive exista y la ruta en .env sea correcta.")
        exit()
    except Exception as e_gdrive:
        print(f"ERROR al instanciar GDriveService en research_agent.py (main): {e_gdrive}")
        import traceback
        traceback.print_exc()

    try:
        print("DEBUG research_agent.py (main): Intentando instanciar PersistenceService...")
        persistence_serv = PersistenceService()
        print(f"DEBUG research_agent.py (main): PersistenceService instanciado. Colección: {'OK' if persistence_serv and persistence_serv.collection else 'FALLÓ o no inicializado'}")
        if persistence_serv and not persistence_serv.collection and hasattr(persistence_serv, 'initialization_error'):
            print(f"DEBUG research_agent.py (main): Error de inicialización ChromaDB: {persistence_serv.initialization_error}")
    except Exception as e_persist:
        print(f"ERROR al instanciar PersistenceService en research_agent.py (main): {e_persist}")
        import traceback
        traceback.print_exc()

    if gdrive_serv and hasattr(gdrive_serv, 'service') and gdrive_serv.service and \
       persistence_serv and hasattr(persistence_serv, 'collection') and persistence_serv.collection:
        try:
            print("DEBUG research_agent.py (main): Intentando instanciar ResearchAgent...")
            agent = ResearchAgent(gdrive_service=gdrive_serv, persistence_service=persistence_serv)
            print("DEBUG research_agent.py (main): ResearchAgent instanciado OK.")
            
            sample_topic = "Mascotas: ¿gatos o perros? Beneficios y desventajas" # Tema con '?'
            sample_content_to_analyze = """
            La elección entre tener un gato o un perro como mascota es una decisión personal
            que depende de muchos factores, incluyendo el estilo de vida, el espacio disponible y 
            las preferencias individuales. Los perros suelen requerir más atención, ejercicio y 
            entrenamiento, pero ofrecen una compañía muy leal y activa. Los gatos, por otro lado, 
            son generalmente más independientes, requieren menos espacio y pueden ser ideales 
            para personas con horarios ocupados. Sin embargo, ambos ofrecen amor incondicional.
            Los costos de veterinario, alimentación y cuidados generales también varían.
            """
            
            print(f"\nDEBUG research_agent.py (main): Solicitando investigación sobre: '{sample_topic}'")
            result = agent.conduct_research(sample_topic, sample_content_to_analyze)
            
            if result.get("error"):
                print(f"\n--- ERROR EN LA PRUEBA ---")
                print(f"Error: {result['error']}")
                if result.get("local_fallback_path"):
                    print(f"Informe de fallback guardado en: {result['local_fallback_path']}")
            else:
                print(f"\n--- RESULTADO DE LA PRUEBA ---")
                print(result.get("message"))
                print(f"Enlace de Google Drive: {result.get('report_gdrive_link')}")

                print("\nDEBUG research_agent.py (main): Intentando consultar la persistencia por un tema similar...")
                if persistence_serv and persistence_serv.collection:
                    similar_results = persistence_serv.query_similar_research("Beneficios de tener mascotas", n_results=1)
                    if similar_results:
                        print("DEBUG research_agent.py (main): Documentos similares encontrados en ChromaDB:")
                        for sr in similar_results:
                            metadata = sr.get('metadata', {})
                            print(f"  ID: {sr.get('id')}, Tema: {metadata.get('topic', 'N/A')}, Enlace GDrive: {metadata.get('gdrive_link', 'N/A')}")
                    else:
                        print("DEBUG research_agent.py (main): No se encontraron documentos similares.")
                else:
                    print("WARN research_agent.py (main): No se puede consultar la persistencia, servicio o colección no disponibles.")

        except Exception as e_agent_logic:
            print(f"ERROR durante la lógica principal de prueba del Agente de Investigación: {e_agent_logic}")
            import traceback
            traceback.print_exc()
    else:
        print("ADVERTENCIA en research_agent.py (main): No se ejecutó la lógica principal del agente porque uno o más servicios (GDrive, Persistencia) no se inicializaron correctamente.")
        if not (gdrive_serv and hasattr(gdrive_serv, 'service') and gdrive_serv.service):
            print("  - Problema con GDriveService.")
        if not (persistence_serv and hasattr(persistence_serv, 'collection') and persistence_serv.collection):
            print("  - Problema con PersistenceService (ChromaDB).")

    print("DEBUG research_agent.py (main): Fin del bloque if __name__ == '__main__'")