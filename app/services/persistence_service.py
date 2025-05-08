# app/services/persistence_service.py
import chromadb
from chromadb.utils import embedding_functions # <--- AÑADIDO PARA DefaultEmbeddingFunction
from app.core.config import settings
import os
import uuid
import datetime # Importar datetime para el timestamp
from typing import Optional, List # <--- LÍNEA CLAVE

class PersistenceService:
    def __init__(self):
        self.collection = None
        self.initialization_error = None

        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.db_path_from_env = settings.CHROMA_DB_PATH if settings else "chroma_db_store_fallback"
        print(f"DEBUG PersistenceService init: DB path from env = {self.db_path_from_env}")

        if os.path.isabs(self.db_path_from_env):
            self.absolute_db_path = self.db_path_from_env
        else:
            self.absolute_db_path = os.path.join(self.project_root, self.db_path_from_env)
        
        print(f"DEBUG PersistenceService init: Absolute DB path = {self.absolute_db_path}")

        try:
            self.client = chromadb.PersistentClient(path=self.absolute_db_path)
            self.collection_name = "research_intelligence_v2" # Cambiado el nombre para forzar nueva colección si la v1 tuvo problemas

            # Usar explícitamente la función de embedding por defecto de ChromaDB
            # sentence-transformers/all-MiniLM-L6-v2 por defecto
            default_ef = embedding_functions.DefaultEmbeddingFunction()
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=default_ef # <--- AÑADIDO explícitamente
                # metadata={"hnsw:space": "cosine"} # Puedes añadir esto si sabes que usarás coseno y el embedding lo soporta
            )
            print(f"INFO PersistenceService: Conectado/Creado a la colección '{self.collection_name}' en '{self.absolute_db_path}' usando DefaultEmbeddingFunction.")
        except Exception as e:
            self.initialization_error = f"Error al inicializar/conectar ChromaDB con la colección '{self.collection_name}': {type(e).__name__} - {e}"
            print(f"ERROR PersistenceService: {self.initialization_error}")
            # self.collection permanece None

    def add_research_document(self, topic: str, summary: str, gdrive_id: str, gdrive_link: str, content_preview: str = "") -> Optional[str]:
        if not self.collection:
            error_msg = f"Colección ChromaDB ('{self.collection_name}') no inicializada. Error de init: {self.initialization_error or 'Desconocido'}"
            print(f"ERROR PersistenceService add_research_document: {error_msg}")
            return None
        
        doc_id = f"research_{uuid.uuid4()}"
        document_to_embed = f"Tema: {topic}\nResumen: {summary}"
        if content_preview:
            document_to_embed += f"\nContexto original (extracto): {content_preview[:500]}..."

        metadata = {
            "topic": topic,
            "source": "ResearchAgentViaCrewAI", # Actualizado para indicar el origen
            "gdrive_id": gdrive_id,
            "gdrive_link": gdrive_link,
            "type": "research_summary",
            "timestamp_utc": datetime.datetime.utcnow().isoformat() # Usar UTC para consistencia
        }
        
        try:
            self.collection.add(
                documents=[document_to_embed],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"INFO PersistenceService: Documento '{doc_id}' (Tema: {topic[:30]}...) añadido a ChromaDB.")
            return doc_id
        except Exception as e:
            print(f"ERROR PersistenceService: Error añadiendo documento '{doc_id}' a ChromaDB: {type(e).__name__} - {e}", exc_info=True)
            return None

    def query_similar_research(self, query_text: str, n_results: int = 3, where_filter: Optional[dict] = None) -> List[dict]:
        if not self.collection:
            error_msg = f"Colección ChromaDB ('{self.collection_name}') no inicializada. Error de init: {self.initialization_error or 'Desconocido'}"
            print(f"ERROR PersistenceService query_similar_research: {error_msg}")
            return []
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
                include=['metadatas', 'documents', 'distances']
            )
            
            processed_results = []
            ids_list = results.get('ids', [[]])[0] # [[id1, id2]] -> [id1, id2]
            docs_list = results.get('documents', [[]])[0]
            metas_list = results.get('metadatas', [[]])[0]
            dists_list = results.get('distances', [[]])[0]

            if ids_list:
                for i in range(len(ids_list)):
                    distance_val = dists_list[i] if dists_list and i < len(dists_list) else None
                    similarity_score_val = (1 - distance_val) if distance_val is not None else None
                    
                    processed_results.append({
                        "id": ids_list[i],
                        "document_stored": docs_list[i] if docs_list and i < len(docs_list) else None,
                        "metadata": metas_list[i] if metas_list and i < len(metas_list) else None,
                        "distance": distance_val,
                        "similarity_score": similarity_score_val,
                    })
            return processed_results
        except Exception as e:
            print(f"ERROR PersistenceService: Error consultando ChromaDB con texto '{query_text[:50]}...': {type(e).__name__} - {e}", exc_info=True)
            return []

