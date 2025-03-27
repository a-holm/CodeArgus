import re
from typing import Dict, Any, List, Optional

# Assuming other components are importable
from .github_client import GitHubClient, GitHubClientError, PullRequest
from .local_project_reader import LocalProjectReader, LocalProjectError
from .ai_analyzer import AIAnalyzer
# from .config_loader import AppConfig # Or pass config dict directly

class ComparisonError(Exception):
    """Custom exception for comparison engine errors."""
    pass

class ComparisonEngine:
    """
    Orchestrates the analysis of a single pull request by comparing its
    changes against the local project and using the AI Analyzer.
    """
    def __init__(self,
                 github_client: GitHubClient,
                 local_reader: LocalProjectReader,
                 ai_analyzer: AIAnalyzer,
                 config: Dict[str, Any]): # Pass relevant parts or full config
        """
        Initializes the Comparison Engine.

        Args:
            github_client: An initialized GitHubClient instance.
            local_reader: An initialized LocalProjectReader instance.
            ai_analyzer: An initialized AIAnalyzer instance.
            config: The application configuration dictionary.
        """
        self.github_client = github_client
        self.local_reader = local_reader
        self.ai_analyzer = ai_analyzer
        self.config = config
        self.ai_focus_areas = config.get('ai', {}).get('focus_areas', [])
        self.project_config = config.get('project', {})

    def _parse_diff_filenames(self, diff_content: str) -> List[str]:
        """
        Parses a diff string to extract unique filenames that were changed.
        Handles both modified/added files (--- a/..., +++ b/...) and potentially
        renamed files (though full rename handling is complex).

        Args:
            diff_content: The diff string.

        Returns:
            A list of unique relative file paths mentioned in the diff headers.
        """
        # Regex to find filenames in diff headers (covers --- a/ and +++ b/)
        # It captures the path after the initial 'a/' or 'b/'
        # Handles spaces in filenames, but might need refinement for edge cases.
        filename_pattern = re.compile(r'^(?:--- a/|\+\+\+ b/)(.+?)(?:\t.*)?$', re.MULTILINE)
        filenames = set()
        for match in filename_pattern.finditer(diff_content):
            filename = match.group(1).strip()
            # Ignore /dev/null for new/deleted files
            if filename != '/dev/null':
                filenames.add(filename)

        # TODO: Add more robust handling for renamed files if needed.
        # This might involve looking for 'rename from'/'rename to' lines.

        sorted_filenames = sorted(list(filenames))
        print(f"Parsed {len(sorted_filenames)} unique filenames from diff.")
        return sorted_filenames

    def _check_test_coverage_needed(self) -> bool:
        """
        Checks if test coverage analysis should be included based on project structure.
        Looks for common test directories or test framework dependencies.
        """
        if "test_coverage" not in self.ai_focus_areas:
            return False # Not requested in config

        # 1. Check for common test directories
        test_indicators = self.project_config.get("test_indicators", ["tests/", "test/"])
        for indicator in test_indicators:
            if self.local_reader.directory_exists(indicator):
                print(f"Test directory indicator '{indicator}' found. Requesting test coverage analysis.")
                return True

        # 2. Check for test dependencies in requirements.txt or pyproject.toml
        test_deps = self.project_config.get("test_dependency_markers", ["pytest", "unittest"])
        req_files = self.local_reader.find_files("**/requirements*.txt") + \
                    self.local_reader.find_files("**/pyproject.toml")

        for req_file_path in req_files:
            content = self.local_reader.read_file(req_file_path)
            if content:
                for dep in test_deps:
                    # Basic check, might need refinement (e.g., handle comments, versions)
                    if dep in content.lower():
                        print(f"Test dependency marker '{dep}' found in '{req_file_path}'. Requesting test coverage analysis.")
                        return True

        print("No strong indicators for tests found. Skipping specific test coverage analysis request.")
        return False


    def analyze_pull_request(self, pr: PullRequest) -> Dict[str, Any]:
        """
        Analyzes a given pull request.

        Args:
            pr: A PyGithub PullRequest object.

        Returns:
            A dictionary containing the aggregated analysis results for the PR.

        Raises:
            ComparisonError: If errors occur during the analysis process.
        """
        print(f"\n--- Analyzing Pull Request #{pr.number}: {pr.title} ---")
        pr_results: Dict[str, Any] = {
            "pr_number": pr.number,
            "pr_title": pr.title,
            "pr_url": pr.html_url,
            "analysis_by_file": {},
            "overall_impact_analysis": None, # Placeholder for AI's project impact assessment
            "errors": []
        }

        try:
            # 1. Get the diff
            diff_content = self.github_client.get_pull_request_diff(pr.number)
            if not diff_content:
                print("Warning: Empty diff content received.")
                # Decide how to handle empty diffs - maybe skip analysis?
                return pr_results # Return early or add a note

            # 2. Parse filenames from diff
            changed_files = self._parse_diff_filenames(diff_content)
            if not changed_files:
                 print("Warning: Could not parse any filenames from the diff.")
                 # Decide how to handle - maybe diff format issue?
                 return pr_results

            # 3. Determine if test coverage analysis is needed
            include_test_analysis = self._check_test_coverage_needed()
            current_criteria = list(self.ai_focus_areas) # Copy base criteria
            if not include_test_analysis and "test_coverage" in current_criteria:
                 current_criteria.remove("test_coverage") # Remove if not applicable

            # 4. Analyze each changed file (Simplified - analyze full diff for now)
            # TODO: Implement per-file analysis by splitting the diff if needed.
            # For now, send the whole diff and ask AI to comment per file.
            print(f"Analyzing full diff for {len(changed_files)} files using criteria: {current_criteria}")

            # Get context (maybe just list files for now, or skip context)
            # Providing full local file content for all changed files might exceed token limits.
            # Strategy: Analyze diff first, maybe fetch specific local files later if AI needs context.
            # For now, we pass None as context.
            local_context = None
            # Alternative: Provide list of changed files as context?
            # local_context = f"Files changed in this PR: {', '.join(changed_files)}"

            ai_analysis = self.ai_analyzer.analyze(
                diff=diff_content,
                context=local_context,
                criteria=current_criteria
            )

            # Store the raw analysis result (needs parsing later by reporting service)
            # Assuming the AI response might contain sections per file or an overall summary.
            pr_results["analysis_raw"] = ai_analysis # Store the whole AI response for now

            # Placeholder for extracting overall impact if AI provides it separately
            # if "overall_impact" in ai_analysis.get("structured_results", {}):
            #    pr_results["overall_impact_analysis"] = ai_analysis["structured_results"]["overall_impact"]

            if "error" in ai_analysis:
                 pr_results["errors"].append(f"AI analysis failed: {ai_analysis['error']}")


            # TODO: Refine how results are structured. Ideally, the AI provides
            # feedback linked to specific files/lines, which we'd store in
            # pr_results["analysis_by_file"]. This requires more sophisticated
            # prompt engineering and response parsing.

            print(f"--- Finished Analysis for PR #{pr.number} ---")

        except (GitHubClientError, LocalProjectError) as e:
            error_msg = f"Error during analysis of PR #{pr.number}: {e}"
            print(error_msg)
            pr_results["errors"].append(error_msg)
            # Optionally re-raise or handle differently
            # raise ComparisonError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during analysis of PR #{pr.number}: {e}"
            print(error_msg)
            pr_results["errors"].append(error_msg)
            # Optionally re-raise
            # raise ComparisonError(error_msg) from e

        return pr_results


