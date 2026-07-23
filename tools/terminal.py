import subprocess
from langchain_core.tools import tool


PROJECT_ROOT = "workspace/generated_project"


ALLOWED_COMMANDS = {
    "python",
    "pytest",
    "pip",
    "uvicorn",
    "ruff",
    "black"
}

@tool
def run_command(command: str) -> str:
    """
    Execute an allowed terminal command inside the generated project.
    """
    command_name = command.split()[0]
    if command_name not in ALLOWED_COMMANDS:
        return (
            f"Command '{command_name}' "
            f"is not allowed."
        )
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"""
Exit Code:
{result.returncode}

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Execution error: {str(e)}"