# --- Bloque de prueba para ejecución directa (python -m app.services.persistence_service) ---
if __name__ == '__main__':
    print("DEBUG PersistenceService: Ejecutando prueba de PersistenceService (main block)...")
    ps = PersistenceService() # Instanciar el servicio

    if ps.collection:
        print(f"INFO PersistenceService (main test): Colección '{ps.collection_name}' disponible y operativa.")
        
        # Probar añadir un documento
        test_topic = "Impacto de la IA en la Educación del Siglo XXI"
        test_summary = "La inteligencia artificial está transformando los métodos de enseñanza, personalizando el aprendizaje y presentando nuevos desafíos éticos para educadores y estudiantes."
        test_gdrive_id = "gdrive123xyz_edu_test"
        test_gdrive_link = "https://example.com/drive/edu_test_doc"
        test_content_preview = "La IA permite adaptar los currículos a las necesidades individuales..."
        
        added_doc_id = ps.add_research_document(
            topic=test_topic,
            summary=test_summary,
            gdrive_id=test_gdrive_id,
            gdrive_link=test_gdrive_link,
            content_preview=test_content_preview
        )
        
        if added_doc_id:
             print(f"INFO PersistenceService (main test): Documento de prueba añadido con ID: {added_doc_id}")
        else:
            print("WARN PersistenceService (main test): No se pudo añadir el documento de prueba.")

        # Probar consultar el documento
        print(f"\nINFO PersistenceService (main test): Consultando por '{test_topic[:30]}...':")
        query_results_direct = ps.query_similar_research(test_topic, n_results=1)
        if query_results_direct:
            for res in query_results_direct:
                print(f"  Encontrado ID: {res['id']}")
                print(f"  Metadata: {res['metadata']}")
                sim = res.get('similarity_score')
                print(f"  Similitud: {sim:.4f}" if sim is not None else "N/A")
        else:
            print("  No se encontraron resultados directos para la prueba (o hubo un error en la consulta).")
        
        print(f"\nINFO PersistenceService (main test): Consultando por algo genérico como 'innovación':")
        query_results_generic = ps.query_similar_research("innovación tecnológica en aprendizaje", n_results=2)
        if query_results_generic:
            for res in query_results_generic:
                print(f"  Encontrado ID: {res['id']}")
                print(f"  Metadata: {res['metadata']}")
                sim = res.get('similarity_score')
                print(f"  Similitud: {sim:.4f}" if sim is not None else "N/A")
        else:
            print("  No se encontraron resultados para 'innovación' (o hubo un error en la consulta).")
            
    elif ps.initialization_error:
        print(f"ERROR PersistenceService (main test): No se pudo inicializar PersistenceService para la prueba. Error: {ps.initialization_error}")
    else:
        print("ERROR PersistenceService (main test): ps.collection es None, pero no hay initialization_error reportado. Estado inesperado.")
    
    print("DEBUG PersistenceService: Fin de la prueba de PersistenceService (main block).")