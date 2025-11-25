# main.py
import os
import sys
from src.prompt_tester import PromptTester
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    try:
        # Config file path
        config_path = os.path.join("config", "config.yaml")
        
        # Verify config exists
        if not os.path.exists(config_path):
            print(f"Error: Config file not found at {config_path}")
            sys.exit(1)

        # Initialize PromptTester
        print("Initializing PromptTester...")
        tester = PromptTester(config_path)
        
        # Display configuration
        provider = tester.config.get("models", "provider", "unknown")
        aec_model = tester.config.get("models", "aec_model", "unknown")
        # transformer_model = tester.config.get("models", "transformer_model", "unknown")
        
        print(f"Provider: {provider}")
        print(f"AEC Model: {aec_model}")
        # print(f"Transformer Model: {transformer_model}")
        print(f"Total test prompts: {len(tester.test_prompts2)}\n")

        # Run all test prompts
        print("Running prompt tests...\n")
        tester.run_tests()
        
        print(f"\nTests completed successfully!")
        print(f"Results saved in: {tester.output_folder}")
        
    except FileNotFoundError as e:
        print(f"Error: Required file not found - {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()