import asyncio
import os
from dotenv import load_dotenv
from air import DistillerClient
 
# Load API key from .env
load_dotenv()
api_key = str(os.getenv("API_KEY"))
 
# Define custom agents
async def search_agent(query: str) -> str:
    # For now, just return a placeholder response
    return f"SearchAgent processed query: {query}"
 
 
# Map agents to executor_dict
executor_dict = {
    "SearchAgent": search_agent
}
 
# Create DistillerClient
client = DistillerClient(api_key=api_key)
 
async def run_query():
    # Validate and create project
    is_valid = client.validate_config(config_path="example.yaml")
    if is_valid:
        client.create_project(config_path="example.yaml", project="hackathon_project")
    if not is_valid:
        print("Config validation failed. Please check your YAML file.")
        return
 
    # Interact with orchestrator
    async with client(project="hackathon_project", uuid="user_123", executor_dict=executor_dict) as dc:
        responses = await dc.query(query="search for latest sustainability news")
        async for response in responses:
            print(response['content'])
 
# Run the async loop
asyncio.run(run_query())