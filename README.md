# Event Session Groups

Partition an unordered multi-user event stream into deterministic inactivity-gap sessions.

## Tools

- `group_sessions` accepts `TaskInput` and returns `TaskOutput`.
- `group-sessions` is a `runner: tool` task using `group_sessions`. It requires no model or external service. A RUSH Lab agent can select the task from its structured interface.

### Exact success conditions

Within each user, order events by (minute,event_id). Adjacent events join when their gap <= gap; a larger gap splits. Session end is the last event time. Sort sessions by user then start. total counts sessions.

The tool creates a new file at `destination`. The exact file format is UTF-8 JSON of `{"records": [...], "total": integer}`, sorted object keys, compact separators `(',', ':')`, ASCII escapes, and one final newline. Returned records, total, and destination must match the file and the independently computed answer. A matching claim without a matching file fails. Existing files are never overwritten. Paths must be canonical relative `.json` paths, at most 200 characters, with identifier-style directories and filename stems; symlinks are rejected. Identifiers match `[A-Za-z0-9][A-Za-z0-9_-]{0,31}`. Input sizes and numeric bounds are declared in `contract.py` and enforced in `verifier/operation.py`.

The tool scans sorted events. The verifier finds connected components in a same-user graph whose edges join events at most gap minutes apart.

### Example input

```json
{
  "destination": "results/out.json",
  "events": [
    {
      "event_id": "e4",
      "user": "u",
      "minute": 21
    },
    {
      "event_id": "e2",
      "user": "u",
      "minute": 10
    },
    {
      "event_id": "e1",
      "user": "u",
      "minute": 0
    },
    {
      "event_id": "e3",
      "user": "v",
      "minute": 10
    },
    {
      "event_id": "e0",
      "user": "u",
      "minute": 0
    }
  ],
  "gap": 10
}
```

## Layout

- `contract.py`: typed schemas and tool/task tables.
- `nanoagent.yaml`: tool runner, no network hosts, workspace-only writes.
- `src/plugin/`: MCP runtime and deterministic implementation.
- `verifier/`: independent deterministic checks; no LLM, clock, network, randomness, or writes.
- `tests/test_verifier.py`: known answers, adversarial outputs, boundaries, malformed inputs, artifact changes, and safe paths.
- `ui/` and `product/`: result schema rendering and marketplace presentation.
- `uv.lock`: pinned dependency versions and Git revision of slimconfig.

## Develop and run

Requires Python 3.12 or later, Git, uv, and NanoAgent implementing `nanoagent.plugin/v0001` (tested with the RUSH Lab bundled CLI). First-time dependency installation requires the package index and GitHub; execution requires no network or environment secrets.

```sh
uv sync --frozen --extra dev
uv run --frozen pytest -q
uv run --frozen ruff check .
uv lock --check
rushlab nanoagent plugin inspect .
```

To run: save the example as `/absolute/path/input.json`, then create a YAML file outside the repository:

```yaml
_ > nanoagent.cli.plugin.PluginRunConfig:
plugin: /absolute/path/sz-event-session-groups
task: group-sessions
arguments: /absolute/path/input.json
inputs: []
timeout: 60.0
```

Run `rushlab nanoagent plugin run config=/absolute/path/run.yaml home=/absolute/path/new-run-folder`.
The new run folder contains `workspace/results/out.json`, `result.json`, and `verdict.json`. A successful verifier returns `valid: true` and `score: 1.0`. Use a fresh run folder and destination for each run. Evidence and validation logs belong in the milestone report, outside this repository.

Limitations: Batch input with at most 200 events; no late-event streaming updates, identity merging, time zones, or real tracking service.
