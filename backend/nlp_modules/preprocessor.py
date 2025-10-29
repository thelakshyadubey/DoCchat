import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

class TextPreprocessor:
    """
    Text preprocessing pipeline for NLP tasks
    """
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
    
    def clean_text(self, text: str) -> str:
        """Remove special characters and extra whitespace"""
        # Remove special characters but keep periods for sentence tokenization
        text = re.sub(r'[^a-zA-Z0-9\s\.]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def tokenize_words(self, text: str) -> list:
        """Tokenize text into words"""
        return word_tokenize(text.lower())
    
    def tokenize_sentences(self, text: str) -> list:
        """Tokenize text into sentences"""
        return sent_tokenize(text)
    
    def remove_stopwords(self, tokens: list) -> list:
        """Remove stopwords from token list"""
        return [token for token in tokens if token not in self.stop_words]
    
    def lemmatize(self, tokens: list) -> list:
        """Lemmatize tokens"""
        return [self.lemmatizer.lemmatize(token) for token in tokens]
    
    def preprocess(self, text: str, remove_stopwords: bool = True) -> list:
        """
        Complete preprocessing pipeline
        Returns list of processed tokens
        """
        # Clean text
        cleaned = self.clean_text(text)
        
        # Tokenize
        tokens = self.tokenize_words(cleaned)
        
        # Remove stopwords
        if remove_stopwords:
            tokens = self.remove_stopwords(tokens)
        
        # Lemmatize
        tokens = self.lemmatize(tokens)
        
        return tokens
    
    def preprocess_for_summarization(self, text: str) -> dict:
        """
        Preprocess text specifically for summarization
        Returns dict with sentences and processed words
        """
        # Get sentences
        sentences = self.tokenize_sentences(text)
        
        # Process each sentence
        processed_sentences = []
        for sentence in sentences:
            tokens = self.preprocess(sentence, remove_stopwords=True)
            processed_sentences.append({
                'original': sentence,
                'tokens': tokens
            })
        
        return {
            'sentences': processed_sentences,
            'sentence_count': len(sentences)
        }

# Create singleton instance
preprocessor = TextPreprocessor()

# Helper functions for direct use
def preprocess_text(text: str, remove_stopwords: bool = True) -> list:
    """Preprocess text and return tokens"""
    return preprocessor.preprocess(text, remove_stopwords)

def preprocess_for_summarization(text: str) -> dict:
    """Preprocess text for summarization"""
    return preprocessor.preprocess_for_summarization(text)

def tokenize_sentences(text: str) -> list:
    """Tokenize text into sentences"""
    return preprocessor.tokenize_sentences(text)
