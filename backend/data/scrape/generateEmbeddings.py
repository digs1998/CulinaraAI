# generateEmbeddings.py
import os
import json
import time
from typing import List, Optional
from dotenv import load_dotenv
from chromadb import Client
from chromadb.config import Settings
from tqdm import tqdm

# Generative AI clients
import google.generativeai as genai
from openai import OpenAI

load_dotenv()


class RecipeEmbedder:
    def __init__(
        self,
        persist_dir: str = "chroma_db/",
        collection_name: str = "recipes",
        provider: str = "openai",
        model: Optional[str] = None,
        batch_size: int = 64,
        embedding_dim: int = 1536,  # adjustable embedding dimension
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.provider = provider.lower()
        self.model = model
        self.embedding_dim = embedding_dim

        # Initialize Chroma client
        self.chroma = Client(
            Settings(persist_directory=self.persist_dir, anonymized_telemetry=False)
        )
        self.collection = self.chroma.get_or_create_collection(self.collection_name)

        # Initialize embedding client
        if self.provider == "openai":
            self.embed_client = OpenAI()
        elif self.provider == "gemini":
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    def _generate_embedding(self, text: str, max_retries: int = 5) -> List[float]:
        """Generate embedding for a single text with retries."""
        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    # Example OpenAI embedding call
                    resp = self.embed_client.embeddings.create(
                        model=self.model or "text-embedding-3-large",
                        input=text
                    )
                    return resp.data[0].embedding

                elif self.provider == "gemini":
                    resp = genai.embed_content(
                        model=self.model or "models/gemini-embedding-001",
                        content=text,
                        task_type="retrieval_query"
                    )
                    return resp["embedding"]

            except Exception as e:
                wait = 2 ** attempt
                print(f"⚠️ Error generating embedding, retrying in {wait}s... ({attempt+1}/{max_retries})")
                time.sleep(wait)

        raise RuntimeError("Failed to generate embedding after multiple retries.")

    def ingest_jsonl(self, jsonl_path: str):
        print(f"📥 Reading recipes from {jsonl_path}")
        with open(jsonl_path, "r") as f:
            docs = [json.loads(line) for line in f]

        print(f"📦 Generating embeddings for {len(docs)} recipes...")
        for i in tqdm(range(0, len(docs), self.batch_size)):
            batch = docs[i:i + self.batch_size]

            ids = [doc["id"] for doc in batch]
            texts = [doc["text"] for doc in batch]
            metadatas = [doc["metadata"] for doc in batch]
            embeddings = [self._generate_embedding(text) for text in texts]

            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        # REMOVE this line — it causes the AttributeError
        # self.chroma.persist()

        print(f"✅ Ingested {len(docs)} recipes into ChromaDB at '{self.persist_dir}'")
        print(f"Collection: '{self.collection_name}' ready to query!")

    def query(self, query_text: str, k: int = 5):
        """Query the ChromaDB collection using an embedding."""
        if not query_text.strip():
            return {"documents": [], "metadatas": []}

        embedding = self._generate_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        return results
