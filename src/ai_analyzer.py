import os
import json
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

# Assuming config_loader structure is available or passed in
# from .config_loader import AIConfig, CacheConfig # Or pass config dict directly

# --- Provider Interface ---

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def analyze_code(self, diff: str, context: Optional[str], criteria: List[str]) -> Dict[str, Any]:
        """
        Analyzes the given code diff using the specific AI provider.

        Args:
            diff: The code diff string.
            context: Optional string containing relevant context (e.g., original file content).
            criteria: List of focus areas or specific instructions for the analysis.

        Returns:
            A dictionary containing the analysis results from the AI.
            The structure might vary slightly by provider initially, but should aim
            for standardization later.
        """
        pass

# --- Concrete Providers ---

class GeminiProvider(AIProvider):
    """AI Provider implementation for Google Gemini."""
    def __init__(self, config: Dict[str, Any]):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not found. Please install it: pip install google-generativeai")

        self.model_name = config.get("model", "gemini-pro")
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Gemini API key is missing in the configuration.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
        print(f"GeminiProvider initialized with model: {self.model_name}")
        # TODO: Add configuration for temperature, max_tokens etc. from config['temperature'], config['max_tokens']

    def analyze_code(self, diff: str, context: Optional[str], criteria: List[str]) -> Dict[str, Any]:
        # --- Basic Prompt Construction (Placeholder) ---
        prompt = f"""Analyze the following code changes based on these criteria: {', '.join(criteria)}.
Provide feedback on potential issues like bugs, style inconsistencies, security vulnerabilities, complexity, and maintainability.
Focus particularly on: {', '.join(criteria)}.

Context (Original Code Snippet, if available):
---
{context or "Not available"}
---

Code Changes (Diff):
---
{diff}
---

Analysis:
"""
        print(f"Sending request to Gemini model: {self.model_name}...")
        try:
            # TODO: Add error handling, retries, potentially adjust for chat vs. text models
            response = self.model.generate_content(prompt)
            print("Received response from Gemini.")
            # Basic response structure - needs refinement
            return {"provider": "gemini", "model": self.model_name, "response_text": response.text}
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # Return an error structure or raise a specific exception
            return {"provider": "gemini", "error": str(e)}


class OpenAICompatibleProvider(AIProvider):
    """AI Provider implementation for OpenAI API and compatible endpoints."""
    def __init__(self, config: Dict[str, Any]):
        try:
            from openai import OpenAI, AzureOpenAI # Handle both standard and Azure
        except ImportError:
            raise ImportError("openai package not found. Please install it: pip install openai")

        self.model_name = config.get("model", "gpt-3.5-turbo")
        api_key = config.get("api_key")
        base_url = config.get("base_url") # For local LLMs or Azure

        if not api_key:
            # For local models, API key might be optional ('ollama', 'none', etc.)
            print("Warning: OpenAI API key is missing. Assuming local model or intentional omission.")
            # raise ValueError("OpenAI API key is missing in the configuration.")

        # Basic logic to differentiate Azure vs OpenAI vs Local
        # TODO: Refine this logic based on Azure-specific config needs if added later
        if base_url and "openai.azure.com" in base_url:
             print(f"Initializing AzureOpenAI client for model: {self.model_name}, base_url: {base_url}")
             # Potentially needs api_version from config as well
             # self.client = AzureOpenAI(api_key=api_key, azure_endpoint=base_url, api_version="YOUR_AZURE_API_VERSION")
             raise NotImplementedError("Azure OpenAI client initialization needs api_version and refinement.")
        else:
             print(f"Initializing OpenAI client for model: {self.model_name}, base_url: {base_url or 'Default OpenAI'}")
             self.client = OpenAI(api_key=api_key, base_url=base_url)

        # TODO: Add configuration for temperature, max_tokens etc.

    def analyze_code(self, diff: str, context: Optional[str], criteria: List[str]) -> Dict[str, Any]:
         # --- Basic Prompt Construction (Placeholder - using ChatCompletion format) ---
        system_prompt = f"""You are a strict code reviewer. Analyze the following code changes based on these criteria: {', '.join(criteria)}.
Provide detailed feedback on potential issues like bugs, style inconsistencies, security vulnerabilities, complexity, and maintainability.
Focus particularly on: {', '.join(criteria)}. Respond in a structured format (e.g., JSON or Markdown sections)."""

        user_prompt = f"""Context (Original Code Snippet, if available):
---
{context or "Not available"}
---

Code Changes (Diff):
---
{diff}
---

Please provide your analysis."""

        print(f"Sending request to OpenAI compatible model: {self.model_name}...")
        try:
            # Using ChatCompletion - adjust if using older completion models
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # TODO: Pass temperature, max_tokens from config
            )
            print("Received response from OpenAI compatible model.")
            # Basic response structure - needs refinement
            analysis_content = response.choices[0].message.content
            return {"provider": "openai", "model": self.model_name, "response_text": analysis_content}
        except Exception as e:
            print(f"Error calling OpenAI compatible API: {e}")
            return {"provider": "openai", "error": str(e)}


# --- Factory Function ---

