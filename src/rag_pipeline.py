import os
import logging
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
import chromadb
from src import config

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    RAG Pipeline for loading, chunking, embedding, indexing,
    and retrieving customer support knowledge base documents.
    """
    def __init__(self):
        # Initialize Google GenAI client
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Initialize ChromaDB persistent client
        self.chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_DB_DIR))
        
        # Get or create collection configured with cosine similarity
        self.collection = self.chroma_client.get_or_create_collection(
            name="support_kb",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Configure text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

    def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generates vector embeddings in batches using text-embedding-004.
        """
        if not texts:
            return []
        try:
            from src.utils import call_with_backoff
            response = call_with_backoff(
                self.client.models.embed_content,
                model=config.EMBEDDING_MODEL,
                contents=texts
            )
            return [e.values for e in response.embeddings]
        except Exception as e:
            logger.error(f"Error generating embeddings batch: {e}")
            raise e

    def get_embedding(self, text: str) -> list[float]:
        """
        Generates a vector embedding for a single text string.
        """
        try:
            from src.utils import call_with_backoff
            response = call_with_backoff(
                self.client.models.embed_content,
                model=config.EMBEDDING_MODEL,
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise e

    def clear_database(self):
        """
        Clears all documents from the ChromaDB collection.
        """
        try:
            # We can delete all items by target IDs, or drop and recreate
            self.chroma_client.delete_collection("support_kb")
            self.collection = self.chroma_client.get_or_create_collection(
                name="support_kb",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection cleared successfully.")
        except Exception as e:
            logger.error(f"Error clearing ChromaDB: {e}")

    def ingest_knowledge_base(self) -> int:
        """
        Loads all PDF, TXT, and MD files from config.DATA_DIR,
        chunks them, generates embeddings, and indexes them in ChromaDB.
        
        Returns:
            The total number of chunks successfully indexed.
        """
        self.clear_database()
        
        data_path = config.DATA_DIR
        if not data_path.exists():
            logger.warning(f"Data directory does not exist: {data_path}")
            return 0

        chunks_to_index = []
        metadatas_to_index = []
        ids_to_index = []
        chunk_counter = 0

        # Loop through all files in the data directory
        for filename in os.listdir(data_path):
            file_path = data_path / filename
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            logger.info(f"Processing file: {filename}")

            if ext == ".pdf":
                try:
                    reader = PdfReader(file_path)
                    for page_idx, page in enumerate(reader.pages):
                        page_num = page_idx + 1
                        text = page.extract_text() or ""
                        if not text.strip():
                            continue
                        
                        # Chunk the text extracted from this specific page
                        page_chunks = self.splitter.split_text(text)
                        for chunk in page_chunks:
                            chunks_to_index.append(chunk)
                            metadatas_to_index.append({
                                "source": filename,
                                "page": page_num
                            })
                            ids_to_index.append(f"{filename}_p{page_num}_{chunk_counter}")
                            chunk_counter += 1
                except Exception as e:
                    logger.error(f"Failed to read PDF file {filename}: {e}")

            elif ext in [".txt", ".md"]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    if not text.strip():
                        continue
                    
                    file_chunks = self.splitter.split_text(text)
                    for chunk in file_chunks:
                        chunks_to_index.append(chunk)
                        metadatas_to_index.append({
                            "source": filename,
                            "page": 1  # Default to page 1 for text files
                        })
                        ids_to_index.append(f"{filename}_{chunk_counter}")
                        chunk_counter += 1
                except Exception as e:
                    logger.error(f"Failed to read text/markdown file {filename}: {e}")

        # Batch embed and write to ChromaDB
        if chunks_to_index:
            batch_size = 50
            for i in range(0, len(chunks_to_index), batch_size):
                batch_chunks = chunks_to_index[i:i + batch_size]
                batch_metadatas = metadatas_to_index[i:i + batch_size]
                batch_ids = ids_to_index[i:i + batch_size]

                # Generate embeddings for the batch
                batch_embeddings = self.get_embeddings_batch(batch_chunks)

                # Add to Chroma collection
                self.collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas,
                    documents=batch_chunks
                )
            logger.info(f"Successfully indexed {len(chunks_to_index)} chunks in ChromaDB.")
            return len(chunks_to_index)
        
        return 0

    def retrieve_context(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Embeds the query and searches the database for top_k similar chunks.
        
        Returns:
            A list of dictionaries with text, source, page, and similarity score.
        """
        if not query.strip():
            return []

        try:
            # Generate query embedding
            query_vector = self.get_embedding(query)
            
            # Query the database
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )

            retrieved_items = []
            if results and results.get("documents") and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    doc_text = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    
                    # ChromaDB returns distance. Since we configured the collection with 'cosine' space,
                    # the distance returned is Cosine Distance = 1.0 - Cosine Similarity.
                    # We compute the score as Cosine Similarity.
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity_score = max(0.0, min(1.0, 1.0 - distance))

                    retrieved_items.append({
                        "text": doc_text,
                        "source": metadata.get("source", "unknown"),
                        "page": metadata.get("page", 1),
                        "score": round(similarity_score, 4)
                    })
            return retrieved_items
            
        except Exception as e:
            logger.error(f"Error during context retrieval: {e}")
            return []
