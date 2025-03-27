import os
from pathlib import Path
from typing import Dict, Any, List
import datetime

# Assuming config_loader structure is available or passed in
# from .config_loader import ReportingConfig # Or pass config dict directly

class ReportingError(Exception):
    """Custom exception for reporting errors."""
    pass

class ReportingService:
    """
    Generates analysis reports in Markdown format and provides terminal output.
    """
    def __init__(self, output_dir: str, terminal_colors: bool = True):
        """
        Initializes the Reporting Service.

        Args:
            output_dir: The directory where reports should be saved.
            terminal_colors: Whether to use colors in terminal output (using Rich).
        """
        self.output_dir = Path(output_dir)
        self.terminal_colors = terminal_colors
        self._ensure_output_dir()

        if self.terminal_colors:
            try:
                from rich.console import Console
                self.console = Console()
            except ImportError:
                print("Warning: 'rich' package not found. Terminal colors disabled. Install with: pip install rich")
                self.terminal_colors = False
                self.console = None # type: ignore
        else:
             self.console = None # type: ignore

        print(f"Reporting service initialized. Output directory: {self.output_dir.resolve()}")

    def _ensure_output_dir(self):
        """Creates the output directory if it doesn't exist."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ReportingError(f"Could not create report output directory: {self.output_dir}. Error: {e}")

    def _format_ai_response(self, analysis_raw: Dict[str, Any]) -> str:
        """
        Basic formatter for the raw AI response.
        Tries to extract the main text or error message.
        """
        if not analysis_raw:
            return "No analysis data received."
        if "error" in analysis_raw:
            return f"**Analysis Error:**\n```\n{analysis_raw['error']}\n```"
        if "response_text" in analysis_raw:
            # Basic Markdown formatting - assumes AI provides reasonable text
            return analysis_raw["response_text"]
        else:
            # Fallback: dump the raw dictionary
            import json
            return f"**Raw Analysis Data:**\n```json\n{json.dumps(analysis_raw, indent=2)}\n```"

    def generate_pr_report(self, analysis_result: Dict[str, Any]):
        """
        Generates a Markdown report for a single pull request analysis.

        Args:
            analysis_result: The dictionary returned by ComparisonEngine.analyze_pull_request.
        """
        pr_number = analysis_result.get("pr_number", "unknown")
        report_filename = self.output_dir / f"pr_{pr_number}_analysis.md"

        print(f"Generating report for PR #{pr_number} -> {report_filename.name}")

        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(f"# CodeArgus Analysis Report: PR #{pr_number}\n\n")
                f.write(f"**Title:** {analysis_result.get('pr_title', 'N/A')}\n")
                f.write(f"**URL:** {analysis_result.get('pr_url', 'N/A')}\n")
                f.write(f"**Analysis Timestamp:** {datetime.datetime.now().isoformat()}\n\n")

                if analysis_result.get("errors"):
                    f.write("## Errors During Analysis\n\n")
                    for error in analysis_result["errors"]:
                        f.write(f"- `{error}`\n")
                    f.write("\n")

                f.write("## AI Analysis\n\n")
                # TODO: Improve parsing based on expected AI output structure
                ai_content = self._format_ai_response(analysis_result.get("analysis_raw", {}))
                f.write(ai_content)
                f.write("\n")

                # Placeholder for future structured results
                # if "analysis_by_file" in analysis_result and analysis_result["analysis_by_file"]:
                #     f.write("\n## Analysis by File\n\n")
                #     for filename, file_analysis in analysis_result["analysis_by_file"].items():
                #         f.write(f"### `{filename}`\n\n")
                #         # Format file_analysis content
                #         f.write("```\n") # Placeholder
                #         f.write(str(file_analysis))
                #         f.write("\n```\n\n")

        except IOError as e:
            error_msg = f"Failed to write report file {report_filename}: {e}"
            print(f"Error: {error_msg}")
            # Optionally re-raise or handle differently
            raise ReportingError(error_msg) from e

    def generate_summary_report(self, all_results: List[Dict[str, Any]]):
        """
        Generates a summary Markdown report for all analyzed pull requests.
        (Placeholder implementation)
        """
        summary_filename = self.output_dir / "analysis_summary.md"
        print(f"Generating summary report -> {summary_filename.name}")

        total_prs = len(all_results)
        prs_with_errors = sum(1 for res in all_results if res.get("errors"))
        # TODO: Add more sophisticated summary metrics once AI parsing is better

        try:
            with open(summary_filename, 'w', encoding='utf-8') as f:
                f.write("# CodeArgus Analysis Summary\n\n")
                f.write(f"**Analysis Timestamp:** {datetime.datetime.now().isoformat()}\n")
                f.write(f"**Total Pull Requests Analyzed:** {total_prs}\n")
                f.write(f"**Pull Requests with Analysis Errors:** {prs_with_errors}\n\n")

                f.write("## Analyzed Pull Requests\n\n")
                if not all_results:
                    f.write("No pull requests were analyzed.\n")
                else:
                    f.write("| PR # | Title | Status | Report File |\n")
                    f.write("|------|-------|--------|-------------|\n")
                    for result in all_results:
                        pr_num = result.get('pr_number', 'N/A')
                        title = result.get('pr_title', 'N/A')
                        status = "Error" if result.get("errors") else "Analyzed"
                        # Link to the individual report
                        report_link = f"[pr_{pr_num}_analysis.md](./pr_{pr_num}_analysis.md)"
                        f.write(f"| {pr_num} | {title[:50]}{'...' if len(title)>50 else ''} | {status} | {report_link} |\n")

        except IOError as e:
            error_msg = f"Failed to write summary report file {summary_filename}: {e}"
            print(f"Error: {error_msg}")
            raise ReportingError(error_msg) from e

    def display_pr_summary(self, analysis_result: Dict[str, Any]):
        """Displays a brief summary of a single PR analysis to the terminal."""
        pr_number = analysis_result.get("pr_number", "unknown")
        title = analysis_result.get('pr_title', 'N/A')
        has_errors = bool(analysis_result.get("errors"))
        report_filename = f"pr_{pr_number}_analysis.md"

        if self.terminal_colors and self.console:
            status_style = "bold red" if has_errors else "bold green"
            status_text = "Error" if has_errors else "Analyzed"
            self.console.print(f"PR #{pr_number}: '{title}' - [{status_style}]{status_text}[/]. Report: {self.output_dir / report_filename}")
        else:
            status_text = "Error" if has_errors else "Analyzed"
            print(f"PR #{pr_number}: '{title}' - {status_text}. Report: {self.output_dir / report_filename}")
        if has_errors:
             for error in analysis_result.get("errors", []):
                 if self.terminal_colors and self.console:
                     self.console.print(f"  [red]Error:[/] {error}")
                 else:
                     print(f"  Error: {error}")


# --- Example Usage (for testing) ---
if __name__ == '__main__':
    import tempfile

    # Dummy analysis results
    dummy_result_ok = {
        "pr_number": 101,
        "pr_title": "Add new feature X",
        "pr_url": "http://example.com/pr/101",
        "analysis_raw": {
            "provider": "dummy",
            "model": "dummy-model",
            "response_text": "### Analysis\n\n- Looks mostly good.\n- Consider adding more tests for edge cases.\n- Minor style nitpick on line 42."
        },
        "errors": []
    }
    dummy_result_error = {
        "pr_number": 102,
        "pr_title": "Fix critical bug Y",
        "pr_url": "http://example.com/pr/102",
        "analysis_raw": {},
        "errors": ["Failed to fetch diff from GitHub.", "AI analysis timed out."]
    }
    dummy_result_ai_error = {
        "pr_number": 103,
        "pr_title": "Refactor module Z",
        "pr_url": "http://example.com/pr/103",
        "analysis_raw": {
            "provider": "openai",
            "error": "API key invalid or quota exceeded."
        },
        "errors": ["AI analysis failed: API key invalid or quota exceeded."]
    }

    all_dummy_results = [dummy_result_ok, dummy_result_error, dummy_result_ai_error]

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Using temporary directory for reports: {tmpdir}")
        try:
            # Test with terminal colors enabled
            print("\n--- Testing with Terminal Colors Enabled ---")
            reporter_color = ReportingService(output_dir=tmpdir, terminal_colors=True)
            reporter_color.generate_pr_report(dummy_result_ok)
            reporter_color.generate_pr_report(dummy_result_error)
            reporter_color.generate_pr_report(dummy_result_ai_error)
            reporter_color.generate_summary_report(all_dummy_results)

            print("\nTerminal Summary Output:")
            reporter_color.display_pr_summary(dummy_result_ok)
            reporter_color.display_pr_summary(dummy_result_error)
            reporter_color.display_pr_summary(dummy_result_ai_error)


            # Test with terminal colors disabled
            print("\n--- Testing with Terminal Colors Disabled ---")
            reporter_no_color = ReportingService(output_dir=tmpdir, terminal_colors=False)
            print("\nTerminal Summary Output (no color):")
            reporter_no_color.display_pr_summary(dummy_result_ok)
            reporter_no_color.display_pr_summary(dummy_result_error)

            print("\nReports generated in:", tmpdir)
            # You can manually check the .md files in the tmpdir

        except ReportingError as e:
            print(f"\nReporting Error: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")