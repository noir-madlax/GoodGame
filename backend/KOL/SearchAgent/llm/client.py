import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from backend/.env
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, "../../../.env")
load_dotenv(dotenv_path)


from typing import Optional

class LLMClient:
    """
    Wrapper for Google Generative AI (Gemini)
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_ANALYZE") 

        if not self.api_key:
             # Just a warning or placeholder, user might configure it later
             print("Warning: GOOGLE_API_KEY not found.")
        else:
             genai.configure(api_key=self.api_key)
        
        self.model_name = "gemini-pro" # Default

    def generate_text(self, prompt: str) -> str:
        """
        Simple text generation
        """
        if not self.api_key:
            return "Error: API Key missing"
            
        model = genai.GenerativeModel(self.model_name)
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating content: {str(e)}"
