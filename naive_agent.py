from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select
from sqlalchemy.orm import Session
from llama_index.llms.ollama import Ollama
from llama_index.agent import FunctionCallingAgent
from llama_index.tools import FunctionTool

# 1. Setup SQLite Database
engine = create_engine("sqlite:///patients.db", echo=False)
metadata = MetaData()

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

# 2. Pre-populate database (only if empty)
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

# 3. Access Control Tool
AUTHORIZED_ROLES = {"doctor", "nurse"}

def get_patient_record(logged_in_user: str, patient_id: int) -> dict:
    """Tool to get a patient record if user has access."""
    with Session(engine) as session:
        user_query = select(users.c.role).where(users.c.username == logged_in_user)
        user_result = session.execute(user_query).fetchone()

        if user_result is None:
            return {"error": "Access denied: user not found"}

        user_role = user_result[0]
        
        if user_role not in AUTHORIZED_ROLES:
            return {"error": "Access denied: insufficient privileges"}

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

# 4. Register tool for agent
get_patient_record_tool = FunctionTool.from_defaults(
    fn=get_patient_record,
    name="get_patient_record",
    description="Retrieve patient information if user is authorized. Inputs are logged_in_user (str) and patient_id (int).",
)

# 5. Setup Ollama LLM and Agent
llm = Ollama(model="llama3")  # Replace "llama3" with your local model if needed
agent = FunctionCallingAgent.from_tools(
    [get_patient_record_tool],
    llm=llm,
    system_prompt="You are a secure medical assistant. Always check if the user has permissions before accessing patient data."
)

# 6. Agent example calls
if __name__ == "__main__":
    # Simulated query
    response = agent.chat("Get me the patient record for patient ID 1. I am logged in as dr_smith.")
    print(response)

    response = agent.chat("Get me the patient record for patient ID 2. I am logged in as receptionist_amy.")
    print(response)