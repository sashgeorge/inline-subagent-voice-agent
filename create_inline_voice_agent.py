"""Create a version of a voice agent with inline subagents from inline-voice-agent.yaml."""

import json
import os
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# read from .env 
from dotenv import load_dotenv
load_dotenv()   

# DEFAULT_ENDPOINT = "https://vz-justin-demo-foundry.services.ai.azure.com/api/projects/proj-default"
# DEFAULT_AGENT_NAME = "appointment-voice-agent"

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
agent_name = os.environ.get("FOUNDRY_VOICE_AGENT_NAME")
subagent_config_file = os.environ.get("SUBAGENT_CONFIG_FILE")

config_path = Path(__file__).with_name(subagent_config_file)

with config_path.open(encoding="utf-8") as source:
    definition = yaml.safe_load(source)

if not isinstance(definition, dict) or definition.get("kind") != "voice":
    raise ValueError("The YAML file must contain a voice agent definition.")

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(
        endpoint=endpoint,
        credential=credential,
        allow_preview=True,
    ) as project_client,
):
    created = project_client.agents.create_version(
        agent_name=agent_name,
        body={
            "definition": definition,
            "description": "Appointment intake with inline subagents",
        },
    )
    readback = project_client.agents.get_version(
        agent_name=agent_name,
        agent_version=created.version,
    )
    saved_config = readback.as_dict()["definition"].get("subagent_config")
    if saved_config is None or saved_config.get("subagent_type") != "inline":
        raise RuntimeError("The saved version didn't preserve inline mode.")

    print(f"Created '{created.name}', version {created.version} on {definition['model']}")
    print(json.dumps(saved_config, indent=2))
