# frontend/streamlit_app.py
import streamlit as st
import requests 
import os
import logging # Usar logging también en Streamlit si es útil

# Configurar logging básico para Streamlit (opcional pero puede ayudar)
logging.basicConfig(level=logging.INFO)
streamlit_logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(page_title="🕵️ Agente de Investigación IA", layout="wide")

# URL del backend FastAPI
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# --- Funciones de ayuda para interactuar con el backend ---
def conduct_research_request(topic: str, content: str):
    api_endpoint = f"{FASTAPI_URL}/research/conduct"
    payload = {"topic": topic, "content_to_analyze": content}
    streamlit_logger.info(f"Enviando petición a {api_endpoint} con tema: {topic[:30]}...")
    try:
        response = requests.post(api_endpoint, json=payload, timeout=300)
        streamlit_logger.info(f"Respuesta recibida: {response.status_code}")
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_message = f"Error HTTP del API: {http_err.response.status_code}"
        try:
            error_detail = http_err.response.json().get("detail", str(http_err))
            error_message += f" - {error_detail}"
        except: # Si el cuerpo del error no es JSON
            error_message += f" - {http_err.response.text[:200]}" if hasattr(http_err.response, "text") else str(http_err)
        st.error(error_message)
        streamlit_logger.error(error_message, exc_info=True)
        return None
    except requests.exceptions.ConnectionError as conn_err:
        msg = f"Error de Conexión: No se pudo conectar al backend en {FASTAPI_URL}. ¿Está el backend corriendo? Detalle: {conn_err}"
        st.error(msg)
        streamlit_logger.error(msg, exc_info=True)
        return None
    except requests.exceptions.Timeout:
        msg = "Error: La solicitud al backend tardó demasiado (Timeout)."
        st.error(msg)
        streamlit_logger.error(msg)
        return None
    except Exception as e:
        msg = f"Ocurrió un error inesperado al contactar el backend: {e}"
        st.error(msg)
        streamlit_logger.error(msg, exc_info=True)
        return None

