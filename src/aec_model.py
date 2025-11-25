# src/aec_model.py
import os
import google.generativeai as genai
from openai import OpenAI


class AECModel:
    """
    Unified model class supporting both Gemini and OpenAI providers.
    """
    def __init__(self, config):
        self.provider = (config.get("models", "provider", "gemini") or "gemini").lower()
        self.model_name = config.get("models", "aec_model", "gemini-2.5-flash")
        self.temperature = config.get("models", "temperature", 0.1)

        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Missing GEMINI_API_KEY environment variable.")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.types.GenerationConfig(temperature=self.temperature)
            )

        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=api_key)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_response(self, prompt: str) -> str:
        """
        Generate response using the configured provider.
        """
        try:
            if self.provider == "gemini":
                response = self.client.generate_content(prompt)
                return response.text if hasattr(response, "text") else "<no response>"

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature
                )
                return response.choices[0].message.content or "<no response>"

        except Exception as e:
            return f"Error generating response: {str(e)}"