# CodeSmith AI

CodeSmith AI is an autonomous multi-agent software engineering framework powered by LangGraph and Mistral AI (`codestral-latest`). It automatically plans, architects, writes, tests, debugs, and reviews code based on high-level natural language requirements.

---

## 🏗 Architecture

CodeSmith orchestrates specialized agents using a directed state graph:

```
                  +---------------+
                  |  User Request |
                  +-------+-------+
                          |
                          v
                  +---------------+
        +-------->|    Manager    |<--------+
        |         +-------+-------+         |
        |                 |                 |
        |      +----------+----------+      |
        |      |     |    |    |     |      |
        v      v     v    v    v     v      v
     Planner Arch Coder Test Debug Review  Doc
                          |
                          v
                   Tools & Workspace
```

1. **Manager Agent (`codestral-latest`)**: Central coordinator that inspects progress, chooses the next specialized agent, and assigns specific tasks.
2. **Planner Agent (`codestral-latest`)**: Breaks the requirement down into an ordered, dependency-aware list of actionable development tasks.
3. **Architect Agent (`codestral-latest`)**: Designs project folder structure, technology stack, database schemas, and API endpoints.
4. **Coder Agent Subgraph (`codestral-latest`)**: Autonomous coding agent with tool-calling capabilities (`list_files`, `read_file`, `write_file`, `edit_file`, `run_command`) that implements tasks inside the workspace.
5. **Tester Agent (`codestral-latest`)**: Discovers and runs tests (via `pytest`, `unittest`) to verify functionality.
6. **Debugger Agent (`codestral-latest`)**: Diagnoses root causes of test or implementation failures, applies targeted fixes, and re-verifies.
7. **Reviewer Agent (`codestral-latest`)**: Inspects code quality, architecture compliance, security, and provides a formal review score and feedback.

---

## ⚙️ Setup & Configuration

### 1. Environment Requirements
- Python 3.11+
- Virtual environment (`venv`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys in `.env`
Create or edit `.env` in the project root:
```ini
MISTRAL_API_KEY=your_mistral_api_key_here
```

---

## 🚀 Running the Project

### Default Run
Run the multi-agent pipeline with the default project request:
```bash
python test.py
```

### Custom Prompt Run
Pass any software requirement directly via command-line arguments:
```bash
python test.py "Create a CLI tool that converts Celsius to Fahrenheit with unit tests"
```

### Generated Code
All code produced by the autonomous agents is created inside:
```
workspace/generated_project/
```
