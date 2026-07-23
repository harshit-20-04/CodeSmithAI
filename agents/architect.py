from typing import List
from graph.state import AgentState
from dotenv import load_dotenv
load_dotenv()
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel, Field

from graph.state import AgentState

llm = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0
)

class APIEndPoint(BaseModel):
    method:str = Field(
        description="HTTP method such as GET, POST, PUT, DELETE"
    )

    path:str = Field(
        description="Path to Endpoint API"
    )
    
    description: str= Field(
        description="What this endpoint does"
    )

class ArchitecturePlan(BaseModel):
    project_structure: List[str] = Field(
        description="The files and folders required by the project."
    )
    technologies: List[str] = Field(
        description="Technologies, frameworks, libraries and tools."
    )
    components: List[str] = Field(
        description="Major components of the software."
    )
    database_design: str = Field(
        description="Description of the database design."
    )
    api_design: List[APIEndPoint] = Field(
        description="List of API endpoints required by the application."
    )
    architecture_explanation: str

architecture_llm = llm.with_structured_output(
    ArchitecturePlan
)

ARCHTIECTURE_PROMPT = """
You are the Architecture Agent of an autonomous AI Software Engineer.
Your job is to design the architecture of a software project.
You receive :
1. The Orginal User Request.
2. The development plan created by the Planner Agent.

You must design:
- Project folder structure
- Technologies
- Major Components
- Database Design
- API Design
- Architecture Explanation

Do not write implementation Code.

The architecture should directly support the development plan.

"""

def architect_agent(state: AgentState):
    prompt = f"""
    {ARCHTIECTURE_PROMPT}

    USER REQUEST:
    {state['user_request']}

    DEVELOPMENT PLAN:
    {state['plan']}

    Design the complete architecture.
    """

    architecture = architecture_llm.invoke(prompt)

    print("==========Architecture===========")
    print("\nProject Structure : ")
    print()

    for item in architecture.project_structure:
        print(item)
    
    print("\nTechnologies:")
    print()

    for tech in architecture.technologies:
        print(tech)
    
    print("\nComponents:")
    print()

    for component in architecture.components:
        print(component)
    
    print("\nDatabase Design:")
    print(architecture.database_design)

    print("\nAPI Design:")
    print()

    for api in architecture.api_design:
        print(
            f"{api.method}"
            f"{api.path} - "
            f"{api.description}"
        )
    
    print("\nArchitecture Explanation: ")
    print()
    print(architecture.architecture_explanation)
    print("=======================================")

    api_design_text = "\n".join(
        f"{api.method} {api.path} - {api.description}"
        for api in architecture.api_design
    )

    architecture_text = f"""
    PROJECT STRUCTURE : 
    {chr(10).join(architecture.project_structure)}

    TECHNOLOGIES :
    {chr(10).join(architecture.technologies)}

    DATABASE DESIGN :
    {architecture.database_design}

    COMPONENTS:
    {chr(10).join(architecture.components)}

    API DESIGN:
    {api_design_text}

    ARCHITECTURE EXPLANATION:
    {architecture.architecture_explanation}
    """
    return {
        "architecture": architecture_text
    }