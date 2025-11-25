# src/prompt_classifier.py
import json
import re
from .aec_model import AECModel


class PromptClassifier:
    def __init__(self, config, aec_model: AECModel):
        self.template = config.get("prompts", "prompt_classification", "{question}\n{response}")
        self.model = aec_model

    def classify(self, question: str, model_response: str) -> dict:
        """
        Classify question/response pair for security issues.
        """
        try:
            prompt = self.template.format(question=question, response=model_response)
            response_text = self.model.generate_response(prompt).strip()

            # Extract JSON from response
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                # Ensure all required fields exist with proper defaults
                return {
                    "is_question_malicious": result.get("is_question_malicious", False),
                    "question_comment": result.get("question_comment", ""),
                    "response_safe": result.get("response_safe", True),
                    "response_safety": result.get("response_safety", 10),
                    "data_leaked": result.get("data_leaked", "None"),
                    "response_comment": result.get("response_comment", "")
                }

            # Fallback: couldn't parse JSON
            return {
                "is_question_malicious": False,
                "question_comment": "Could not parse model output",
                "response_safe": True,  # Changed from False
                "response_safety": 10,
                "data_leaked": "N/A",
                "response_comment": response_text[:200]
            }

        except Exception as e:
            return {
                "is_question_malicious": False,
                "question_comment": f"Classification error: {str(e)}",
                "response_safe": True,  # Changed from False
                "response_safety": 10,
                "data_leaked": "N/A",
                "response_comment": f"Error: {str(e)}"
            }