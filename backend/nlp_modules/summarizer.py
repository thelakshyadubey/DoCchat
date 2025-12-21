from sklearn.feature_extraction.text import TfidfVectorizer
from nlp_modules.preprocessor import tokenize_sentences
from nlp_modules.api_client import generate_summary_with_api
import numpy as np

async def generate_summary(text: str, summary_type: str = "extractive", num_sentences: int = 5) -> str:
    """
    Generate a summary using API (Gemini with Groq fallback)
    
    Args:
        text: Input text to summarize
        summary_type: 'extractive' or 'abstractive'
        num_sentences: Number of sentences for extractive summary
    
    Returns:
        Summary text
    """
    if not text or len(text.strip()) < 50:
        return "Text too short to summarize."
    
    # Use API for both extractive and abstractive summaries
    try:
        summary = await generate_summary_with_api(text, summary_type)
        return summary.strip()
    except Exception as e:
        # Fallback to basic TF-IDF if APIs fail
        print(f"⚠️ API summarization failed, using TF-IDF fallback: {str(e)}")
        return generate_extractive_summary_tfidf(text, num_sentences)


def generate_extractive_summary_tfidf(text: str, num_sentences: int = 5) -> str:
    """
    Fallback: Generate extractive summary using TF-IDF (local, no API needed)
    """
    try:
        # Tokenize into sentences
        sentences = tokenize_sentences(text)
        
        if len(sentences) <= num_sentences:
            return text
        
        # Calculate TF-IDF scores
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # Calculate sentence scores (sum of TF-IDF values)
        sentence_scores = np.array(tfidf_matrix.sum(axis=1)).flatten()
        
        # Get indices of top sentences
        top_indices = sentence_scores.argsort()[-num_sentences:][::-1]
        top_indices = sorted(top_indices)  # Keep original order
        
        # Generate summary
        summary_sentences = [sentences[i] for i in top_indices]
        summary = ' '.join(summary_sentences)
        
        return summary
        
    except Exception as e:
        return f"Summarization failed: {str(e)}"


def get_key_points(text: str, num_points: int = 5) -> list:
    """
    Extract key points from text using sentence scoring
    """
    sentences = tokenize_sentences(text)
    
    if len(sentences) <= num_points:
        return sentences
    
    # Calculate TF-IDF
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(sentences)
    sentence_scores = np.array(tfidf_matrix.sum(axis=1)).flatten()
    
    # Get top sentences
    top_indices = sentence_scores.argsort()[-num_points:][::-1]
    top_indices = sorted(top_indices)
    
    key_points = [sentences[i] for i in top_indices]
    
    return key_points
