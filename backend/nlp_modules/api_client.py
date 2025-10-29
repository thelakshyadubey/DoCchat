import os
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
import asyncio
from functools import wraps

load_dotenv()

# Configure API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize clients
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    gemini_model = None

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None


async def generate_with_fallback(prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """
    Generate text using Gemini API with automatic fallback to Groq if Gemini fails.
    
    Args:
        prompt: The input prompt
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 to 1.0)
    
    Returns:
        Generated text
    """
    
    # Try Gemini first
    if gemini_model:
        try:
            print("🔵 Attempting with Gemini API...")
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            
            # Handle the response properly for new API version
            if response and response.candidates:
                # Get text from the first candidate's content parts
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
                
                if text_parts:
                    result = ''.join(text_parts)
                    print("✅ Gemini API successful")
                    return result
                else:
                    raise Exception("No text content in response")
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            print(f"⚠️ Gemini API failed: {str(e)}")
            print("🔄 Falling back to Groq API...")
    
    # Fallback to Groq
    if groq_client:
        try:
            print("🟢 Attempting with Groq API...")
            chat_completion = await asyncio.to_thread(
                groq_client.chat.completions.create,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",  # Fast and capable model
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = chat_completion.choices[0].message.content
            print("✅ Groq API successful")
            return result
            
        except Exception as e:
            print(f"❌ Groq API also failed: {str(e)}")
            raise Exception(f"Both Gemini and Groq APIs failed. Last error: {str(e)}")
    
    raise Exception("No API keys configured. Please set GEMINI_API_KEY or GROQ_API_KEY in .env file")


async def generate_summary_with_api(text: str, summary_type: str = "extractive") -> str:
    """Generate summary using API"""
    
    if summary_type == "extractive":
        prompt = f"""Extract the most important sentences from this text to create a concise summary. 
Keep the original wording and select 3-5 key sentences that capture the main points.

Text:
{text[:4000]}  # Limit text length

Summary:"""
    else:  # abstractive
        prompt = f"""Create a concise abstractive summary of the following text. 
Rewrite the main ideas in your own words, making it clear and easy to understand.
Aim for 3-4 sentences.

Text:
{text[:4000]}  # Limit text length

Summary:"""
    
    return await generate_with_fallback(prompt, max_tokens=500, temperature=0.5)


async def generate_explanation_with_api(text: str, tone: str = "simple") -> str:
    """Generate explanation using API"""
    
    tone_prompts = {
        "simple": "Explain this in simple, easy-to-understand terms:",
        "examples": "Explain this with practical examples and analogies:",
        "professional": "Provide a professional, detailed explanation of this:",
        "child-friendly": "Explain this as if talking to a 10-year-old child:"
    }
    
    prompt = f"""{tone_prompts.get(tone, tone_prompts["simple"])}

Text:
{text[:2000]}  # Limit text length

Explanation:"""
    
    return await generate_with_fallback(prompt, max_tokens=800, temperature=0.7)


async def generate_key_points_with_api(text: str) -> str:
    """Generate exam-ready key points from document"""
    
    prompt = f"""Analyze the following document and extract the most important key points for exam preparation.
Format your response as a numbered list of concise bullet points.
Focus on:
- Main concepts and definitions
- Important facts and figures
- Key theories or frameworks
- Critical relationships or processes
- Memorable formulas or equations (if any)

Aim for 8-12 key points that a student should memorize for an exam.

Document:
{text[:6000]}  # Larger limit for comprehensive analysis

KEY POINTS:"""
    
    return await generate_with_fallback(prompt, max_tokens=1000, temperature=0.3)


async def generate_short_notes_with_api(text: str) -> str:
    """Generate exam-ready short notes from document"""
    
    prompt = f"""Create concise, exam-ready short notes from the following document.
Structure your notes with:
1. Brief overview (2-3 sentences)
2. Key topics with explanations (use subheadings)
3. Important terms and definitions
4. Quick revision points

Make it easy to review quickly before an exam. Use clear formatting with bullet points and short paragraphs.

Document:
{text[:6000]}  # Larger limit for comprehensive notes

EXAM NOTES:"""
    
    return await generate_with_fallback(prompt, max_tokens=1500, temperature=0.4)

