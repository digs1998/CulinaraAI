import json
import os
from typing import List, Dict, Optional
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

class RecipeEmbedder:
    """Generate embeddings for recipe documents using various providers"""
    
    def __init__(self, provider: str = "openai", model: str = None):
        """
        Initialize embedder with chosen provider
        
        Args:
            provider: "openai", "sentence-transformers", or "cohere"
            model: Specific model name (optional, uses defaults)
        """
        self.provider = provider.lower()
        self.model = model
        self.embeddings = []
        self.documents = []
        
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the chosen embedding provider"""
        
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.model = self.model or "text-embedding-3-small"
                self.dimension = 1536
                print(f"✓ Initialized OpenAI embeddings: {self.model}")
            except ImportError:
                raise ImportError("Install openai: pip install openai")
        
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                self.model = self.model or "models/text-embedding-004"
                self.dimension = 768
                self.client = genai
                print(f"✓ Initialized Gemini embeddings: {self.model}")
                print(f"   Dimension: {self.dimension}")
            except ImportError:
                raise ImportError("Install google-generativeai: pip install google-generativeai")
        
        elif self.provider == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = self.model or "all-MiniLM-L6-v2"
                self.client = SentenceTransformer(self.model)
                self.dimension = self.client.get_sentence_embedding_dimension()
                print(f"✓ Initialized Sentence Transformers: {self.model}")
                print(f"   Dimension: {self.dimension}")
            except ImportError:
                raise ImportError("Install sentence-transformers: pip install sentence-transformers")
        
        elif self.provider == "cohere":
            try:
                import cohere
                self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
                self.model = self.model or "embed-english-v3.0"
                self.dimension = 1024
                print(f"✓ Initialized Cohere embeddings: {self.model}")
            except ImportError:
                raise ImportError("Install cohere: pip install cohere")
        
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def load_documents(self, jsonl_path: str):
        """Load documents from JSONL file"""
        self.documents = []
        
        with open(jsonl_path, 'r') as f:
            for line in f:
                doc = json.loads(line)
                self.documents.append(doc)
        
        print(f"📚 Loaded {len(self.documents)} documents from {jsonl_path}")
        return self.documents
    
    def embed_batch_gemini(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Gemini"""
        embeddings = []
        for text in texts:
            result = self.client.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        return embeddings
    
    def embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]
    
    def embed_batch_sentence_transformers(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers"""
        embeddings = self.client.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
    
    def embed_batch_cohere(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Cohere"""
        response = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document"
        )
        return response.embeddings
    
    def generate_embeddings(self, batch_size: int = 100):
        """Generate embeddings for all loaded documents"""
        if not self.documents:
            raise ValueError("No documents loaded. Run load_documents() first.")
        
        texts = [doc['text'] for doc in self.documents]
        self.embeddings = []
        
        print(f"\n🔄 Generating embeddings...")
        print(f"   Provider: {self.provider}")
        print(f"   Model: {self.model}")
        print(f"   Documents: {len(texts)}")
        print(f"   Batch size: {batch_size}")
        
        # Process in batches
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch_texts = texts[i:i+batch_size]
            
            try:
                if self.provider == "openai":
                    batch_embeddings = self.embed_batch_openai(batch_texts)
                elif self.provider == "gemini":
                    batch_embeddings = self.embed_batch_gemini(batch_texts)
                elif self.provider == "sentence-transformers":
                    batch_embeddings = self.embed_batch_sentence_transformers(batch_texts)
                elif self.provider == "cohere":
                    batch_embeddings = self.embed_batch_cohere(batch_texts)
                
                self.embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"\n❌ Error in batch {i//batch_size + 1}: {str(e)}")
                # Add zero vectors as placeholders for failed batches
                self.embeddings.extend([[0.0] * self.dimension] * len(batch_texts))
        
        print(f"\n✓ Generated {len(self.embeddings)} embeddings")
        print(f"   Dimension: {len(self.embeddings[0]) if self.embeddings else 0}")
        
        return self.embeddings
    
    def save_embeddings(self, output_path: str = "recipe_embeddings.npz"):
        """Save embeddings and documents to file"""
        if not self.embeddings:
            raise ValueError("No embeddings generated. Run generate_embeddings() first.")
        
        # Convert to numpy array
        embeddings_array = np.array(self.embeddings, dtype=np.float32)
        
        # Save embeddings and metadata
        np.savez_compressed(
            output_path,
            embeddings=embeddings_array,
            ids=[doc['id'] for doc in self.documents],
            metadata=json.dumps([doc['metadata'] for doc in self.documents])
        )
        
        print(f"✓ Saved embeddings to {output_path}")
        print(f"   Shape: {embeddings_array.shape}")
        print(f"   Size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    
    def save_for_vector_db(self, output_path: str = "vector_db_ready.jsonl"):
        """Save in format ready for vector database ingestion"""
        if not self.embeddings:
            raise ValueError("No embeddings generated. Run generate_embeddings() first.")
        
        with open(output_path, 'w') as f:
            for doc, embedding in zip(self.documents, self.embeddings):
                record = {
                    "id": doc['id'],
                    "embedding": embedding,
                    "text": doc['text'],
                    "metadata": doc['metadata']
                }
                f.write(json.dumps(record) + "\n")
        
        print(f"✓ Saved vector DB ready format to {output_path}")
    
    def test_similarity(self, query: str, top_k: int = 5):
        """Test similarity search with a query"""
        if not self.embeddings:
            raise ValueError("No embeddings generated. Run generate_embeddings() first.")
        
        print(f"\n🔍 Testing similarity search...")
        print(f"   Query: '{query}'")
        
        # Generate query embedding
        if self.provider == "openai":
            query_embedding = self.embed_batch_openai([query])[0]
        elif self.provider == "gemini":
            result = self.client.embed_content(
                model=self.model,
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
        elif self.provider == "sentence-transformers":
            query_embedding = self.embed_batch_sentence_transformers([query])[0]
        elif self.provider == "cohere":
            response = self.client.embed(
                texts=[query],
                model=self.model,
                input_type="search_query"
            )
            query_embedding = response.embeddings[0]
        
        # Calculate cosine similarity
        embeddings_array = np.array(self.embeddings)
        query_array = np.array(query_embedding)
        
        # Normalize
        embeddings_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        query_norm = query_array / np.linalg.norm(query_array)
        
        # Compute similarities
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Get top k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        print(f"\n   Top {top_k} results:")
        for i, idx in enumerate(top_indices):
            doc = self.documents[idx]
            sim = similarities[idx]
            print(f"\n   {i+1}. {doc['metadata']['title']} (similarity: {sim:.4f})")
            print(f"      Category: {doc['metadata'].get('category', 'N/A')}")
            print(f"      URL: {doc['metadata']['url']}")


def main():
    """Main function to generate embeddings"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate recipe embeddings")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "sentence-transformers", "cohere"],
        default="gemini",
        help="Embedding provider (default: gemini)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specific model name (optional)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="recipes_for_embedding.jsonl",
        help="Input JSONL file"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding generation"
    )
    
    args = parser.parse_args()
    
    print("🚀 Recipe Embedding Generator\n")
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print(f"   Run the embedding preparation script first!")
        return
    
    # Initialize embedder
    try:
        embedder = RecipeEmbedder(provider=args.provider, model=args.model)
    except Exception as e:
        print(f"❌ Failed to initialize embedder: {str(e)}")
        return
    
    # Load documents
    embedder.load_documents(args.input)
    
    # Generate embeddings
    embedder.generate_embeddings(batch_size=args.batch_size)
    
    # Save embeddings
    embedder.save_embeddings("recipe_embeddings.npz")
    embedder.save_for_vector_db("vector_db_ready.jsonl")
    
    # Test with sample queries
    print("\n" + "="*80)
    print("Testing similarity search with sample queries:")
    print("="*80)
    
    test_queries = [
        "quick chicken dinner",
        "healthy vegetarian recipes",
        "chocolate dessert"
    ]
    
    for query in test_queries:
        embedder.test_similarity(query, top_k=3)
    
    print("\n✅ Embedding generation complete!")
    print(f"\n📁 Output files:")
    print(f"   - recipe_embeddings.npz (NumPy compressed format)")
    print(f"   - vector_db_ready.jsonl (ready for vector DB)")
    print(f"\n💡 Next steps:")
    print(f"   1. Upload embeddings to a vector database (Pinecone, Weaviate, ChromaDB)")
    print(f"   2. Implement RAG query system in your backend")
    print(f"   3. Connect to your chat interface")


if __name__ == "__main__":
    main()