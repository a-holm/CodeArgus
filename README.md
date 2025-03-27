# CodeArgus

CodeArgus is an AI-powered GitHub pull request analyzer that scrutinizes every change with ruthless precision. Like the hundred-eyed giant of Greek myth, it never sleeps—mercilessly hunting for code quality issues, architectural inconsistencies, and hidden risks before they infiltrate your codebase.

It fetches open pull requests from a specified GitHub repository, analyzes the code changes using configurable AI models (like Gemini, OpenAI, or compatible local LLMs), compares them against your local project baseline, and generates detailed reports.

## Features

*   **GitHub Integration:** Fetches open PRs, diffs, and metadata via the GitHub API (`PyGithub`).
*   **Configurable AI Analysis:** Supports multiple AI providers (Gemini, OpenAI, compatible local LLMs) via configuration. Uses the `google-generativeai` and `openai` Python libraries.
*   **Strict Evaluation:** Focuses on configurable areas like code quality, complexity, security vulnerabilities, project impact, and test coverage.
*   **Local Project Context:** Reads files from a local clone of the repository for comparison context (though full context usage is still under development).
*   **Caching:** Caches AI responses to speed up repeated analysis and reduce API costs.
*   **Reporting:** Generates Markdown reports per PR and a summary report in a configurable output directory. Provides terminal summaries.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd CodeArgus
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional: If using a `.env` file for secrets, also run `pip install python-dotenv`)*

## Configuration

1.  **Create `config.yaml`:**
    Copy the example configuration file:
    ```bash
    cp config.yaml.example config.yaml
    ```

2.  **Edit `config.yaml`:**
    Open `config.yaml` in a text editor and configure the following sections:

    *   **`github`:**
        *   `repository`: The target repository in `"owner/repo"` format (e.g., `"your-username/your-project"`).
        *   `token`: Your GitHub Personal Access Token (PAT) with `repo` scope.
            *   **SECURITY WARNING:** It is STRONGLY recommended to use environment variables. Set `token: "ENV:GITHUB_TOKEN"` in the file and create an environment variable named `GITHUB_TOKEN` with your PAT value.
        *   `base_url` (Optional): Use for GitHub Enterprise instances.

    *   **`ai`:**
        *   `provider`: Select your AI provider: `"openai"`, `"gemini"`, or `"local_llm"` (uses the OpenAI configuration).
        *   Configure the corresponding subsection (`openai`, `gemini`):
            *   `model`: The specific model name (e.g., `"gpt-4-turbo-preview"`, `"gemini-pro"`).
            *   `api_key`: Your API key for the selected provider.
                *   **SECURITY WARNING:** Use environment variables! Set `api_key: "ENV:YOUR_PROVIDER_API_KEY"` (e.g., `ENV:OPENAI_API_KEY`, `ENV:GEMINI_API_KEY`) and define the corresponding environment variable. For many local LLMs using the OpenAI provider, the key might be `"ollama"`, `"none"`, or similar.
            *   `base_url` (for `openai` provider): Set this if using a local LLM server or a non-standard OpenAI endpoint (e.g., `"http://localhost:11434/v1"` for Ollama).
        *   `temperature`, `max_tokens`: Optional parameters to control AI generation.
        *   `strictness_level`: Controls the tone/detail of the analysis prompt (e.g., `"high"`).
        *   `focus_areas`: List of specific aspects for the AI to critique (e.g., `"undocumented_changes"`, `"security_vulnerabilities"`, `"project_impact"`, `"test_coverage"`).

    *   **`project`:**
        *   `local_path`: The **absolute or relative path** to the root directory of your local clone of the target GitHub repository. This is crucial for context comparison.

    *   **`reporting`:**
        *   `output_dir`: The directory where Markdown reports will be saved (default: `"analysis_results"`).
        *   `terminal_colors`: Enable/disable colored terminal output (`true` or `false`).

    *   **`cache`:**
        *   `enabled`: Enable/disable AI response caching (`true` or `false`).
        *   `directory`: Directory to store cache files (default: `".code_argus_cache"`).

3.  **Set Environment Variables (Recommended for Secrets):**
    Define the environment variables you specified in `config.yaml` (e.g., `GITHUB_TOKEN`, `OPENAI_API_KEY`) in your terminal session or using a `.env` file (if you installed `python-dotenv`).

    *Example using `.env` file:*
    Create a file named `.env` in the project root:
    ```dotenv
    GITHUB_TOKEN="ghp_YourGitHubTokenHere"
    OPENAI_API_KEY="sk-YourOpenAIKeyHere"
    # GEMINI_API_KEY="YourGeminiKeyHere"
    ```
    *(Note: The current `main.py` doesn't automatically load `.env`. You would need to add `from dotenv import load_dotenv; load_dotenv()` at the beginning of `main()` or run the script in a way that loads it, e.g., using `python-dotenv` CLI.)*

## Running CodeArgus

Ensure your virtual environment is active and environment variables are set. Then, run the main script from the project root directory:

```bash
python -m src.main --config config.yaml
```

Or, if your configuration file is named `config.yaml`:

```bash
python -m src.main
```

The tool will:
1.  Load the configuration.
2.  Connect to GitHub and fetch open pull requests.
3.  Analyze each pull request using the configured AI provider and caching.
4.  Print a summary to the terminal for each PR.
5.  Generate detailed Markdown reports in the directory specified by `reporting.output_dir`.
6.  Generate a summary Markdown report (`analysis_summary.md`) in the same directory.

## Development

See `PLAN.md` for the detailed project plan and architecture. Tests are intended to be placed in the `tests/` directory and run using `pytest`.
