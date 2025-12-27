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

        # Chroma client
        self.chroma = Client(Settings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False
        ))
        self.collection = self.chroma.get_or_create_collection(self.collection_name)

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
                    task_type="retrieval_query"
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
                print(f"⚠ Error generating embedding, retrying in {wait_time}s... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)

        raise RuntimeError("Failed to generate embedding after multiple retries.")

    # -----------------------------
    # Ingest JSONL with chunking
    # -----------------------------
    def ingest_jsonl(self, jsonl_path: str):
        print(f"📥 Reading recipes from {jsonl_path}")
        with open(jsonl_path, "r") as f:
            docs = [json.loads(line) for line in f]

        print(f"📦 Generating embeddings for {len(docs)} recipes...")

        for i in tqdm(range(0, len(docs), self.batch_size)):
            batch = docs[i:i+self.batch_size]

            chunked_texts = []
            chunked_ids = []
            chunked_metadatas = []

            # Chunk each recipe
            for doc in batch:
                chunks = self.chunk_text(doc["text"])
                for idx, chunk in enumerate(chunks):
                    chunked_texts.append(chunk)
                    chunked_ids.append(f"{doc['id']}_chunk{idx+1}")
                    metadata = doc.get("metadata", {})
                    chunked_metadatas.append({k: v for k, v in metadata.items() if v is not None})

            # Generate embeddings for chunks
            embeddings = [self._generate_embedding(text) for text in chunked_texts]

            # Add to Chroma
            self.collection.add(
                ids=chunked_ids,
                documents=chunked_texts,
                metadatas=chunked_metadatas,
                embeddings=embeddings
            )

        print(f"✅ Ingested {len(docs)} recipes (chunked) into ChromaDB at '{self.persist_dir}'")

    # -----------------------------
    # Query example
    # -----------------------------
    def query(self, query_text: str, k: int = 5):
        embedding = self._generate_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        return results
