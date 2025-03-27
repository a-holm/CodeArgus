from github import Github, GithubException, Auth
from github.PullRequest import PullRequest
from typing import List, Optional, Dict, Any

# Assuming config_loader structure is available or passed in
# from .config_loader import GitHubConfig # Or pass config dict directly

class GitHubClientError(Exception):
    """Custom exception for GitHub client errors."""
    pass

class GitHubClient:
    """
    A client to interact with the GitHub API using PyGithub.
    Handles fetching pull requests and their diffs.
    """
    def __init__(self, repo_name: str, token: str, base_url: Optional[str] = None):
        """
        Initializes the GitHub client.

        Args:
            repo_name: The name of the repository (e.g., "owner/repo").
            token: The GitHub API token for authentication.
            base_url: Optional base URL for GitHub Enterprise instances.

        Raises:
            GitHubClientError: If authentication fails or the repository is not found.
        """
        self.repo_name = repo_name
        try:
            auth = Auth.Token(token)
            if base_url:
                self._gh = Github(auth=auth, base_url=base_url)
            else:
                self._gh = Github(auth=auth)

            # Verify authentication and repository access
            self._user = self._gh.get_user() # Basic check to see if token is valid
            self._repo = self._gh.get_repo(self.repo_name)
            print(f"Successfully authenticated as GitHub user: {self._user.login}")
            print(f"Accessing repository: {self._repo.full_name}")

        except GithubException as e:
            raise GitHubClientError(f"GitHub API error during initialization: {e.status} {e.data}") from e
        except Exception as e:
            # Catch potential network errors or other unexpected issues
            raise GitHubClientError(f"Unexpected error during GitHub client initialization: {e}") from e

    def get_open_pull_requests(self) -> List[PullRequest]:
        """
        Fetches all open pull requests for the configured repository.

        Returns:
            A list of PyGithub PullRequest objects.

        Raises:
            GitHubClientError: If there's an error fetching pull requests.
        """
        try:
            pulls = self._repo.get_pulls(state='open', sort='created', direction='desc')
            # Convert PaginatedList to a simple list for easier handling downstream
            open_prs = list(pulls)
            print(f"Found {len(open_prs)} open pull requests.")
            return open_prs
        except GithubException as e:
            raise GitHubClientError(f"GitHub API error fetching open pull requests: {e.status} {e.data}") from e
        except Exception as e:
            raise GitHubClientError(f"Unexpected error fetching open pull requests: {e}") from e

    def get_pull_request_diff(self, pr_number: int) -> str:
        """
        Fetches the diff content for a specific pull request.

        Args:
            pr_number: The number of the pull request.

        Returns:
            A string containing the diff.

        Raises:
            GitHubClientError: If the PR is not found or there's an error fetching the diff.
        """
        try:
            pr = self._repo.get_pull(pr_number)
            # PyGithub's get_diff() returns bytes, decode to string
            diff_content_bytes = pr.get_diff()
            diff_content = diff_content_bytes.decode('utf-8')
            print(f"Fetched diff for PR #{pr_number} ({len(diff_content)} characters).")
            return diff_content
        except GithubException as e:
            if e.status == 404:
                raise GitHubClientError(f"Pull Request #{pr_number} not found in repository {self.repo_name}.") from e
            else:
                raise GitHubClientError(f"GitHub API error fetching diff for PR #{pr_number}: {e.status} {e.data}") from e
        except Exception as e:
            raise GitHubClientError(f"Unexpected error fetching diff for PR #{pr_number}: {e}") from e

    # --- Future Methods (Placeholder) ---

    # def get_pull_request_metadata(self, pr_number: int) -> Dict[str, Any]:
    #     """Fetches metadata like description, comments, etc."""
    #     # Implementation using pr.body, pr.get_comments(), etc.
    #     pass

    # def post_comment(self, pr_number: int, comment_body: str):
    #      """Posts a comment to a pull request."""
    #      # Implementation using pr.create_issue_comment()
    #      pass


# --- Example Usage (for testing) ---
if __name__ == '__main__':
    from config_loader import load_config, ConfigError

    try:
        # Load config - assumes config.yaml exists and is valid
        # You might need to manually create a config.yaml from the example
        # and set a real repo and token (or use ENV: syntax)
        print("Loading configuration for GitHub client test...")
        config = load_config() # Uses default 'config.yaml'

        # Ensure required config sections are present
        if not config.get('github'):
            raise ConfigError("Missing 'github' section in configuration.")

        repo = config['github']['repository']
        token = config['github']['token']
        base_url = config['github'].get('base_url') # Optional

        if not repo or repo == "owner/repo-name":
             print("\nWARNING: 'github.repository' in config.yaml is not set or is the default.")
             print("Skipping live GitHub API tests.")
        elif not token or token == "YOUR_GITHUB_API_TOKEN":
             print("\nWARNING: 'github.token' in config.yaml is not set or is the default.")
             print("Skipping live GitHub API tests.")
        else:
            print(f"\nInitializing GitHubClient for repository: {repo}")
            client = GitHubClient(repo_name=repo, token=token, base_url=base_url)

            print("\nFetching open pull requests...")
            open_prs = client.get_open_pull_requests()

            if open_prs:
                print(f"\nFound {len(open_prs)} open PRs:")
                for pr in open_prs[:3]: # Print details for the first few
                    print(f"  - PR #{pr.number}: {pr.title} (by {pr.user.login})")

                # Test fetching diff for the first open PR
                first_pr_number = open_prs[0].number
                print(f"\nFetching diff for PR #{first_pr_number}...")
                diff = client.get_pull_request_diff(first_pr_number)
                print(f"Diff for PR #{first_pr_number} (first 500 chars):\n--- DIFF START ---")
                print(diff[:500])
                print("--- DIFF END ---")
            else:
                print("No open pull requests found in the repository.")

    except ConfigError as e:
        print(f"\nConfiguration Error: {e}")
        print("Please ensure 'config.yaml' exists, is correctly formatted, and contains valid GitHub details.")
    except GitHubClientError as e:
        print(f"\nGitHub Client Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")