from dataclasses import asdict

from .checks import destination_problem, encoded, identifier, result, safe_path


def input_problem(v):
    problem = destination_problem(v.destination)
    if problem:
        return problem
    if len(v.events) > 200 or not 1 <= v.gap <= 1440:
        return "event count or inactivity gap is out of bounds"
    if len({r.event_id for r in v.events}) != len(v.events):
        return "event identifiers must be globally unique"
    if any(not identifier(r.event_id) or not identifier(r.user) or not 0 <= r.minute <= 1000000000 for r in v.events):
        return "invalid event identifier, user, or minute"
    return None


def verify_input(value):
    problem = input_problem(value)
    return result(not problem, problem or "input is valid")


def expected(v):
    unseen = set(range(len(v.events)))
    components = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        component = [seed]
        frontier = [seed]
        while frontier:
            current = v.events[frontier.pop()]
            linked = [
                i
                for i in sorted(unseen)
                if v.events[i].user == current.user and abs(v.events[i].minute - current.minute) <= v.gap
            ]
            for i in linked:
                unseen.remove(i)
                component.append(i)
                frontier.append(i)
        events = sorted((v.events[i] for i in component), key=lambda r: (r.minute, r.event_id))
        components.append(
            {
                "user": events[0].user,
                "start": events[0].minute,
                "end": events[-1].minute,
                "event_ids": [r.event_id for r in events],
            }
        )
    rows = sorted(components, key=lambda r: (r["user"], r["start"], r["event_ids"][0]))
    return rows, len(rows)


def verify_output(input_value, output_value, workspace):
    problem = input_problem(input_value)
    if problem:
        return result(False, problem)
    rows, total = expected(input_value)
    actual = [asdict(r) for r in output_value.records]
    if actual != rows or output_value.total != total:
        return result(False, "returned rows or total do not match the task rules")
    if output_value.path != input_value.destination:
        return result(False, "returned path does not match destination")
    path = safe_path(workspace, input_value.destination)
    if path is None or not path.is_file():
        return result(False, "artifact is missing, is a symlink, or escapes the workspace")
    try:
        content = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return result(False, "artifact cannot be read as UTF-8")
    if content != encoded(rows, total):
        return result(False, "artifact is not the exact canonical JSON result")
    return result(True, "verified rows, total, destination, and artifact bytes", rows=len(rows), total=total)


def verify_task(arguments, output, reference, workspace):
    return verify_output(arguments, output, workspace)
