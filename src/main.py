import argparse
import sys
from typing import List, Dict, Any

# Import components
from .config_loader import load_config, ConfigError, AppConfig
from .github_client import GitHubClient, GitHubClientError
from .local_project_reader import LocalProjectReader, LocalProjectError
from .ai_analyzer import AIAnalyzer
from .comparison_engine import ComparisonEngine, ComparisonError
from .reporting_service import ReportingService, ReportingError

def main():
    """
    Main entry point for the CodeArgus application.
    """
    parser = argparse.ArgumentParser(description="CodeArgus: AI Pull Request Analyzer")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to the configuration file (default: config.yaml)"
    )
    args = parser.parse_args()

    config: AppConfig
    github_client: GitHubClient
    local_reader: LocalProjectReader
    ai_analyzer: AIAnalyzer
    comparison_engine: ComparisonEngine
    reporting_service: ReportingService

    try:
        # 1. Load Configuration
        print(f"Loading configuration from: {args.config}")
        config = load_config(args.config)

        # 2. Initialize Components
        print("Initializing components...")
        # TODO: Add logging setup based on config['reporting'].get('log_level')

        reporting_service = ReportingService(
            output_dir=config['reporting']['output_dir'],
            terminal_colors=config['reporting']['terminal_colors']
        )

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

        comparison_engine = ComparisonEngine(
            github_client=github_client,
            local_reader=local_reader,
            ai_analyzer=ai_analyzer,
            config=config # Pass full config for now
        )
        print("Initialization complete.")

        # 3. Fetch Open Pull Requests
        print("\nFetching open pull requests...")
        open_prs = github_client.get_open_pull_requests()

        if not open_prs:
            print("No open pull requests found. Exiting.")
            sys.exit(0)

        # 4. Analyze Each Pull Request
        all_analysis_results: List[Dict[str, Any]] = []
        print(f"\nStarting analysis of {len(open_prs)} pull requests...")

        for pr in open_prs:
            try:
                analysis_result = comparison_engine.analyze_pull_request(pr)
                all_analysis_results.append(analysis_result)

                # 5. Generate Individual Report & Display Summary
                reporting_service.generate_pr_report(analysis_result)
                reporting_service.display_pr_summary(analysis_result)

            except ComparisonError as e:
                # Errors during comparison engine run (already logged by engine)
                print(f"Skipping report generation for PR #{pr.number} due to analysis error: {e}")
                # Add a basic error result if needed for the summary
                all_analysis_results.append({
                    "pr_number": pr.number,
                    "pr_title": pr.title,
                    "pr_url": pr.html_url,
                    "errors": [f"Analysis failed: {e}"]
                })
            except ReportingError as e:
                 # Errors during reporting itself
                 print(f"Reporting error for PR #{pr.number}: {e}")
                 # The analysis might be fine, but reporting failed. Add error to result.
                 # Find the result if it exists and add the reporting error
                 for res in all_analysis_results:
                     if res.get("pr_number") == pr.number:
                         res.setdefault("errors", []).append(f"Reporting failed: {e}")
                         break


        # 6. Generate Summary Report
        print("\nGenerating final summary report...")
        reporting_service.generate_summary_report(all_analysis_results)

        print("\nCodeArgus analysis complete.")
        print(f"Reports generated in: {reporting_service.output_dir.resolve()}")

    except (ConfigError, GitHubClientError, LocalProjectError, ReportingError, ValueError, ImportError) as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("CodeArgus failed to run.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        # TODO: Add more detailed traceback logging here if needed
        print("CodeArgus encountered an unexpected error.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
