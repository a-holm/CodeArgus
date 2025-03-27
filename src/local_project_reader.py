import os
from pathlib import Path
from typing import Optional, List

class LocalProjectError(Exception):
    """Custom exception for local project reading errors."""
    pass

class LocalProjectReader:
    """
    Reads files and checks existence within a specified local project directory.
    """
    def __init__(self, project_base_path: str):
        """
        Initializes the reader with the base path of the local project.

        Args:
            project_base_path: The absolute or relative path to the root of the
                               local project clone.

        Raises:
            LocalProjectError: If the project base path does not exist or is not a directory.
        """
        self.base_path = Path(project_base_path).resolve() # Ensure absolute path
        if not self.base_path.is_dir():
            raise LocalProjectError(
                f"Local project path does not exist or is not a directory: {self.base_path}"
            )
        print(f"Local project reader initialized for path: {self.base_path}")

    def read_file(self, relative_path: str) -> Optional[str]:
        """
        Reads the content of a file within the project directory.

        Args:
            relative_path: The path of the file relative to the project base path.
                           Uses forward slashes as separators, consistent with diffs.

        Returns:
            The content of the file as a string, or None if the file does not exist
            or cannot be read.
        """
        # Normalize path separators for the local filesystem
        # Pathlib handles this reasonably well, but explicit conversion might be safer
        # depending on how relative_path is generated (e.g., from git diff).
        # Assuming relative_path uses '/' from diffs.
        file_path = self.base_path / Path(relative_path.replace('\\', '/'))

        try:
            # Resolve to prevent path traversal issues (though Pathlib helps)
            resolved_path = file_path.resolve()
            # Double-check it's still within the base path
            if not resolved_path.is_relative_to(self.base_path):
                 print(f"Warning: Attempted to read file outside project base path: {relative_path}")
                 return None

            if resolved_path.is_file():
                with open(resolved_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # print(f"Read file: {relative_path} ({len(content)} chars)")
                return content
            else:
                # print(f"File not found in local project: {relative_path} (resolved: {resolved_path})")
                return None
        except FileNotFoundError:
             # print(f"File not found exception for: {relative_path}")
             return None
        except PermissionError:
            print(f"Warning: Permission denied reading file: {relative_path}")
            return None
        except Exception as e:
            print(f"Warning: Error reading file {relative_path}: {e}")
            return None

    def path_exists(self, relative_path: str) -> bool:
        """
        Checks if a file or directory exists within the project directory.

        Args:
            relative_path: The path relative to the project base path.

        Returns:
            True if the path exists, False otherwise.
        """
        target_path = (self.base_path / Path(relative_path.replace('\\', '/'))).resolve()
        # Check it's within the base path for safety
        if not target_path.is_relative_to(self.base_path):
            return False
        return target_path.exists()

    def directory_exists(self, relative_path: str) -> bool:
        """
        Checks if a directory exists within the project directory.

        Args:
            relative_path: The path relative to the project base path.

        Returns:
            True if the path exists and is a directory, False otherwise.
        """
        target_path = (self.base_path / Path(relative_path.replace('\\', '/'))).resolve()
        if not target_path.is_relative_to(self.base_path):
            return False
        return target_path.is_dir()

    def find_files(self, pattern: str) -> List[str]:
        """
        Finds files matching a glob pattern within the project directory.

        Args:
            pattern: A glob pattern (e.g., "**/requirements.txt", "*.py").

        Returns:
            A list of relative paths (using forward slashes) matching the pattern.
        """
        matches = []
        try:
            for path in self.base_path.rglob(pattern):
                if path.is_file():
                    # Convert back to relative path with forward slashes
                    relative = path.relative_to(self.base_path).as_posix()
                    matches.append(relative)
            return matches
        except Exception as e:
            print(f"Warning: Error searching for files with pattern '{pattern}': {e}")
            return []


# --- Example Usage (for testing) ---
if __name__ == '__main__':
    import tempfile
    import shutil

    # Create a temporary directory structure for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Created temporary project directory: {tmpdir}")
        base_path = Path(tmpdir)

        # Create some dummy files and directories
        (base_path / "src").mkdir()
        (base_path / "src" / "main.py").write_text("print('hello world')\n", encoding='utf-8')
        (base_path / "README.md").write_text("# Test Project\n", encoding='utf-8')
        (base_path / "tests").mkdir()
        (base_path / "tests" / "test_main.py").write_text("assert True\n", encoding='utf-8')
        (base_path / ".hidden_file").write_text("secret", encoding='utf-8')

        try:
            print("\nInitializing LocalProjectReader...")
            reader = LocalProjectReader(str(base_path))

            print("\nTesting file reading:")
            readme_content = reader.read_file("README.md")
            print(f"README.md content: {readme_content.strip() if readme_content else 'Not Found'}")

            main_py_content = reader.read_file("src/main.py")
            print(f"src/main.py content: {main_py_content.strip() if main_py_content else 'Not Found'}")

            non_existent = reader.read_file("non_existent.txt")
            print(f"non_existent.txt content: {'Not Found' if non_existent is None else 'Found?!'}")

            # Test reading outside base path (should fail safely)
            # Note: This depends on OS and how paths are constructed.
            # Pathlib's resolve() and is_relative_to() provide good protection.
            outside_content = reader.read_file("../some_other_file.txt")
            print(f"../some_other_file.txt content: {'Not Found' if outside_content is None else 'Found?!'}")


            print("\nTesting path existence:")
            print(f"Does 'src' exist? {reader.path_exists('src')}")
            print(f"Does 'src/main.py' exist? {reader.path_exists('src/main.py')}")
            print(f"Does 'data' exist? {reader.path_exists('data')}")

            print("\nTesting directory existence:")
            print(f"Is 'src' a directory? {reader.directory_exists('src')}")
            print(f"Is 'src/main.py' a directory? {reader.directory_exists('src/main.py')}")

            print("\nTesting file finding:")
            py_files = reader.find_files("*.py") # Non-recursive in top-level
            print(f"*.py files (top-level): {py_files}")
            all_py_files = reader.find_files("**/*.py") # Recursive
            print(f"**/*.py files (recursive): {all_py_files}")
            readme_files = reader.find_files("**/README.md")
            print(f"**/README.md files: {readme_files}")


        except LocalProjectError as e:
            print(f"\nLocal Project Error: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

    print("\nTemporary directory cleaned up.")