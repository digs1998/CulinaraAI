# generateEmbeddings.py

import os
import json
import time
from typing import Optional, List
from dotenv import load_dotenv
from chromadb import Client
from chromadb.config import Settings
from tqdm import tqdm
import google.generativeai as genai

load_dotenv()


class RecipeEmbedder:
    def __init__(
        self,
        persist_dir,
        collection_name,
        provider,
        model,
        embedding_dim,
        batch_size,
        chunk_size
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.provider = provider
        self.model = model
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self.chunk_size = chunk_size

        # Chroma client - use PersistentClient for better reliability
        from chromadb import PersistentClient
        self.chroma = PersistentClient(path=self.persist_dir)
        
        # Delete existing collection to start fresh
        try:
            self.chroma.delete_collection(self.collection_name)
            print(f"🗑️  Deleted existing collection '{self.collection_name}'")
        except:
            pass
        
        self.collection = self.chroma.create_collection(
            name=self.collection_name,
            metadata={"description": "Recipe embeddings for RAG search"}
        )
        print(f"✅ Created new collection '{self.collection_name}'")

        # Gemini configuration
        if self.provider == "gemini":
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    # -----------------------------
    # Chunk text into smaller pieces
    # -----------------------------
    def chunk_text(self, text: str) -> List[str]:
        words = text.split()
        return [" ".join(words[i:i+self.chunk_size]) for i in range(0, len(words), self.chunk_size)]

    # -----------------------------
    # Generate embedding with retries
    # -----------------------------
    def _generate_embedding(self, text: str, max_retries: int = 5):
        if self.provider != "gemini":
            raise NotImplementedError(f"Provider {self.provider} not supported")

        model = self.model

        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model=model,
                    content=text,
                    task_type="retrieval_document"  # Changed from retrieval_query
                )
                embedding = result.get("embedding")
                if not embedding:
                    raise ValueError("Empty embedding returned")

                # Adjust dimension
                if len(embedding) != self.embedding_dim:
                    print(f"⚠️ Warning: Embedding dimension mismatch "
                          f"(expected {self.embedding_dim}, got {len(embedding)})")
                    if len(embedding) < self.embedding_dim:
                        embedding += [0.0] * (self.embedding_dim - len(embedding))
                    else:
                        embedding = embedding[:self.embedding_dim]

                return embedding
            except Exception as e:
                wait_time = 2 ** attempt
                print(f"⚠️ Error generating embedding, retrying in {wait_time}s... ({attempt+1}/{max_retries})")
                print(f"   Error: {str(e)[:100]}")
                time.sleep(wait_time)

        raise RuntimeError("Failed to generate embedding after multiple retries.")

    # -----------------------------
    # Flatten metadata for ChromaDB
    # -----------------------------
    def _flatten_metadata(self, metadata: dict) -> dict:
        """
        ChromaDB requires flat metadata (no nested dicts/lists).
        Convert all values to strings or numbers.
        """
        flat = {}
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                flat[key] = value
            elif isinstance(value, list):
                # Convert list to comma-separated string
                flat[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                # Skip nested dicts or flatten them
                continue
            else:
                flat[key] = str(value)
        
        return flat

    # -----------------------------
    # Ingest JSONL WITHOUT chunking (better for RAG)
    # -----------------------------
    def ingest_jsonl(self, jsonl_path: str):
        print(f"📥 Reading recipes from {jsonl_path}")
        with open(jsonl_path, "r") as f:
            docs = [json.loads(line) for line in f]

        print(f"📦 Generating embeddings for {len(docs)} recipes...")
        print(f"⚙️  Batch size: {self.batch_size}")

        all_ids = []
        all_documents = []
        all_metadatas = []
        all_embeddings = []

        for i, doc in enumerate(tqdm(docs), 1):
            try:
                # Get full text (no chunking - keep recipe intact)
                text = doc["text"]
                recipe_id = doc["id"]
                
                # Generate embedding
                embedding = self._generate_embedding(text)
                
                # Flatten metadata
                metadata = self._flatten_metadata(doc.get("metadata", {}))
                # Add recipe ID to metadata
                metadata["id"] = recipe_id
                
                all_ids.append(recipe_id)
                all_documents.append(text)
                all_metadatas.append(metadata)
                all_embeddings.append(embedding)
                
                # Insert in batches to avoid rate limits
                if len(all_ids) >= self.batch_size:
                    self.collection.add(
                        ids=all_ids,
                        documents=all_documents,
                        metadatas=all_metadatas,
                        embeddings=all_embeddings
                    )
                    print(f"   ✅ Inserted batch ({len(all_ids)} recipes)")
                    all_ids = []
                    all_documents = []
                    all_metadatas = []
                    all_embeddings = []
                    
                    # Rate limiting pause
                    time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Skipping recipe {i} due to error: {str(e)[:100]}")
                continue

        # Insert remaining recipes
        if all_ids:
            self.collection.add(
                ids=all_ids,
                documents=all_documents,
                metadatas=all_metadatas,
                embeddings=all_embeddings
            )
            print(f"   ✅ Inserted final batch ({len(all_ids)} recipes)")

        total_count = self.collection.count()
        print(f"\n✅ Successfully ingested {total_count} recipes into ChromaDB")
        print(f"📊 Collection '{self.collection_name}' at '{self.persist_dir}'")

    # -----------------------------
    # Query example
    # -----------------------------
    def query(self, query_text: str, k: int = 5):
        embedding = self._generate_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["metadatas", "distances", "documents"]
        )
        return results