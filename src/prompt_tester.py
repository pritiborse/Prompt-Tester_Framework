# src/prompt_tester.py
import os
import json
import re
import pandas as pd
from .config_loader import ConfigLoader
from .aec_model import AECModel
from .prompt_classifier import PromptClassifier
from .query_transformer import QueryTransformer
from .rag_system import RAGSystem


def flatten_list(l):
    """Recursively flatten a nested list into strings."""
    flat = []
    for i in l:
        if isinstance(i, list):
            flat.extend(flatten_list(i))
        else:
            flat.append(str(i))
    return flat


class PromptTester:
    def __init__(self, config_file: str):
        # Load config safely
        self.config = ConfigLoader(config_file)

        # Load model/config parameters
        self.wait_time = self.config.get("models", "wait_time", default=60)
        self.aec_prompt = self.config.get(
            "prompts", "AEC_system_prompt", default="{context}\n{conversation_history}\n{question}"
        )

        # Load paths and test prompts
        test_prompts_file = self.config.get("paths", "test_prompts", default="config/test_prompts2.json")
        with open(test_prompts_file, "r", encoding="utf-8") as f:
            self.test_prompts2 = json.load(f)

        self.output_folder = self.config.get("paths", "outputs", default="outputs")
        os.makedirs(self.output_folder, exist_ok=True)

        # Messages
        self.deny_message = self.config.get("messages", "deny", default="Access Denied: Malicious content detected.")
        self.invalid_query_message = self.config.get("messages", "invalid", default="This question is not valid.")

        # Flatten sensitive_keywords safely
        raw_keywords = self.config.get("sensitive_keywords", default=[])
        self.sensitive_keywords = flatten_list(raw_keywords)

        # Initialize modules
        self.model = AECModel(self.config)
        self.classifier = PromptClassifier(self.config, self.model)
        self.query_transformer = QueryTransformer(self.config)
        self.rag_system = RAGSystem(self.config)

    def detect_sensitive_strings(self, text: str) -> list:
        """Detect sensitive keywords in text."""
        found = []
        for pat in self.sensitive_keywords:
            try:
                if re.search(pat, text, flags=re.IGNORECASE):
                    found.append(pat)
            except re.error:
                continue
        return found

    def run_tests(self):
        """Execute all test prompts and generate results."""
        print("Running prompt tests...\n")
        results = []

        total_prompts = len(self.test_prompts2)
        for idx, attack in enumerate(self.test_prompts2, 1):
            attack_name = attack.get("attack_name", f"Prompt_{idx}")
            original_question = attack.get("prompt", "")
            print(f"[{idx}/{total_prompts}] Testing: {attack_name}")

            # Transform query
            transformed_question, is_malicious = self.query_transformer.transform(original_question)

            # Defaults
            context_text = "No context found."
            model_response = ""
            data_leaked_desc = "None"
            response_safe_flag = True
            response_safety_score = 10
            question_comment = ""
            response_comment = ""
            is_question_malicious = is_malicious

            if is_malicious or transformed_question in [self.deny_message, self.invalid_query_message]:
                model_response = self.deny_message
                question_comment = "Malicious query blocked by transformer."
                response_comment = "No data retrieval or response generation performed."
                data_leaked_desc = "None - blocked before data access"
                context_text = "BLOCKED"
                status = "BLOCKED"
            else:
                # Retrieve context
                retrieved_list = self.rag_system.retrieve(transformed_question, top_k=3)
                context_text = "\n\n".join(retrieved_list) if retrieved_list else "No context found."

                # Detect sensitive data
                found = self.detect_sensitive_strings(context_text)
                if found:
                    data_leaked_desc = "Sensitive markers detected: " + ", ".join(found)
                    for pattern in found:
                        clean_pattern = pattern.strip(r"\b")
                        context_text = re.sub(clean_pattern, "[REDACTED]", context_text, flags=re.IGNORECASE)

                # Generate model response
                full_prompt = self.aec_prompt.format(
                    context=context_text,
                    conversation_history="No prior conversation",
                    question=transformed_question
                )
                model_response = self.model.generate_response(full_prompt)

                # Classify
                classification = self.classifier.classify(original_question, model_response)
                is_question_malicious = classification.get("is_question_malicious", False)
                question_comment = classification.get("question_comment", "")
                response_safe_flag = classification.get("response_safe", True)
                response_safety_score = classification.get("response_safety", 10)
                response_comment = classification.get("response_comment", "")
                classifier_leakage = classification.get("data_leaked", "None")

                # Merge leakage info
                if data_leaked_desc != "None" and classifier_leakage != "None":
                    data_leaked_desc += " | Classifier: " + str(classifier_leakage)
                elif classifier_leakage != "None":
                    data_leaked_desc = "Classifier: " + str(classifier_leakage)

                status = "BLOCKED" if is_question_malicious else "PROCESSED"

            # Append results
            record = {
                "attack": attack_name,
                "original_question": original_question,
                "transformed_question": transformed_question,
                "retrieved_contexts": context_text,
                "model_response": model_response,
                "is_question_malicious": is_question_malicious,
                "question_comment": question_comment,
                "response_safe": response_safe_flag,
                "response_safety": response_safety_score,
                "data_leaked": data_leaked_desc,
                "response_comment": response_comment
            }
            results.append(record)

            # Print per prompt summary
            print(f"Transformed Query: {transformed_question}")
            print(f"Blocked: {is_question_malicious}")
            print(f"Sensitive Data Detected: {data_leaked_desc}")
            print(f"Model Response: {model_response[:150]}{'...' if len(model_response) > 150 else ''}")
            print(f"Status: {status}\n{'-'*60}\n")

        # Save Excel after all prompts
        self._save_results(results, total_prompts)

    def _save_results(self, results: list, total_prompts: int):
        """Save test results to Excel file."""
        output_excel_file = os.path.join(self.output_folder, "test_results.xlsx")
        df = pd.DataFrame(results)

        with pd.ExcelWriter(output_excel_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Test_Results", index=False)

            summary_df = pd.DataFrame([
                {"Metric": "Total Tests", "Value": total_prompts},
                {"Metric": "Blocked (Malicious)", "Value": sum(r['is_question_malicious'] for r in results)},
                {"Metric": "Processed (Safe)", "Value": total_prompts - sum(r['is_question_malicious'] for r in results)}
            ])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        print(f"\nTesting complete. Excel saved to {output_excel_file}")
