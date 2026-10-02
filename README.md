# CodeSmith AI

CodeSmith AI is an autonomous multi-agent software engineering framework powered by LangGraph, Mistral AI, and Groq. It automatically plans, architects, writes, and tests code based on high-level natural language requirements.

---

## 🏗 Architecture

CodeSmith orchestrates multiple specialized agents using a directed state graph:

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
        |      |          |          |      |
        v      v          v          v      v
     Planner Architect  Coder     Tester Debugger
                          |
                          v
                     Tools & Workspace
```

1. **Manager Agent (`codestral-latest`)**: Central coordinator that inspects progress, chooses the next specialized agent, and assigns specific tasks.
2. **Planner Agent (`codestral-latest`)**: Breaks the requirement down into an ordered, dependency-aware list of actionable development tasks.
3. **Architect Agent (`codestral-latest`)**: Designs project folder structure, technology stack, database schemas, and API endpoints.
4. **Coder Agent Subgraph (`openai/gpt-oss-120b` on Groq + `codestral-latest`)**: Autonomous coding agent with tool-calling capabilities (`list_files`, `read_file`, `write_file`, `edit_file`, `run_command`) that executes tasks inside the workspace.

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
GROQ_API_KEY=your_groq_api_key_here
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
