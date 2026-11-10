# Inline subagent handoff — voice agent (gpt-realtime-2.1)

One Foundry voice agent split into three inline subagents that hand off in the same session:

`$entrypoint` (front desk) → `scheduling` (collects request, different voice) → `end` (summary + goodbye)

Based on [Use an inline subagent in a voice-based agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-inline-subagent-voice-agent).


## Files

| File | Purpose |
| --- | --- |
| `inline-voice-agent.yaml` | Voice agent definition with the three subagents and handoff conditions |
| `create_inline_voice_agent.py` | Creates a new agent version from the YAML and reads back `subagent_config` |
| `talk_to_inline_voice_agent.py` | Microphone/speaker client that prints the active subagent and handoff events |
| `requirements.txt` | Python dependencies |

## Run

Requires Python 3.11+, `az login`, the Foundry User role on the project, and a microphone and headphones.

Copy `.env.example` to `.env` and set your Foundry project endpoint before running.
Local `.env` files and Python virtual environments are excluded from Git.

```powershell
cd inline-subagent-voice-agent
python -m pip install -r requirements.txt
python create_inline_voice_agent.py
python talk_to_inline_voice_agent.py
```

Optional overrides: `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_VOICE_AGENT_NAME` (default `appointment-voice-agent`).

## Try it

| Say | Expected console output |
| --- | --- |
| "Hello. What can you help me with?" | `Active subagent: $entrypoint` |
| "I'd like to reschedule an appointment." | `Handoff requested: $entrypoint -> scheduling`, `Active subagent: scheduling`, `Handoff completed.` |
| "I'd prefer Tuesday." | Stays in `scheduling` |
| "Yes, that's correct. That's all, goodbye." | `Handoff requested: scheduling -> end`, `Active subagent: end` |

To test interruption recovery, add `delay_ms: 3000` to `entry_to_scheduling`, create a new version, and keep talking right after asking about an appointment.

Handoff conditions are model guidance, not authorization. Any real tool you add must enforce its own access checks.
