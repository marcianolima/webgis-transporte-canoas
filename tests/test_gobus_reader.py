"""Rede sintética isolada: retomada, limites e preservação após falhas."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
import urllib.error
import pytest
from transporte.gobus_reader import BASE, Reader
from transporte.persistence import atomic_bytes


class Response:
    status = 200

    def __init__(self, body=b'retornoJSON({"sucesso":true,"cidade":[]});'):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.body[:limit]


class Opener:
    def __init__(self, *results):
        self.results = iter(results)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def reader(tmp_path, opener, **options):
    return Reader(
        tmp_path / "reference-cache", opener=opener, sleep=lambda _: None, **options
    )


def stale_cache(tmp_path):
    url = BASE + "V3/cidadesLinhas/MPA/retornoJSONCidadesLinhas"
    path = (
        tmp_path
        / "reference-cache"
        / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    old = {
        "url": url,
        "sha256": "a" * 64,
        "kind": "cidades_linhas",
        "params": {"cidade": "MPA"},
        "fetched_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "body": 'retornoJSON({"sucesso":true,"cidade":[{"cod":"4"}]});',
    }
    path.write_text(json.dumps(old))
    return path, path.read_bytes()


def test_timeout_retry_progress_and_resume_from_cache(tmp_path):
    opener = Opener(TimeoutError("SYNTHETIC timeout"), Response())
    first = reader(tmp_path, opener, timeout=60, max_requests=3)
    document, _ = first.get("cidades_linhas", cidade="MPA")
    assert document["sucesso"] is True
    assert [timeout for _, timeout in opener.calls] == [60, 60]
    progress = first.finish("completed")
    assert progress["http_requests"] == 2 and progress["retry_attempts"] == 1
    assert json.loads(first.progress_path.read_text())["status"] == "completed"
    second = reader(tmp_path, Opener())
    assert second.get("cidades_linhas", cidade="MPA")[0] == document
    assert second.count == 0 and second.cache_hits == 1
    assert len(list((tmp_path / "source-history").glob("*.json"))) == 1


@pytest.mark.parametrize(
    "error", [TimeoutError("SYNTHETIC"), ValueError("SYNTHETIC schema")]
)
def test_failed_refresh_never_overwrites_old_capture(tmp_path, error):
    path, before = stale_cache(tmp_path)
    current = reader(tmp_path, Opener(error, error, error))
    with pytest.raises(type(error)):
        current.get("cidades_linhas", cidade="MPA")
    assert path.read_bytes() == before
    assert len(list((tmp_path / "source-history").glob("*.json"))) == 1
    assert current.count == (3 if isinstance(error, TimeoutError) else 1)


def test_retries_consume_total_request_budget(tmp_path):
    opener = Opener(TimeoutError("SYNTHETIC"), Response())
    current = reader(tmp_path, opener, max_requests=1)
    with pytest.raises(ValueError, match="Orçamento"):
        current.get("cidades_linhas", cidade="MPA")
    assert len(opener.calls) == current.count == 1


def test_403_stops_network_and_does_not_retry(tmp_path):
    error = urllib.error.HTTPError(BASE, 403, "SYNTHETIC forbidden", {}, None)
    opener = Opener(error, Response())
    current = reader(tmp_path, opener)
    with pytest.raises(urllib.error.HTTPError):
        current.get("cidades_linhas", cidade="MPA")
    with pytest.raises(ValueError, match="suspensa"):
        current.get("linhas")
    assert current.denied and current.count == 1
    assert json.loads(current.progress_path.read_text())["status"] == "paused"


def test_long_retry_after_pauses_without_traffic(tmp_path):
    error = urllib.error.HTTPError(
        BASE, 429, "SYNTHETIC rate limit", {"Retry-After": "120"}, None
    )
    current = reader(tmp_path, Opener(error))
    with pytest.raises(urllib.error.HTTPError):
        current.get("linhas")
    assert current.stop_reason == "rate_limited" and current.count == 1


def test_atomic_write_failure_keeps_destination(tmp_path, monkeypatch):
    from transporte import persistence

    target = tmp_path / "existing.json"
    target.write_bytes(b"SYNTHETIC previous")

    def fail(*_):
        raise OSError("SYNTHETIC disk failure")

    monkeypatch.setattr(persistence.os, "replace", fail)
    with pytest.raises(OSError):
        atomic_bytes(target, b"SYNTHETIC new")
    assert target.read_bytes() == b"SYNTHETIC previous"
    assert not list(tmp_path.glob("*.tmp"))


def test_repeated_transient_resources_open_circuit(tmp_path):
    current = reader(
        tmp_path, Opener(*[TimeoutError("SYNTHETIC") for _ in range(3)]), retries=0
    )
    for _ in range(3):
        with pytest.raises(TimeoutError):
            current.get("linhas")
    assert current.stop_reason == "repeated_transient_failures"
    with pytest.raises(ValueError, match="suspensa"):
        current.get("linhas")
    assert current.count == 3
