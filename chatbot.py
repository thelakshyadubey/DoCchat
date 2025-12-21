import numpy as np
import faiss
import pickle
import os
import traceback
from groq import Groq
from config import Config
from document_processor import model
from dotenv import load_dotenv
from database import load_embeddings, get_db

load_dotenv()

class DocumentChatbot:
    def __init__(self, user_id, doc_ids):
        self.chunks = []
        self.embeddings = None
        self.index = None
        
        print(f"\nInitializing chatbot for user {user_id} with docs: {doc_ids}")
        
        if not doc_ids:
            raise ValueError("No document IDs provided")
        
        # Debug database state
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, filename, drive_file_id FROM documents WHERE user_id = %s",
                (user_id,)
            )
            print("User documents in DB:", cur.fetchall())
        finally:
            cur.close()
            conn.close()
            
        self._load_documents(user_id, doc_ids)
        
        if not self.chunks:
            raise ValueError("No document content could be loaded")

    def _load_documents(self, user_id, doc_ids):
        """Load documents from database"""
        all_chunks = []
        all_embeddings = []
        
        for doc_id in doc_ids:
            try:
                data = load_embeddings(user_id, doc_id)
                if not data:
                    continue
                    
                all_chunks.extend(data['chunks'])
                all_embeddings.append(data['embeddings'])
                
                # Rebuild FAISS index
                if not self.index:
                    self.index = faiss.IndexFlatL2(data['embeddings'].shape[1])
                self.index.add(data['embeddings'])
                
                print(f"✓ Successfully loaded document {doc_id}")
                
            except Exception as e:
                print(f"🚨 Failed to load document {doc_id}: {str(e)}")
                traceback.print_exc()
                continue
        
        if not all_chunks:
            raise ValueError("No valid documents could be loaded")
        
        self.chunks = all_chunks
        self.embeddings = np.vstack(all_embeddings)
        
        # Create merged index
        self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        self.index.add(self.embeddings)

    def generate_response(self, query):
        try:
            # Get relevant chunks from all documents
            query_embedding = model.encode([query])
            D, I = self.index.search(query_embedding, k=5)  # Get top 5 relevant chunks
            
            # Combine context from multiple documents
            context = "\n\n".join([self.chunks[i] for i in I[0]])
            print(f"Context length: {len(context)} characters")
            
            # Generate response using GROQ
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides comprehensive answers "
                                  "by combining information from multiple documents. When asked for "
                                  "a summary or comparison, analyze all provided context together."
                    },
                    {
                        "role": "user",
                        "content": f"Context from multiple documents:\n{context}\n\nQuestion: {query}"
                    }
                ],
                model=Config.GROQ_MODEL,
                temperature=0.3,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "Sorry, I encountered an error processing your question."