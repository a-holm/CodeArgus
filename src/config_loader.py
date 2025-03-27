import yaml
import os
from typing import Dict, Any, Optional, List, TypedDict
from pathlib import Path

# --- TypedDicts for Config Structure (Basic Validation) ---

class GitHubConfig(TypedDict):
    repository: str
    token: str
    base_url: Optional[str]

class OpenAIConfig(TypedDict):
    model: str
    api_key: str
    base_url: Optional[str]

class GeminiConfig(TypedDict):
    model: str
    api_key: str

# class AnthropicConfig(TypedDict): # Future
#     model: str
#     api_key: str

class AIConfig(TypedDict):
    provider: str
    openai: Optional[OpenAIConfig]
    gemini: Optional[GeminiConfig]
    # anthropic: Optional[AnthropicConfig] # Future
    temperature: Optional[float]
    max_tokens: Optional[int]
    strictness_level: str
    focus_areas: List[str]

class ProjectConfig(TypedDict):
    local_path: str
    # test_indicators: Optional[List[str]]
    # test_dependency_markers: Optional[List[str]]

class ReportingConfig(TypedDict):
    output_dir: str
    terminal_colors: bool
    # log_level: Optional[str]

class CacheConfig(TypedDict):
    enabled: bool
    directory: str
    # max_age_days: Optional[int] # Future

class AppConfig(TypedDict):
    github: GitHubConfig
    ai: AIConfig
    project: ProjectConfig
    reporting: ReportingConfig
    cache: CacheConfig

# --- Configuration Loading ---

DEFAULT_CONFIG_FILENAME = "config.yaml"

class ConfigError(Exception):
    """Custom exception for configuration loading errors."""
    pass

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Loads the application configuration from a YAML file.

    Args:
        config_path: Optional path to the config file. Defaults to 'config.yaml'
                     in the current working directory.

    Returns:
        A dictionary containing the application configuration.

    Raises:
        ConfigError: If the config file is not found or cannot be parsed.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILENAME

    config_file = Path(config_path)

    if not config_file.is_file():
        raise ConfigError(
            f"Configuration file not found: {config_file.resolve()}. "
            f"Please create it based on 'config.yaml.example'."
        )

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing configuration file {config_file}: {e}")
    except Exception as e:
        raise ConfigError(f"Error reading configuration file {config_file}: {e}")

    if not isinstance(config_data, dict):
         raise ConfigError(f"Invalid configuration format in {config_file}. Expected a dictionary.")

    # Basic validation (more sophisticated validation could be added later)
    required_keys = ["github", "ai", "project", "reporting", "cache"]
    for key in required_keys:
        if key not in config_data:
            raise ConfigError(f"Missing required top-level key '{key}' in {config_file}")

    # TODO: Add more detailed validation of nested structures and types

    # Resolve potential environment variables for sensitive keys
    # Example for GitHub token:
    if config_data.get("github", {}).get("token", "").startswith("ENV:"):
        var_name = config_data["github"]["token"].split(":", 1)[1]
        env_value = os.getenv(var_name)
        if not env_value:
            raise ConfigError(f"Environment variable '{var_name}' specified for github.token not found.")
        config_data["github"]["token"] = env_value

    # Example for AI API keys (add similar logic for Gemini, Anthropic etc. as needed)
    if config_data.get("ai", {}).get("openai", {}).get("api_key", "").startswith("ENV:"):
        var_name = config_data["ai"]["openai"]["api_key"].split(":", 1)[1]
        env_value = os.getenv(var_name)
        if not env_value:
             raise ConfigError(f"Environment variable '{var_name}' specified for ai.openai.api_key not found.")
        config_data["ai"]["openai"]["api_key"] = env_value

    if config_data.get("ai", {}).get("gemini", {}).get("api_key", "").startswith("ENV:"):
        var_name = config_data["ai"]["gemini"]["api_key"].split(":", 1)[1]
        env_value = os.getenv(var_name)
        if not env_value:
             raise ConfigError(f"Environment variable '{var_name}' specified for ai.gemini.api_key not found.")
        config_data["ai"]["gemini"]["api_key"] = env_value


    # Cast to AppConfig for type checking, though runtime validation is basic
    # A library like Pydantic could enforce this more strictly
    return config_data # type: ignore


if __name__ == '__main__':
    # Example usage (for testing the loader)
    try:
        # Create a dummy config.yaml for testing if it doesn't exist
        if not Path(DEFAULT_CONFIG_FILENAME).exists():
             print(f"Creating dummy {DEFAULT_CONFIG_FILENAME} for testing...")
             dummy_config = """
github:
  repository: "test/repo"
  token: "ENV:GITHUB_TEST_TOKEN" # Example using env var

ai:
  provider: "openai"
  openai:
    model: "gpt-test"
    api_key: "ENV:OPENAI_TEST_KEY"
    base_url: null
  gemini: null
  temperature: 0.5
  max_tokens: 1000
  strictness_level: "medium"
  focus_areas: ["test"]

project:
  local_path: "./local_project_dummy"

reporting:
  output_dir: "test_results"
  terminal_colors: true

cache:
  enabled: false
  directory: ".test_cache"
"""
             with open(DEFAULT_CONFIG_FILENAME, 'w') as f:
                 f.write(dummy_config)
             print("Set GITHUB_TEST_TOKEN and OPENAI_TEST_KEY environment variables to test.")


        print(f"Attempting to load config from '{DEFAULT_CONFIG_FILENAME}'...")
        # Set dummy env vars if needed for the test run
        os.environ.setdefault("GITHUB_TEST_TOKEN", "dummy_github_token_from_env")
        os.environ.setdefault("OPENAI_TEST_KEY", "dummy_openai_key_from_env")

        loaded_config = load_config()
        print("Config loaded successfully:")
        import json
        print(json.dumps(loaded_config, indent=2))

        # Test accessing a value
        print(f"\nGitHub Repo: {loaded_config['github']['repository']}")
        print(f"GitHub Token: {loaded_config['github']['token']}") # Should show env var value
        print(f"AI Provider: {loaded_config['ai']['provider']}")
        if loaded_config['ai']['openai']:
             print(f"OpenAI API Key: {loaded_config['ai']['openai']['api_key']}") # Should show env var value

    except ConfigError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Clean up dummy file if created
    # if Path(DEFAULT_CONFIG_FILENAME).exists() and "dummy_config" in locals():
    #     print(f"Cleaning up dummy {DEFAULT_CONFIG_FILENAME}...")
    #     Path(DEFAULT_CONFIG_FILENAME).unlink()