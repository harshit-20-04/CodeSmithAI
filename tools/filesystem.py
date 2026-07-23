import os
from langchain_core.tools import tool

@tool
def list_files(path: str) -> str:
    """List files in a project directory."""
    if not os.path.exists(path):
        return f"Directory does not exist: {path}"
    result = []
    for root, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)

            relative_path = os.path.relpath(
                full_path,
                path
            )
            result.append(relative_path)
    return "\n".join(result)

@tool
def read_file(file_name: str, path: str) -> str:
    """Read the contents of a file."""
    path_file = os.path.join(
        path,
        file_name
    )
    if not os.path.exists(path_file):
        return f"File does not exist: {path_file}"
    try:
        with open(path_file, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(file_name: str, path: str, content: str) -> str:
    """Create or overwrite a file."""
    try:
        os.makedirs(
            path,
            exist_ok=True
        )
        path_file = os.path.join(
            path,
            file_name
        )
        with open(path_file, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote {path_file}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def edit_file(file_name: str, path: str, content: str) -> str:
    """Replace the complete contents of an existing file."""
    path_file = os.path.join(
        path,
        file_name
    )
    if not os.path.exists(path_file):
        return f"File does not exist: {path_file}"
    try:
        with open(path_file, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully edited {path_file}"
    except Exception as e:
        return f"Error editing file: {str(e)}"
