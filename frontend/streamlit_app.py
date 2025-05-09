# frontend/streamlit_app.py
import streamlit as st
import requests
import os
import logging
from typing import Optional # <-- AÑADIR IMPORT

# Configuración Logger y URL Backend
logging.basicConfig(level=logging.INFO)
streamlit_logger = logging.getLogger(__name__)
st.set_page_config(page_title="Suite Agentes IA", layout="wide")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# --- Funciones API ---
def handle_api_error(err, endpoint_name):
    """Función helper para loguear y mostrar errores de API."""
    error_message = f"Error llamando a {endpoint_name}: {err}"
    try:
        if isinstance(err, requests.exceptions.HTTPError):
            error_detail = err.response.json().get("detail", err.response.text[:200])
            error_message = f"Error HTTP ({err.response.status_code}) en {endpoint_name}: {error_detail}"
    except Exception: pass
    st.error(error_message)
    streamlit_logger.error(error_message, exc_info=True if not isinstance(err, requests.exceptions.HTTPError) else False)
    return None

# Corregido con Optional
def conduct_research_request(topic: str, content: Optional[str]):
    """Llama al endpoint de investigación."""
    api_endpoint = f"{FASTAPI_URL}/research/conduct"
    payload = {"topic": topic, "content_to_analyze": content}
    streamlit_logger.info(f"POST {api_endpoint} - Tema: {topic[:30]}...")
    try:
        response = requests.post(api_endpoint, json=payload, timeout=420) # Timeout 7 mins
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return handle_api_error(e, "/research/conduct")

# Corregido con Optional
def query_memory_request(query: str) -> Optional[list]: # Añadir tipo de retorno opcional
    """Llama al endpoint de consulta de memoria."""
    api_endpoint = f"{FASTAPI_URL}/research/memory"
    params = {"query": query}
    streamlit_logger.info(f"GET {api_endpoint} - Query: {query}")
    try:
        response = requests.get(api_endpoint, params=params, timeout=60)
        response.raise_for_status()
        return response.json() # Devuelve lista si éxito
    except Exception as e:
        st.warning(f"No se pudo consultar la memoria: {e}")
        streamlit_logger.warning(f"Error API consulta memoria: {e}", exc_info=False)
        return None # Devuelve None si falla

# Corregido con Optional
def generate_marketing_content_request(topic: str, platform: str, context: Optional[str]):
    """Llama al nuevo endpoint de marketing."""
    api_endpoint = f"{FASTAPI_URL}/marketing/generate-content"
    payload = {"topic": topic, "platform": platform, "context": context}
    streamlit_logger.info(f"POST {api_endpoint} - Tema: {topic[:30]}, Plataforma: {platform}...")
    try:
        response = requests.post(api_endpoint, json=payload, timeout=300) # 5 minutos
        response.raise_for_status()
        return response.json()
    except Exception as e:
         return handle_api_error(e, "/marketing/generate-content")


# --- Interfaz Streamlit ---
st.title("🤖 Suite de Agentes Inteligentes IA (PoC)")
st.caption(f"Backend API: {FASTAPI_URL}")

tab_research, tab_memory, tab_marketing = st.tabs([
    "🔎 Investigación",
    "📚 Memoria",
    "📢 Marketing Contenido"
])

# --- Pestaña de Investigación ---
with tab_research:
    st.header("Agente Investigador + Editor")
    with st.form("new_research_form"):
        research_topic = st.text_input("Tema de la Investigación:", placeholder="Ej: Futuro del trabajo remoto")
        research_content = st.text_area("Contenido Base (Opcional):", height=150, placeholder="Pega texto aquí si quieres analizarlo junto con la búsqueda web.")
        submit_research_button = st.form_submit_button("🚀 Iniciar Investigación")

    if submit_research_button and research_topic:
        with st.spinner(f"🔎 Procesando investigación sobre '{research_topic}'..."):
            # Pasa None explícitamente si research_content está vacío
            api_result = conduct_research_request(research_topic, research_content if research_content and research_content.strip() else None)

        if api_result:
            st.success(api_result.get("message", "Proceso completado."))
            if api_result.get("report_gdrive_link"): st.markdown(f"📄 **Informe Final:** [Ver en Google Drive]({api_result['report_gdrive_link']})")
            if api_result.get("full_report_content"):
                with st.expander("Ver Contenido del Informe Final", expanded=False):
                    st.markdown(api_result["full_report_content"])
            # Mostrar memoria relevante (si existe y no está vacía)
            past_research = api_result.get("relevant_past_research")
            if past_research:
                st.divider(); st.subheader("Memoria Relevante:")
                for item in past_research:
                    topic=item.get("metadata", {}).get("topic", "?")
                    link=item.get("metadata", {}).get("gdrive_link", "#")
                    sim=item.get("similarity_score")
                    st.markdown(f"- **[{topic}]({link})** (Sim: {sim:.3f})" if sim else f"- **[{topic}]({link})**")

