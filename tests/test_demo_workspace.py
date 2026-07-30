"""Tests for the Demo Workspace split & reset mechanism.

Verifies the three-way separation:
- demo_seed_units.json     (read-only standard examples)
- demo_runtime_units.json  (live demo workspace, rebuilt from seed)
- acceptance_test_units.json (reserved scratch space)

And the "Reset demo workspace" behaviour:
- rebuilds runtime from seed with pristine usage counters
- never touches the real activation_units.json
- never writes to the seed file
"""

from __future__ import annotations

import json

import pytest

import src.demo_workspace as dw


@pytest.fixture
def demo_env(tmp_path, monkeypatch):
    """Redirect all demo workspace paths to a temp dir and seed a clean state."""
    import src.activation_unit as au_mod

    seed = tmp_path / "demo_seed_units.json"
    runtime = tmp_path / "demo_runtime_units.json"
    acceptance = tmp_path / "acceptance_test_units.json"
    real = tmp_path / "activation_units.json"

    monkeypatch.setattr(dw, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dw, "DEMO_SEED_FILE", seed)
    monkeypatch.setattr(dw, "DEMO_RUNTIME_FILE", runtime)
    monkeypatch.setattr(dw, "ACCEPTANCE_TEST_FILE", acceptance)
    monkeypatch.setattr(dw, "REAL_AU_FILE", real)
    monkeypatch.setattr(dw, "DEMO_AU_FILE", runtime)
    # Keep the storage module's file in sync with the demo runtime file.
    monkeypatch.setattr(au_mod, "AU_FILE", runtime)
    monkeypatch.setattr(au_mod, "DATA_DIR", tmp_path)

    # Real user data — must remain untouched throughout.
    real.write_text(json.dumps([{"id": "real-1", "name": "Real User Unit"}]), encoding="utf-8")

    return {
        "seed": seed,
        "runtime": runtime,
        "acceptance": acceptance,
        "real": real,
        "au_mod": au_mod,
    }


def _make_seed_unit(uid: str, name: str) -> dict:
    return {
        "id": uid,
        "name": name,
        "status": "active",
        "usage": {
            "activation_count": 0,
            "useful_count": 0,
            "not_useful_count": 0,
            "false_trigger_count": 0,
            "missing_context_count": 0,
            "expression_issue_count": 0,
            "last_used_at": "",
        },
        "_activation_log": [],
        "_feedback_log": [],
    }


def _write_seed(path, units):
    path.write_text(json.dumps(units, ensure_ascii=False), encoding="utf-8")


class TestDemoWorkspaceSplit:
    def test_seed_creates_runtime_with_pristine_counters(self, demo_env):
        seed_units = [_make_seed_unit("u1", "Example A"), _make_seed_unit("u2", "Example B")]
        _write_seed(demo_env["seed"], seed_units)

        n = dw.seed_demo_workspace()
        assert n == 2

        runtime = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        assert len(runtime) == 2
        for u in runtime:
            assert u["usage"]["activation_count"] == 0
            assert u["_feedback_log"] == []
            assert u["_activation_log"] == []

    def test_reset_clears_runtime_feedback_and_drafts(self, demo_env):
        """Reset rebuilds runtime from seed, discarding drafts + feedback."""
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)
        dw.seed_demo_workspace()

        # Simulate demo interaction: pollute the runtime with a draft + feedback.
        runtime = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        runtime[0]["usage"]["activation_count"] = 5
        runtime[0]["_feedback_log"].append({"type": "useful"})
        runtime.append({"id": "draft-1", "name": "Test Draft", "status": "draft"})
        demo_env["runtime"].write_text(json.dumps(runtime), encoding="utf-8")

        # Reset → back to the clean seed state.
        n = dw.seed_demo_workspace()
        assert n == 1
        rebuilt = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        assert len(rebuilt) == 1
        assert rebuilt[0]["usage"]["activation_count"] == 0
        assert rebuilt[0]["_feedback_log"] == []
        assert all(u["id"] != "draft-1" for u in rebuilt)

    def test_reset_never_touches_real_data(self, demo_env):
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)

        before = demo_env["real"].read_text(encoding="utf-8")
        dw.seed_demo_workspace()
        after = demo_env["real"].read_text(encoding="utf-8")

        assert before == after
        assert json.loads(after)[0]["id"] == "real-1"

    def test_seed_file_is_not_modified_by_reset(self, demo_env):
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)
        seed_before = demo_env["seed"].read_text(encoding="utf-8")

        dw.seed_demo_workspace()
        # Mutate runtime, then reset again — seed must stay identical.
        runtime = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        runtime[0]["usage"]["activation_count"] = 9
        demo_env["runtime"].write_text(json.dumps(runtime), encoding="utf-8")
        dw.seed_demo_workspace()

        assert demo_env["seed"].read_text(encoding="utf-8") == seed_before

    def test_apply_demo_mode_points_storage_at_runtime(self, demo_env):
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)

        dw.apply_demo_mode(True)
        assert demo_env["au_mod"].AU_FILE == demo_env["runtime"]
        assert demo_env["runtime"].exists()  # auto-seeded on first use

        dw.apply_demo_mode(False)
        assert demo_env["au_mod"].AU_FILE == demo_env["real"]

    def test_ensure_demo_runtime_seeds_when_missing(self, demo_env):
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)
        assert not demo_env["runtime"].exists()

        dw.ensure_demo_runtime()
        assert demo_env["runtime"].exists()
        runtime = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        assert len(runtime) == 1

    def test_backup_runtime_preserves_evidence(self, demo_env, tmp_path):
        seed_units = [_make_seed_unit("u1", "Example A")]
        _write_seed(demo_env["seed"], seed_units)
        dw.seed_demo_workspace()

        # Pollute runtime, then back it up as evidence before reset.
        runtime = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        runtime[0]["_feedback_log"].append({"type": "useful"})
        demo_env["runtime"].write_text(json.dumps(runtime), encoding="utf-8")

        backup_path = tmp_path / "evidence" / "backup.json"
        dw.backup_runtime(backup_path)
        assert backup_path.exists()
        backed = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backed[0]["_feedback_log"][0]["type"] == "useful"

        # Reset wipes runtime but the backup keeps the evidence.
        dw.seed_demo_workspace()
        rebuilt = json.loads(demo_env["runtime"].read_text(encoding="utf-8"))
        assert rebuilt[0]["_feedback_log"] == []
        assert json.loads(backup_path.read_text(encoding="utf-8"))[0]["_feedback_log"][0]["type"] == "useful"

    def test_seed_missing_raises(self, demo_env):
        with pytest.raises(FileNotFoundError):
            dw.seed_demo_workspace()
