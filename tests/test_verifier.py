import copy

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TaskInput, TaskOutput
from plugin.operation import operate

SAMPLE = {
    "events": [
        {"event_id": "e4", "user": "u", "minute": 21},
        {"event_id": "e2", "user": "u", "minute": 10},
        {"event_id": "e1", "user": "u", "minute": 0},
        {"event_id": "e3", "user": "v", "minute": 10},
        {"event_id": "e0", "user": "u", "minute": 0},
    ],
    "gap": 10,
}
EXPECTED_ROWS = [
    {"user": "u", "start": 0, "end": 10, "event_ids": ["e0", "e1", "e2"]},
    {"user": "u", "start": 21, "end": 21, "event_ids": ["e4"]},
    {"user": "v", "start": 10, "end": 10, "event_ids": ["e3"]},
]
EXPECTED_TOTAL = 3
EMPTY = {"events": [], "gap": 1}
INVALID = {"gap": 0}
TOOL = "group_sessions"
TASK = "group-sessions"


def given(data):
    return build_output({"destination": "results/out.json", **data}, TaskInput)


def valid_input(data):
    return verifier.verify_input(TOOL, given(data))["valid"]


def execute(data, workspace):
    value = given(data)
    assert verifier.verify_input(TOOL, value)["valid"]
    output = build_output(plain_output(operate(value, workspace)), TaskOutput)
    assert verifier.verify_output(TOOL, value, output, str(workspace))["valid"]
    verdict = verifier.verify_task(TASK, value, output, None, str(workspace))
    assert verdict["valid"] and verdict["score"] == 1.0
    assert verdict == verifier.verify_task(TASK, value, output, None, str(workspace))
    return output


def test_known_answer(tmp_path):
    out = execute(SAMPLE, tmp_path)
    assert plain_output(out)["records"] == EXPECTED_ROWS
    assert out.total == EXPECTED_TOTAL


def test_empty_boundary(tmp_path):
    out = execute(EMPTY, tmp_path)
    assert out.records == [] and out.total == 0


def test_wrong_total_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.total += 1
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_omitted_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.pop()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_duplicate_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.append(out.records[0])
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_order_is_canonical(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.reverse()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_missing_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).unlink()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "text", ["{", "null", "{}", '{"records":[],"total":NaN}', '{"records":[],"total":0,"total":1}']
)
def test_malformed_or_incorrect_file_rejected(tmp_path, text):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_text(text)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_invalid_utf8_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_bytes(b"\xff")
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_claimed_path_mismatch_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.path = "different.json"
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "destination", ["../escape.json", "/absolute.json", "result.txt", "", "a/../b.json", "./x.json", "a\\b.json"]
)
def test_destination_rejected(destination):
    assert not valid_input({**SAMPLE, "destination": destination})


def test_invalid_input_and_tool_failure(tmp_path):
    data = {**SAMPLE, **INVALID}
    assert not valid_input(data)
    with pytest.raises(ValueError):
        operate(given(data), tmp_path)


def test_schema_rejects_missing_or_malformed():
    with pytest.raises((ValueError, TypeError)):
        build_output({}, TaskInput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": "wrong", "total": "wrong"}, TaskOutput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": [], "total": 0, "extra": 1}, TaskOutput)


def test_existing_file_is_never_overwritten(tmp_path):
    out = execute(SAMPLE, tmp_path)
    content = (tmp_path / out.path).read_bytes()
    with pytest.raises(FileExistsError):
        operate(given(SAMPLE), tmp_path)
    assert (tmp_path / out.path).read_bytes() == content


def test_symlink_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    path = tmp_path / out.path
    target = tmp_path / "target.json"
    path.rename(target)
    path.symlink_to(target)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_symlink_directory_rejected(tmp_path):
    (tmp_path / "actual").mkdir()
    (tmp_path / "results").symlink_to(tmp_path / "actual", target_is_directory=True)
    with pytest.raises(ValueError):
        operate(given(SAMPLE), tmp_path)


def test_input_permutation_does_not_change_result(tmp_path):
    data = copy.deepcopy(SAMPLE)
    for value in data.values():
        if isinstance(value, list):
            value.reverse()
    assert plain_output(execute(data, tmp_path))["records"] == EXPECTED_ROWS


def test_edited_row_even_with_matching_file_is_rejected(tmp_path):
    import json

    out = execute(SAMPLE, tmp_path)
    data = plain_output(out)
    row = data["records"][0]
    key = next(k for k, v in row.items() if type(v) is int)
    row[key] += 1
    forged = build_output(data, TaskOutput)
    artifact = {"records": data["records"], "total": data["total"]}
    (tmp_path / out.path).write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n")
    assert not verifier.verify_task(TASK, given(SAMPLE), forged, None, str(tmp_path))["valid"]


def test_equal_gap_joins_but_gap_plus_one_splits(tmp_path):
    data = {
        "events": [
            {"event_id": "a", "user": "u", "minute": 0},
            {"event_id": "b", "user": "u", "minute": 10},
            {"event_id": "c", "user": "u", "minute": 21},
        ],
        "gap": 10,
    }
    assert execute(data, tmp_path).total == 2


def test_session_can_span_more_than_gap(tmp_path):
    data = {"events": [{"event_id": str(i), "user": "u", "minute": i * 10} for i in range(10)], "gap": 10}
    out = execute(data, tmp_path)
    assert out.total == 1 and out.records[0].end == 90


def test_duplicate_event_rejected():
    assert not valid_input({**SAMPLE, "events": [SAMPLE["events"][0]] * 2})


def test_user_isolation(tmp_path):
    data = {
        "events": [{"event_id": "a", "user": "u", "minute": 0}, {"event_id": "b", "user": "v", "minute": 0}],
        "gap": 1440,
    }
    assert execute(data, tmp_path).total == 2


def test_crlf_is_not_canonical_bytes(tmp_path):
    out = execute(SAMPLE, tmp_path)
    artifact = tmp_path / out.path
    artifact.write_bytes(artifact.read_bytes().replace(b"\n", b"\r\n"))
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]
