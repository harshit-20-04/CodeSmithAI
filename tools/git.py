import subprocess
from langchain_core.tools import tool

PROJECT_ROOT = "workspace/generated_project"

def run_git_command(args: list[str], cwd: str = PROJECT_ROOT) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return f"Git Error:\n{result.stderr}"

        return result.stdout
    except Exception as e:
        return f"Error running Git command: {str(e)}"

@tool
def git_init() -> str:
    """
    Initialize a Git repository in the generated project.
    """
    return run_git_command(["init"])

@tool
def git_status() -> str:
    """
    Show the current Git status of the project.
    """
    return run_git_command(
        ["status", "--short"]
    )

@tool
def git_diff() -> str:
    """
    Show the current changes in the project.
    """
    return run_git_command(
        ["diff"]
    )

@tool
def git_add(files: list[str]) -> str:
    """
    Stage specified files for a Git commit.

    Args:
        files: List of file paths to stage.
    """
    return run_git_command(
        ["add"] + files
    )

@tool
def git_commit(message: str) -> str:
    """
    Commit staged changes to Git.

    Args:
        message: Commit message.
    """
    return run_git_command(
        ["commit", "-m", message]
    )

@tool
def git_log() -> str:
    """
    Show recent Git commit history.
    """
    return run_git_command(
        [
            "log",
            "--oneline",
            "-10"
        ]
    )
