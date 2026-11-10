"""Talk to the inline-subagent voice agent and print each handoff."""

import asyncio
import os
from contextlib import closing

import pyaudio
from azure.ai.projects import models
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.aio.operations import AsyncBetaRealtimeConnection
from azure.identity.aio import DefaultAzureCredential

# read from .env 
from dotenv import load_dotenv
load_dotenv()   

# DEFAULT_ENDPOINT = "https://vz-justin-demo-foundry.services.ai.azure.com/api/projects/proj-default"
# DEFAULT_AGENT_NAME = "appointment-voice-agent"

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
agent_name = os.environ.get("FOUNDRY_VOICE_AGENT_NAME")


RATE = 24000
CHUNK = 2400


def observe_handoff(event) -> None:
    event_type = event["type"]
    if event_type == "session.updated":
        state = event["session"].get("handoff")
        if state is None:
            raise RuntimeError(
                "The session has no handoff state. Check the saved agent "
                "configuration and the client library version."
            )
        print(f"Active subagent: {state['active_node_id']}")
    elif event_type == "session.handoff.started":
        print(f"Handoff requested: {event['from_node_id']} -> {event['to_node_id']}")
    elif event_type == "session.handoff.completed":
        print("Handoff completed.")
    elif event_type == "session.handoff.aborted":
        if event["reason"] == "user_interruption":
            print("Handoff cancelled by caller; source remains active.")
        else:
            raise RuntimeError(
                f"Handoff aborted: {event['reason']}; detail={event.get('error')}"
            )


async def wait_until_ready(connection: AsyncBetaRealtimeConnection) -> None:
    while True:
        event = await connection.recv()
        if event["type"] == "error":
            raise RuntimeError(event["error"]["message"])
        if event["type"] == "session.updated":
            observe_handoff(event)
            return


async def send_microphone(
    connection: AsyncBetaRealtimeConnection, stream: pyaudio.Stream
) -> None:
    while True:
        audio = await asyncio.to_thread(
            stream.read, CHUNK, exception_on_overflow=False
        )
        await connection.input_audio_buffer.append(audio=audio)


async def receive_audio(
    connection: AsyncBetaRealtimeConnection, stream: pyaudio.Stream
) -> None:
    async for event in connection:
        observe_handoff(event)
        if isinstance(event, models.RealtimeServerEventResponseAudioDelta):
            await asyncio.to_thread(stream.write, event.delta)
        elif isinstance(event, models.RealtimeServerEventResponseAudioTranscriptDone):
            print(f"Agent: {event.transcript}")
        elif event["type"] == "error":
            raise RuntimeError(event["error"]["message"])
    raise ConnectionError("The voice session closed. Restart to reconnect.")


async def talk() -> None:
    audio = pyaudio.PyAudio()
    try:
        with (
            closing(audio.open(
                format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK,
            )) as microphone,
            closing(audio.open(
                format=pyaudio.paInt16, channels=1, rate=RATE,
                output=True, frames_per_buffer=CHUNK,
            )) as speaker,
        ):
            async with (
                DefaultAzureCredential() as credential,
                AIProjectClient(
                    endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT"),
                    credential=credential,
                    allow_preview=True,
                ) as project_client,
                project_client.beta.voice_agents.realtime.connect(
                    agent_name=os.environ.get("FOUNDRY_VOICE_AGENT_NAME"),
                ) as connection,
            ):
                await asyncio.wait_for(wait_until_ready(connection), timeout=30)
                print("Connected. Ask about an appointment. Ctrl+C exits.")
                async with asyncio.TaskGroup() as tasks:
                    tasks.create_task(send_microphone(connection, microphone))
                    tasks.create_task(receive_audio(connection, speaker))
    finally:
        audio.terminate()


if __name__ == "__main__":
    try:
        asyncio.run(talk())
    except KeyboardInterrupt:
        print("\nDisconnected.")
