import os
import pickle
import numpy as np
import faiss
import subprocess  # This is the critical missing import
from pathlib import Path
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import traceback
from pdfminer.high_level import extract_text as pdfminer_extract_text
import warnings
warnings.filterwarnings("ignore")
from database import get_drive_file_id, update_document_with_drive_id
# from app import get_drive_manager
from drive_utils import get_drive_file_id, download_from_drive, get_drive_manager


# Constants
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

# Initialize model with robust error handling
try:
    print("\nInitializing Sentence Transformer model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"✓ Model loaded | Device: {model.device} | Max length: {model.max_seq_length}")
except Exception as e:
    print(f"🚨 Model loading failed: {str(e)}")
    traceback.print_exc()
    raise

def extract_text_from_pdf(filepath):
    """Robust PDF text extraction with multiple fallbacks"""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"🚨 File not found: {filepath}")
        return ""

    text = ""
    methods = [
        # (method_name, function)
        ("PyPDF2", lambda: "".join(p.extract_text() or "" for p in PdfReader(filepath).pages)),
        ("PDFMiner", lambda: pdfminer_extract_text(filepath)),
        ("pdftotext", lambda: subprocess.run(['pdftotext', str(filepath), '-'], 
                                           capture_output=True, text=True).stdout)
    ]

    for name, method in methods:
        try:
            text = method()
            if text.strip():
                print(f"✓ Extracted with {name} ({len(text)} chars)")
                return text
        except Exception as e:
            print(f"⚠️ {name} failed: {str(e)}")
            continue

    print("🚨 All extraction methods failed")
    return ""

def create_chunks(text):
    """Split text into overlapping chunks"""
    words = text.split()
    return [
        ' '.join(words[i:i+CHUNK_SIZE])
        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP)
    ]

def create_faiss_index(embeddings):
    """Create and populate FAISS index"""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def process_document(filepath, user_id, doc_id):
    """Main document processing pipeline"""
    try:
        # Verify Google Drive folder exists
        drive_manager = get_drive_manager()
        folder_id = drive_manager.get_or_create_user_folder(user_id)
        if not folder_id:
            raise Exception("Google Drive folder not found")
        
        filepath = Path(filepath)
        if not filepath.exists():
            drive_file_id = get_drive_file_id(user_id, doc_id)
            if not drive_file_id:
                print(f"🚨 Error: File not found at {filepath}")
                return False
            
            print("Downloading file from Google Drive...")
            if not download_from_drive(drive_file_id, str(filepath)):
                print("🚨 Failed to download from Google Drive")
                return False

        print(f"\nProcessing document {doc_id}...")

        # 1. Text extraction
        print("[1/4] Extracting text...")
        text = extract_text_from_pdf(filepath)
        if not text.strip():
            print("🚨 Error: No text extracted")
            return False

        # 2. Chunk creation
        print("[2/4] Creating chunks...")
        chunks = create_chunks(text)
        if not chunks:
            print("🚨 Error: No chunks created")
            return False
        print(f"✓ Created {len(chunks)} chunks")

        # 3. Embedding generation
        print("[3/4] Generating embeddings...")
        embeddings = model.encode(chunks, show_progress_bar=True)
        print(f"✓ Embeddings shape: {embeddings.shape}")

        # 4. FAISS index creation
        print("[4/4] Creating FAISS index...")
        index = create_faiss_index(embeddings)
        print(f"✓ Index size: {index.ntotal}")

        # 5. Save to PostgreSQL
        print("\nSaving to database...")
        from database import save_embeddings
        save_embeddings(user_id, doc_id, chunks, embeddings, index)
        
        print("✓ Processing completed successfully")
        return True

    except Exception as e:
        print(f"🚨 Processing failed: {str(e)}")
        traceback.print_exc()
        return False

    
# Add this function to document_processor.py
def delete_document_embeddings(user_id, doc_id):
    """Delete all embedding files for a document"""
    embedding_dir = Path("embeddings") / str(user_id)
    base_path = embedding_dir / str(doc_id)
    
    for ext in ['.pkl', '.npy', '.index']:
        try:
            file_path = base_path.with_suffix(ext)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting {file_path}: {str(e)}")
            raise

