import os
import sys
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
        os.makedirs(PROJECT_ROOT, exist_ok=True)
        env = os.environ.copy()
        venv_scripts = os.path.join(sys.prefix, "Scripts")
        if os.path.exists(venv_scripts):
            env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        stdout = result.stdout.strip() if result.stdout and result.stdout.strip() else "(none)"
        stderr = result.stderr.strip() if result.stderr and result.stderr.strip() else "(none)"
        return f"Exit Code: {result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Execution error: {str(e)}"