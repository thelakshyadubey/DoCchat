from nlp_modules.api_client import generate_explanation_with_api

async def generate_explanation(text: str, tone: str = "simple") -> str:
    """
    Generate an explanation using API (Gemini with Groq fallback)
    
    Args:
        text: Text to explain
        tone: Explanation tone ('simple', 'examples', 'professional', 'child-friendly')
    
    Returns:
        Explained text
    """
    if not text or len(text.strip()) < 10:
        return "Text too short to explain."
    
    try:
        explanation = await generate_explanation_with_api(text, tone)
        return explanation.strip()
    except Exception as e:
        return f"Explanation generation failed: {str(e)}. Please check your API keys."
