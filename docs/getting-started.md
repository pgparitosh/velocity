# Getting Started with Velocity

Velocity is a production-grade AI Agent Platform that enables teams to build, deploy, and scale AI agents in days.

## 1. Installation

Install the platform via PyPI:

```bash
pip install velocity-platform
```

## 2. Scaffold Your First Agent

Use the CLI to create a new agent:

```bash
velocity init my-agent
```

This creates a directory structure with all necessary files.

## 3. Implement Domain Logic

Open `my-agent/agent.py` and implement the 3 core methods of `AgentBase`:

- `system_prompt()`: The instructions for the LLM.
- `tools()`: The list of tools available to the agent.
- `execute_tool()`: How to call those tools.

## 4. Run Locally

Start your agent in development mode:

```bash
velocity run my-agent
```

## 5. Evaluate Performance

Run the evaluation suite to ensure accuracy:

```bash
velocity test my-agent
```

## 6. Deploy to Production

Once ready, deploy to the Velocity platform:

```bash
velocity deploy my-agent
```

For more details, see the [Architecture Guide](architecture.md).
