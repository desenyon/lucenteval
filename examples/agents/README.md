# Example agents

`mock_agent.py` is the deterministic, zero-provider fixture used by the Docker smoke. It replies in the supported chat format, records synthetic zero token/cost usage, handles a recovery follow-up and exposes a local-only webhook receiver. It executes no tools and makes no outbound calls. Its scores are not evidence of model quality.

```bash
# From repository root, after installing api/requirements.txt
PYTHONPATH=api:. uvicorn examples.agents.mock_agent:app --port 8080
```

The default Docker demo runs this internally as `mock-agent:8080`. A host-run agent needs a corresponding **exact** hostname in the operator's `OUTBOUND_LOCAL_HOSTS` list to permit private HTTP. There is no unrestricted private-network bypass setting.

Other examples:

- `echo_agent.py`: basic refusal/echo illustration; token counts are rough word counts and its model name has no known cost rate.
- `tool_use_agent.py`: emits illustrative tool call payloads; the evaluator inspects calls but never executes them.
- `openai_proxy_agent.py`: optional provider-backed example that can incur charges and requires its own server-side provider credential. It is never used by tests or the smoke flow.

Register an account through `POST /v1/accounts` and keep its one-time `raw_key`. Submit evaluations through `/v1/runs` with `Authorization: Bearer lev_…`; the exact agent path is `/v1/chat/completions` for these examples. The evaluator sends only a JSON `messages` request plus configured headers. See the [agent protocol](../../README.md#3-implement-the-agent-protocol) and [credential boundaries](../../README.md#credentials-destinations-and-webhooks).
