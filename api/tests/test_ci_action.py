"""Run the real composite-action shell against command fixtures, with no network."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("score,passes", [(0.8, True), (0.2, False), (0.0, False), (None, False)])
def test_action_quotes_credentials_exports_outputs_and_enforces_threshold(tmp_path, score, passes):
    root = Path(__file__).resolve().parents[2]
    action = yaml.safe_load((root / ".github/actions/run-eval/action.yml").read_text())
    script = action["runs"]["steps"][0]["run"]
    binary = tmp_path / "bin"
    binary.mkdir()
    curl = binary / "curl"
    curl.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
if "-d" in args:
    body = json.loads(args[args.index("-d") + 1])
    pathlib.Path(os.environ["BODY_FILE"]).write_text(json.dumps(body))
    print(json.dumps({"id": "11111111-1111-4111-8111-111111111111"}))
else:
    print(json.dumps({"status": "completed", "completed_count": 1, "prompt_count": 1,
                      "composite_score": json.loads(os.environ["FAKE_SCORE"]),
                      "score_adversarial": 1, "score_hallucination": 0.5, "score_latency": 1}))
''')
    curl.chmod(0o755)
    sleep = binary / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    output = tmp_path / "outputs"
    body_file = tmp_path / "body"
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "LUCENT_API_KEY": "lev_test_only",
           "ENDPOINT_URL": "https://agent.example/run", "AUTH_HEADER": 'Bearer test-"quoted"-value',
           "SYSTEM_PROMPT": 'Keep "quoted" text intact', "MIN_SCORE": "0.7", "CORPUS_VERSION": "v1",
           "API_URL": "http://api.example", "TIMEOUT_MINUTES": "1", "GITHUB_RUN_ID": "123",
           "GITHUB_RUN_ATTEMPT": "1", "GITHUB_JOB": "test", "GITHUB_OUTPUT": str(output),
           "BODY_FILE": str(body_file), "FAKE_SCORE": json.dumps(score)}
    process = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=10)
    assert (process.returncode == 0) == passes, process.stdout + process.stderr
    assert json.loads(body_file.read_text())["headers"]["Authorization"] == env["AUTH_HEADER"]
    assert env["AUTH_HEADER"] not in process.stdout
    assert "run_id=11111111-1111-4111-8111-111111111111" in output.read_text()
    for name, spec in action["outputs"].items():
        assert spec["value"] == "${{ steps.run_eval.outputs." + name + " }}"