# --- Example Usage (for testing) ---
if __name__ == '__main__':
    # This example requires significant setup:
    # 1. A valid config.yaml with GitHub repo, token, AI provider details, local project path.
    # 2. The local project path must exist.
    # 3. Environment variables for API keys if using ENV: syntax.
    # 4. An accessible GitHub repository with open PRs.

    from config_loader import load_config, ConfigError
    from github_client import GitHubClient
    from local_project_reader import LocalProjectReader
    from ai_analyzer import AIAnalyzer

    try:
        print("Loading configuration for Comparison Engine test...")
        config = load_config()

        # Basic validation
        if not all(k in config for k in ['github', 'project', 'ai', 'cache']):
             raise ConfigError("Missing required sections in config.yaml")

        # Initialize components
        print("Initializing components...")
        github_client = GitHubClient(
            repo_name=config['github']['repository'],
            token=config['github']['token'],
            base_url=config['github'].get('base_url')
        )
        local_reader = LocalProjectReader(
            project_base_path=config['project']['local_path']
        )
        ai_analyzer = AIAnalyzer(
            ai_config=config['ai'],
            cache_config=config['cache']
        )

        engine = ComparisonEngine(github_client, local_reader, ai_analyzer, config)

        # Fetch one open PR for testing
        print("\nFetching one open pull request...")
        open_prs = github_client.get_open_pull_requests()

        if not open_prs:
            print("No open pull requests found in the repository to test the engine.")
        else:
            test_pr = open_prs[0]
            analysis_result = engine.analyze_pull_request(test_pr)

            print("\n--- Analysis Result ---")
            import json
            print(json.dumps(analysis_result, indent=2))

            if analysis_result.get("errors"):
                print("\nErrors occurred during analysis:")
                for err in analysis_result["errors"]:
                    print(f"- {err}")

    except ConfigError as e:
        print(f"\nConfiguration Error: {e}")
        print("Please ensure 'config.yaml' is correctly set up.")
    except (GitHubClientError, LocalProjectError, ComparisonError, ValueError, ImportError) as e:
         print(f"\nError during engine test: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")