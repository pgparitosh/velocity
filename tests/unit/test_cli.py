import argparse
import os

import pytest

from velocity.cli import init_agent


def test_cli_init_agent(tmp_path):
    # Change to tmp_path to avoid creating files in the repo
    os.chdir(tmp_path)
    
    args = argparse.Namespace(name="my-test-agent")
    init_agent(args)
    
    assert os.path.exists("my-test-agent")
    assert os.path.exists("my-test-agent/agent.py")
    assert os.path.exists("my-test-agent/tools.py")
    assert os.path.exists("my-test-agent/agent_config.yaml")

def test_cli_init_agent_exists(tmp_path):
    os.chdir(tmp_path)
    os.makedirs("existing-agent")
    
    args = argparse.Namespace(name="existing-agent")
    # init_agent calls sys.exit(1) if exists
    with pytest.raises(SystemExit) as cm:
        init_agent(args)
    assert cm.value.code == 1
