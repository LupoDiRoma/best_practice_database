from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select
from sqlalchemy.orm import Session
from llama_index.llms.ollama import Ollama
from llama_index.agent import FunctionCallingAgent
from llama_index.tools import FunctionTool

# 1. Setup SQLite Database
engine = create_engine("sqlite:///patients.db", echo=False)
metadata = MetaData()

# Define tables
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, nullable=False),
    Column("role", String, nullable=False),
)

patients = Table(
    "patients", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("provider_name", String, nullable=False),
    Column("condition", String, nullable=False),
)

metadata.create_all(engine)

# Pre-populate database (only if empty)
with Session(engine) as session:
    if session.query(users).count() == 0:
        session.execute(users.insert(), [
            {"username": "dr_smith", "role": "doctor"},
            {"username": "nurse_johnson", "role": "nurse"},
            {"username": "receptionist_amy", "role": "receptionist"},
        ])
    if session.query(patients).count() == 0:
        session.execute(patients.insert(), [
            {"name": "John Doe", "provider_name": "Dr. Smith", "condition": "Flu"},
            {"name": "Jane Roe", "provider_name": "Dr. Smith", "condition": "Diabetes"},
            {"name": "Mary Major", "provider_name": "Dr. Brown", "condition": "Asthma"},
        ])
    session.commit()

# 2. Engine Wrapper with Access Control
AUTHORIZED_ROLES = {"doctor", "nurse"}

class DatabaseAccessWrapper:
    """Wrapper around database to enforce user-based access control."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def get_user_role(self):
        with Session(engine) as session:
            user_query = select(users.c.role).where(users.c.username == self.user_id)
            user_result = session.execute(user_query).fetchone()
            if user_result is None:
                return None
            return user_result[0]

    def get_patient_record(self, patient_id: int) -> dict:
        user_role = self.get_user_role()
        if user_role is None:
            return {"error": "Access denied: user not found"}
        if user_role not in AUTHORIZED_ROLES:
            return {"error": "Access denied: insufficient privileges"}
        
        with Session(engine) as session:
            patient_query = select(patients).where(patients.c.id == patient_id)
            patient_result = session.execute(patient_query).fetchone()

            if patient_result is None:
                return {"error": "Patient not found"}

            return {
                "id": patient_result.id,
                "name": patient_result.name,
                "provider_name": patient_result.provider_name,
                "condition": patient_result.condition,
            }

# 3. Define the tool for the agent
# Notice: now the wrapper instance must be created **before** using the tool.

def make_get_patient_record_tool(wrapper: DatabaseAccessWrapper):
    """Create a tool instance bound to a specific user wrapper."""
    return FunctionTool.from_defaults(
        fn=wrapper.get_patient_record,
        name="get_patient_record",
        description="Retrieve patient information if user is authorized. Input is patient_id (int).",
    )

# 4. Setup Ollama LLM and Agent
llm = Ollama(model="llama3")  # or whatever local model you use

def create_agent_for_user(user_id: str) -> FunctionCallingAgent:
    """Create an agent instance tied to a user session."""
    wrapper = DatabaseAccessWrapper(user_id)
    patient_record_tool = make_get_patient_record_tool(wrapper)

    agent = FunctionCallingAgent.from_tools(
        [patient_record_tool],
        llm=llm,
        system_prompt=f"You are a secure medical assistant. You are logged in as {user_id}.",
    )
    return agent

# 5. Example Usage
if __name__ == "__main__":
    agent_dr_smith = create_agent_for_user("dr_smith")
    agent_receptionist = create_agent_for_user("receptionist_amy")
    
    print(agent_dr_smith.chat("Get the patient record for patient ID 3."))  # Will succeed
    print(agent_receptionist.chat("Get the patient record for patient ID 3."))  # Will fail