def query_memory_request(query: str):
    api_endpoint = f"{FASTAPI_URL}/research/memory"
    params = {"query": query}
    streamlit_logger.info(f"Enviando petición a {api_endpoint} con query: {query}")
    try:
        response = requests.get(api_endpoint, params=params, timeout=60)
        streamlit_logger.info(f"Respuesta recibida de memoria: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_message = f"Error HTTP del API (memoria): {http_err.response.status_code}"
        try:
            error_detail = http_err.response.json().get("detail", str(http_err))
            error_message += f" - {error_detail}"
        except:
             error_message += f" - {http_err.response.text[:200]}" if hasattr(http_err.response, "text") else str(http_err)
        st.warning(f"No se pudo consultar la memoria: {error_message}")
        streamlit_logger.warning(error_message)
        return None # Devolver None para indicar fallo, o [] si se prefiere lista vacía para "no encontrado"
    except Exception as e:
        st.warning(f"No se pudo consultar la memoria (otro error): {e}")
        streamlit_logger.warning(f"Error consultando memoria: {e}", exc_info=True)
        return None


# --- Interfaz de Streamlit ---
st.title("🕵️ Agente de Investigación IA")
st.caption("Impulsado por OpenAI, Google Drive, FastAPI y ChromaDB.")

tab_research, tab_memory = st.tabs(["🔎 Nueva Investigación", "📚 Consultar Memoria"])

with tab_research:
    st.header("Formulario de Investigación")
    with st.form("new_research_form"):
        research_topic = st.text_input(
            "Tema Principal:", 
            placeholder="Ej: El futuro de la IA en la atención médica",
            help="Introduce el tema que el agente debe investigar."
        )
        research_content = st.text_area(
            "Contenido Base (Input):", 
            height=250, 
            placeholder="Pega aquí un artículo, notas, o texto extenso que sirva como base para el análisis.",
            help="Este contenido será analizado y resumido por el agente."
        )
        submit_research_button = st.form_submit_button("🚀 Iniciar Investigación y Generar Informe")

    if submit_research_button:
        if not research_topic or not research_content:
            st.warning("⚠️ Por favor, completa el tema y el contenido base.")
        else:
            if len(research_content) < 50: # Validación de longitud mínima
                st.warning("⚠️ El contenido base parece demasiado corto. Por favor, proporciona más texto.")
            else:
                with st.spinner(f"🤖 Procesando investigación sobre '{research_topic}'..."):
                    api_result = conduct_research_request(research_topic, research_content)
                
                if api_result:
                    st.balloons() # ¡Pequeña celebración!
                    st.success(api_result.get("message", "Investigación procesada."))
                    
                    if api_result.get("report_gdrive_link"):
                        st.markdown(f"🔗 **Informe en Google Drive:** [{api_result.get('topic', 'Ver Informe')}]({api_result['report_gdrive_link']})")
                    
                    if api_result.get("local_fallback_path"):
                        st.info(f"ℹ️ El informe también se guardó localmente en el servidor en: `{api_result['local_fallback_path']}` (esto es un fallback si GDrive falló inicialmente pero el agente continuó).")

                    report_display_content = api_result.get("full_report_content")
                    if not report_display_content:
                        report_display_content = api_result.get("report_summary_for_db", "No hay resumen disponible.")

                    with st.expander("📄 Ver Contenido del Informe Generado", expanded=True):
                        st.markdown(report_display_content)
                    
                    if api_result.get("error_details"): # Si la API devuelve un error manejado por el agente
                        st.error(f"El agente reportó un problema: {api_result['error_details']}")
                    
                    past_research = api_result.get("relevant_past_research")
                    if past_research:
                        st.markdown("---")
                        st.subheader("💡 Investigaciones Anteriores Relacionadas (de la memoria):")
                        for item in past_research:
                            item_topic = item.get("metadata", {}).get("topic", "Desconocido")
                            gdrive_link = item.get("metadata", {}).get("gdrive_link")
                            similarity = item.get("similarity_score")
                            dist = item.get("distance")
                            
                            display_text = f"**{item_topic}**"
                            if gdrive_link: display_text += f" ([Drive]({gdrive_link}))"
                            if similarity is not None: display_text += f" - Sim: {similarity:.2f}"
                            elif dist is not None: display_text += f" - Dist: {dist:.2f}"
                            
                            st.markdown(display_text)
                            with st.expander("Ver resumen de memoria", expanded=False):
                                st.caption(item.get("document_stored", "N/A"))
                # No es necesario un 'else' aquí porque conduct_research_request ya muestra st.error


with tab_memory:
    st.header("Búsqueda en la Memoria de Investigaciones")
    memory_query = st.text_input("Buscar por tema o palabras clave:", placeholder="Ej: Ciberseguridad cuántica")
    
    if st.button("🧠 Buscar en Memoria") and memory_query:
        with st.spinner("Consultando la base de datos de vectores..."):
            memory_results = query_memory_request(memory_query)
        
        st.subheader(f"Resultados para: '{memory_query}'")
        if memory_results:
            for item in memory_results:
                topic = item.get("metadata", {}).get("topic", "Tópico Desconocido")
                gdrive_link = item.get("metadata", {}).get("gdrive_link", "#")
                similarity = item.get("similarity_score")
                dist = item.get("distance")
                doc_stored = item.get("document_stored", "No hay resumen.")
                
                col1, col2 = st.columns([3,1])
                with col1:
                    st.markdown(f"##### [{topic}]({gdrive_link})")
                    st.caption(f"Fuente: {item.get('metadata', {}).get('source', 'N/A')} | Tipo: {item.get('metadata', {}).get('type', 'N/A')}")
                    st.expander("Ver resumen almacenado").markdown(doc_stored)
                with col2:
                    if similarity is not None: st.metric(label="Similitud", value=f"{similarity:.3f}")
                    elif dist is not None: st.metric(label="Distancia", value=f"{dist:.3f}")
                st.markdown("---")
        elif memory_results == []: # API devolvió lista vacía (no error, solo sin resultados)
            st.info("ℹ️ No se encontraron informes relevantes en la memoria para tu consulta.")
        # else: # memory_results es None (hubo un error en la petición, ya mostrado por query_memory_request)
        #     st.warning("No se pudo obtener respuesta del servicio de memoria.")


st.sidebar.header("Acerca de")
st.sidebar.info(
    "PoC del Agente de Investigación IA v0.3\n\n"
    "Permite generar informes de investigación basados en un tema y contenido, "
    "guardarlos en Google Drive y consultarlos desde una memoria vectorial (ChromaDB)."
)
st.sidebar.markdown("---")
st.sidebar.caption(f"API Backend: {FASTAPI_URL}")