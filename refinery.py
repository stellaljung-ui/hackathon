import asyncio
import os

from air import AsyncAIRefinery, DistillerClient
from dotenv import load_dotenv

# Load the API Key
load_dotenv() # loads your API_KEY from your local '.env' file
api_key=str(os.getenv("API_KEY"))

async def simple_agent(query: str):
    """
    A simple custom agent that generates synthetic data
    using Chat Completions API
    """


    prompt = f"""Your task is to generate some synthetic data so that it will be useful to answer the user question. Do not mention this is synthetic data in your answer.\n\n{query}"""
    client = AsyncAIRefinery(api_key=api_key)


    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="meta-llama/Llama-3.1-70B-Instruct",
    )

    return response.choices[0].message.content

async def quickstart_demo():
    distiller_client = DistillerClient(api_key=api_key)

    # Validate your configuration file before creating the project
    is_config_valid = distiller_client.validate_config(config_path="refinery.yaml")

    if not is_config_valid:
        # Abort if validation fails to avoid creating an invalid project
        print("Configuration validation failed!")
        return

    # upload your config file to register a new distiller project
    distiller_client.create_project(config_path="refinery.yaml", project="demo") 

    # Define a mapping between your custom agent to Callable.
    # When the custom agent is summoned by the super agent / orchestrator,
    # distiller-sdk will run the custom agent and send its response back to the
    # multi-agent system.
    executor_dict = {
        "Data Scientist Agent": simple_agent,
    }

    # connect to the created project
    async with distiller_client(
        project="demo",
        uuid="test_user",
        executor_dict=executor_dict
    ) as dc:
        responses = await dc.query(query="Who won the FIFA world cup 2022?") # send a query to project
        async for response in responses:
            print(response['content']) 

if __name__ == "__main__":
     asyncio.run(quickstart_demo())