# app/services/persistence_service.py
import chromadb
from app.core.config import settings # Importa la instancia 'settings'
import os
import uuid

class PersistenceService:
    def __init__(self):
        self.collection = None # Inicializar a None
        self.initialization_error = None

        # La raíz del proyecto, calculada desde la ubicación de ESTE archivo
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.db_path_from_env = settings.CHROMA_DB_PATH # ej: "chroma_db_store"
        print(f"DEBUG PersistenceService init: DB path from env = {self.db_path_from_env}")

        # Construir ruta absoluta a la carpeta de ChromaDB
        if os.path.isabs(self.db_path_from_env):
            self.absolute_db_path = self.db_path_from_env
        else:
            self.absolute_db_path = os.path.join(self.project_root, self.db_path_from_env)
        
        print(f"DEBUG PersistenceService init: Absolute DB path = {self.absolute_db_path}")

        # ChromaDB crea el directorio si no existe, así que no necesitamos os.makedirs explícito aquí,
        # pero nos aseguramos de que la ruta base exista si CHROMA_DB_PATH es algo como "data/chroma"
        # os.makedirs(os.path.dirname(self.absolute_db_path), exist_ok=True) # Si db_path tuviera subcarpetas

        self.client = chromadb.PersistentClient(path=self.absolute_db_path) # Chroma manejará la creación del dir
        self.collection_name = "research_intelligence"
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                # metadata={"hnsw:space": "cosine"} # Opcional, depende de tus embeddings
            )
            print(f"INFO PersistenceService: Conectado/Creado a la colección '{self.collection_name}' en '{self.absolute_db_path}'")
        except Exception as e:
            self.initialization_error = f"Error al inicializar/conectar ChromaDB con la colección '{self.collection_name}': {e}"
            print(f"ERROR PersistenceService: {self.initialization_error}")
            # self.collection permanece None

    def add_research_document(self, topic: str, summary: str, gdrive_id: str, gdrive_link: str, content_preview: str = ""):
        if not self.collection:
            error_msg = f"Colección ChromaDB ('{self.collection_name}') no inicializada. Error: {self.initialization_error or 'Desconocido'}"
            print(f"ERROR PersistenceService add_research_document: {error_msg}")
            return None # Devolver None en lugar de False para el ID
        
        doc_id = f"research_{uuid.uuid4()}"
        document_to_embed = f"Tema: {topic}\nResumen: {summary}"
        if content_preview:
            document_to_embed += f"\nContexto original (extracto): {content_preview[:500]}..."

        metadata = {
            "topic": topic,
            "source": "ResearchAgent", # De dónde vino este dato
            "gdrive_id": gdrive_id,
            "gdrive_link": gdrive_link,
            "type": "research_summary", # Tipo de documento
            "timestamp": datetime.datetime.now().isoformat() # Añadir timestamp
        }
        
        try:
            self.collection.add(
                documents=[document_to_embed],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"INFO PersistenceService: Documento de investigación '{doc_id}' (Tema: {topic}) añadido a ChromaDB.")
            return doc_id # Devolver el ID del documento añadido
        except Exception as e:
            print(f"ERROR PersistenceService: Error añadiendo documento '{doc_id}' a ChromaDB: {e}")
            return None

    def query_similar_research(self, query_text: str, n_results: int = 3, where_filter: dict = None) -> list:
        if not self.collection:
            error_msg = f"Colección ChromaDB ('{self.collection_name}') no inicializada. Error: {self.initialization_error or 'Desconocido'}"
            print(f"ERROR PersistenceService query_similar_research: {error_msg}")
            return []
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter, # Para filtrar por metadatos, ej: {"type": "research_summary"}
                include=['metadatas', 'documents', 'distances']
            )
            
            processed_results = []
            # Chroma devuelve listas anidadas, incluso para una sola query_text
            ids_list = results.get('ids', [[]])[0]
            docs_list = results.get('documents', [[]])[0]
            metas_list = results.get('metadatas', [[]])[0]
            dists_list = results.get('distances', [[]])[0]

            if ids_list: # Si hay resultados
                for i in range(len(ids_list)):
                    processed_results.append({
                        "id": ids_list[i],
                        "document_stored": docs_list[i] if docs_list and i < len(docs_list) else None,
                        "metadata": metas_list[i] if metas_list and i < len(metas_list) else None,
                        "distance": dists_list[i] if dists_list and i < len(dists_list) else None,
                        "similarity_score": (1 - dists_list[i]) if (dists_list and i < len(dists_list) and dists_list[i] is not None) else None,
                    })
            return processed_results
        except Exception as e:
            print(f"ERROR PersistenceService: Error consultando ChromaDB con texto '{query_text}': {e}")
            return []

import datetime # Necesario para el timestamp en add_research_document

if __name__ == '__main__':
    print("DEBUG PersistenceService: Ejecutando prueba de PersistenceService (main block)...")
    # Este bloque de prueba solo se ejecuta si el archivo se llama directamente
    # python -m app.services.persistence_service (desde la raíz del proyecto)
    ps = PersistenceService()
    if ps.collection:
        print("INFO PersistenceService (main test): Colección disponible.")
        # Test add
        added_id = ps.add_research_document(
            topic="IA en el Desarrollo de Software",
            summary="La IA está optimizando ciclos de desarrollo y mejorando la calidad del código.",
            gdrive_id="gdrive_test_id_devsw",
            gdrive_link="http://example.com/gdrive/devsw",
            content_preview="El uso de herramientas IA como copilotos de código..."
        )
        if added_id:
             print(f"INFO PersistenceService (main test): Documento de prueba añadido con ID: {added_id}")
        else:
            print("WARN PersistenceService (main test): No se pudo añadir el documento de prueba.")


        # Test query
        print("\nINFO PersistenceService (main test): Consultando por 'IA y software':")
        query_results = ps.query_similar_research("Uso de la IA en programación", n_results=2)
        if query_results:
            for res in query_results:
                print(f"  ID: {res['id']}")
                print(f"  Meta: {res['metadata']}")
                sim_score = res.get('similarity_score')
                print(f"  Simil (1-Dist): {sim_score:.4f}" if sim_score is not None else "N/A")
        else:
            print("  No se encontraron resultados o hubo un error.")
    elif ps.initialization_error:
        print(f"ERROR PersistenceService (main test): No se pudo inicializar PersistenceService. Error: {ps.initialization_error}")
    else:
        print("ERROR PersistenceService (main test): ps.collection es None, pero no hay initialization_error. Estado inesperado.")
    print("DEBUG PersistenceService: Fin de la prueba de PersistenceService (main block).")