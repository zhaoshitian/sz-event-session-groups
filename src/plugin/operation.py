from slimconfig import build_output

from contract import TaskOutput
from verifier.checks import encoded, safe_path
from verifier.operation import verify_input


def solve(v):
    rows = []
    for event in sorted(v.events, key=lambda r: (r.user, r.minute, r.event_id)):
        if not rows or rows[-1]["user"] != event.user or event.minute - rows[-1]["end"] > v.gap:
            rows.append({"user": event.user, "start": event.minute, "end": event.minute, "event_ids": [event.event_id]})
        else:
            rows[-1]["end"] = event.minute
            rows[-1]["event_ids"].append(event.event_id)
    return rows, len(rows)


def operate(value, workspace):
    verdict = verify_input(value)
    if not verdict["valid"]:
        raise ValueError(verdict["message"])
    path = safe_path(workspace, value.destination)
    if path is None:
        raise ValueError("destination crosses a symlink or leaves the workspace")
    rows, total = solve(value)
    output = build_output({"path": value.destination, "records": rows, "total": total}, TaskOutput)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded(rows, total))
    return output