def get_ai_provider(ai_config: Dict[str, Any]) -> AIProvider:
    """
    Factory function to create an instance of the appropriate AI provider.
    """
    provider_name = ai_config.get("provider", "").lower()

    if provider_name == "gemini":
        gemini_config = ai_config.get("gemini")
        if not gemini_config:
            raise ValueError("Missing 'gemini' configuration section for Gemini provider.")
        # Pass general AI settings too if needed (temp, tokens)
        gemini_config.update({k: v for k, v in ai_config.items() if k in ['temperature', 'max_tokens']})
        return GeminiProvider(gemini_config)
    elif provider_name == "openai" or provider_name == "local_llm":
        openai_config = ai_config.get("openai")
        if not openai_config:
            raise ValueError("Missing 'openai' configuration section for OpenAI/local_llm provider.")
        openai_config.update({k: v for k, v in ai_config.items() if k in ['temperature', 'max_tokens']})
        return OpenAICompatibleProvider(openai_config)
    # elif provider_name == "anthropic": # Future
    #     anthropic_config = ai_config.get("anthropic")
    #     # ... implementation ...
    #     return AnthropicProvider(anthropic_config)
    else:
        raise ValueError(f"Unsupported AI provider specified: {provider_name}")


# --- Caching ---

class AIAnalyzer:
    """
    Manages AI analysis, including provider selection and caching.
    """
    def __init__(self, ai_config: Dict[str, Any], cache_config: Dict[str, Any]):
        """
        Initializes the AI Analyzer.

        Args:
            ai_config: The AI configuration dictionary.
            cache_config: The cache configuration dictionary.
        """
        self.ai_provider = get_ai_provider(ai_config)
        self.ai_config = ai_config # Store for cache key generation
        self.cache_enabled = cache_config.get("enabled", False)
        self.cache_dir = Path(cache_config.get("directory", ".code_argus_cache"))

        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"AI response caching enabled. Cache directory: {self.cache_dir.resolve()}")
        else:
            print("AI response caching disabled.")

    def _generate_cache_key(self, diff: str, context: Optional[str], criteria: List[str]) -> str:
        """Generates a unique cache key based on inputs and relevant config."""
        hasher = hashlib.sha256()
        hasher.update((diff or "").encode('utf-8'))
        hasher.update((context or "").encode('utf-8'))
        hasher.update(json.dumps(sorted(criteria)).encode('utf-8'))
        # Include relevant AI config in the key
        hasher.update(self.ai_config.get('provider', '').encode('utf-8'))
        # Include model name from specific provider config
        provider_name = self.ai_config.get('provider', '')
        model_name = self.ai_config.get(provider_name, {}).get('model', '')
        hasher.update(model_name.encode('utf-8'))
        hasher.update(self.ai_config.get('strictness_level', '').encode('utf-8'))
        # Add other relevant config if needed (temp, max_tokens?)

        return hasher.hexdigest()

    def analyze(self, diff: str, context: Optional[str], criteria: List[str]) -> Dict[str, Any]:
        """
        Performs AI analysis, utilizing caching if enabled.
        """
        cache_key = None
        cache_file = None

        if self.cache_enabled:
            start_time = time.time()
            cache_key = self._generate_cache_key(diff, context, criteria)
            cache_file = self.cache_dir / f"{cache_key}.json"

            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    # TODO: Add cache expiry check if max_age_days is implemented
                    print(f"Cache hit for key {cache_key[:8]}... (took {time.time() - start_time:.3f}s)")
                    return cached_data
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Error reading cache file {cache_file}. Ignoring cache. Error: {e}")

            print(f"Cache miss for key {cache_key[:8]}...")


        # Cache miss or caching disabled, call the actual provider
        start_time = time.time()
        result = self.ai_provider.analyze_code(diff, context, criteria)
        print(f"AI provider call took {time.time() - start_time:.3f}s")


        # Store result in cache if enabled and no error occurred
        if self.cache_enabled and cache_file and "error" not in result:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                print(f"Stored result in cache: {cache_file.name}")
            except IOError as e:
                print(f"Warning: Error writing cache file {cache_file}. Error: {e}")

        return result


# --- Example Usage (for testing) ---
if __name__ == '__main__':
    from config_loader import load_config, ConfigError

    # Dummy data
    dummy_diff = """
--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,4 @@
 print('hello world')
+
+def add(a, b):
+    return a+b # Simple addition
"""
    dummy_context = "print('hello world')\n"
    dummy_criteria = ["code_quality", "complexity", "security"]

    try:
        print("Loading configuration for AI Analyzer test...")
        # Assumes config.yaml exists and is configured for a provider
        # (e.g., openai with a valid key/model or local_llm settings)
        config = load_config()

        analyzer = AIAnalyzer(ai_config=config['ai'], cache_config=config['cache'])

        print("\n--- First Analysis (Cache Miss Expected) ---")
        analysis1 = analyzer.analyze(dummy_diff, dummy_context, dummy_criteria)
        print("\nAnalysis Result 1:")
        print(json.dumps(analysis1, indent=2))

        print("\n--- Second Analysis (Cache Hit Expected if enabled) ---")
        analysis2 = analyzer.analyze(dummy_diff, dummy_context, dummy_criteria)
        print("\nAnalysis Result 2:")
        print(json.dumps(analysis2, indent=2))

        # Verify results are the same
        if analysis1 == analysis2:
            print("\nResults match, caching appears functional (if enabled).")
        else:
             print("\nResults DO NOT match. Caching might be disabled or there's an issue.")

        # Test with slightly different criteria (should be cache miss)
        print("\n--- Third Analysis (Different Criteria - Cache Miss Expected) ---")
        analysis3 = analyzer.analyze(dummy_diff, dummy_context, ["performance"])
        print("\nAnalysis Result 3:")
        print(json.dumps(analysis3, indent=2))


    except ConfigError as e:
        print(f"\nConfiguration Error: {e}")
        print("Please ensure 'config.yaml' exists and is correctly configured.")
    except (ValueError, ImportError) as e:
         print(f"\nInitialization Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")