"""
Velocity Command Line Interface.
Provides rapid orchestration commands bridging developer laptops to the cluster deployments.
Commands:
  velocity init [name]    - Scaffold a new agent 
  velocity run [name]     - Run agent logic locally
  velocity test [name]    - Run evals framework
"""

import argparse
import os
import sys


def init_agent(args: argparse.Namespace) -> None:
    """Scaffolds a new agent directory with standard configs and code separation."""
    agent_name = args.name
    if os.path.exists(agent_name):
        print(f"Directory {agent_name} already exists.")
        sys.exit(1)
        
    os.makedirs(f"{agent_name}/prompts", exist_ok=True)
    
    # 1. Boilerplate config
    with open(f"{agent_name}/agent_config.yaml", "w") as f:
        f.write(f"name: {agent_name}\nversion: 1.0.0\nenvironment: dev\n")
        
    # 2. Boilerplate Agent Logic
    with open(f"{agent_name}/agent.py", "w") as f:
        f.write(f"""from velocity.sdk import AgentBase, AgentContext
from typing import List, Dict, Any

class {agent_name.capitalize()}Agent(AgentBase):
    AGENT_ID = "{agent_name}"
    
    def system_prompt(self) -> str:
        return "You are a helpful '{agent_name}' agent."
        
    def tools(self) -> List[Dict[str, Any]]:
        # Import your @tool decorated functions from tools.py and append their schemas here
        return []

    async def execute_tool(self, name: str, inputs: Dict[str, Any], ctx: AgentContext) -> str:
        # Route to your concrete implementation from tools.py
        raise NotImplementedError()
""")

    # 3. Boilerplate Tools
    with open(f"{agent_name}/tools.py", "w") as f:
         f.write("""from velocity.sdk import tool

@tool(name="hello", description="Says hello.")
async def say_hello(name: str) -> str:
    return f"Hello, {name}!"
""")
         
    print(f"Successfully initialized '{agent_name}'.")


def run_agent(args: argparse.Namespace) -> None:
    """Mock runner for CLI invocation."""
    print(f"Running agent {args.name} against simulated platform environment...")
    print("Agent output: [Not implemented natively in local CLI without config injection.]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Velocity AI Agent Platform CLI")
    subparsers = parser.add_subparsers(dest="command")

    init_p = subparsers.add_parser("init", help="Initialize a new agent project.")
    init_p.add_argument("name", help="Name of the agent module.")

    run_p = subparsers.add_parser("run", help="Run an agent locally.")
    run_p.add_argument("name", help="Name of the agent module to run.")

    args = parser.parse_args()

    if args.command == "init":
        init_agent(args)
    elif args.command == "run":
        run_agent(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