# --- Pestaña de Memoria ---
with tab_memory:
    st.header("Consultar Memoria de Investigaciones (ChromaDB)")
    memory_query = st.text_input("Buscar informes por tema:", placeholder="Ej: Energía solar")
    if st.button("🧠 Buscar en Memoria", key="memory_search_button") and memory_query:
        with st.spinner("Consultando memoria..."):
            memory_results = query_memory_request(memory_query)
        if memory_results:
             st.subheader(f"Resultados para '{memory_query}':")
             for item in memory_results:
                topic = item.get("metadata", {}).get("topic", "?")
                link = item.get("metadata", {}).get("gdrive_link", "#")
                sim = item.get("similarity_score")
                st.markdown(f"**[{topic}]({link})** (Sim: {sim:.3f})" if sim else f"**[{topic}]({link})**")
                with st.expander("Ver Resumen Guardado"):
                    st.caption(item.get("document_stored","(Sin resumen)"))
                st.divider()
        elif memory_results == []: st.info("No se encontraron resultados.")
        # Error ya manejado por handle_api_error si devuelve None

# --- Pestaña de Marketing ---
with tab_marketing:
    st.header("Agente Creador de Contenido de Marketing")
    st.markdown("Genera ideas, texto para posts y prompts para imágenes basado en un tema.")
    with st.form("marketing_content_form"):
        mk_topic = st.text_input("Tema Central o Producto:", placeholder="Ej: Nuestro nuevo curso online")
        mk_platform = st.selectbox("Plataforma Destino:", ("Instagram", "LinkedIn", "Twitter/X", "Facebook", "General"), index=0)
        mk_context = st.text_area("Contexto Adicional (Opcional):", placeholder="Ej: Audiencia: emprendedores. Objetivo: inscripciones.", height=100)
        submit_marketing_button = st.form_submit_button("✨ Generar Contenido de Marketing")

    if submit_marketing_button and mk_topic and mk_platform:
        with st.spinner(f"✍️ Creando contenido para '{mk_topic}' en {mk_platform}..."):
            # Pasa None explícitamente si mk_context está vacío
            mk_api_result = generate_marketing_content_request(mk_topic, mk_platform, mk_context if mk_context and mk_context.strip() else None)

        if mk_api_result:
            st.success(mk_api_result.get("message", "Contenido generado."))
            st.divider()
            ideas = mk_api_result.get("marketing_ideas")
            post = mk_api_result.get("post_text")
            prompt = mk_api_result.get("image_prompt")

            if ideas: st.subheader("💡 Ideas Sugeridas:"); st.markdown(ideas); st.divider()
            if post: st.subheader(f"✍️ Borrador de Post ({mk_platform}):"); st.text_area("Texto:", value=post, height=150, disabled=False, key="post_text_area"); st.divider() # Permitir copiar
            if prompt: st.subheader("🎨 Prompt de Imagen (DALL-E):"); st.code(prompt, language=None)
            if mk_api_result.get("error_details"): st.error(f"Problema reportado: {mk_api_result['error_details']}")
        # Error ya manejado por handle_api_error si devuelve None

# --- Sidebar ---
st.sidebar.header("Acerca de")
st.sidebar.info("PoC Suite Agentes IA v0.4\n- Agente Investigador (Web+Editor)\n- Agente Marketing Contenido\nOrquestado con CrewAI.")
st.sidebar.markdown("---")
st.sidebar.caption(f"API Backend: {FASTAPI_URL}")