"""Leitor TACOM retomável, com timeout, orçamento e novas tentativas limitadas."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
from .gobus import request_path, payload
from .http import utcnow
from .persistence import atomic_json

BASE = "http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirecionamento não permitido")


class Reader:
    def __init__(
        self,
        folder,
        interval=2,
        max_requests=180,
        *,
        timeout=60,
        retries=2,
        opener=None,
        sleep=time.sleep,
        clock=time.monotonic,
        failure_limit=3,
    ):
        if not 10 <= timeout <= 90:
            raise ValueError("Timeout deve ficar entre 10 e 90 segundos")
        if not 0 <= retries <= 2:
            raise ValueError("Aceitas até duas novas tentativas")
        if not 1 <= max_requests <= 300:
            raise ValueError("Orçamento deve ficar entre 1 e 300 requisições")
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.interval = max(1.5, interval)
        self.maximum = max_requests
        self.timeout = timeout
        self.retries = retries
        self.opener = opener or urllib.request.build_opener(NoRedirect)
        self.sleep = sleep
        self.clock = clock
        self.failure_limit = failure_limit
        self.count = 0
        self.cache_hits = 0
        self.retry_attempts = 0
        self.successes = 0
        self.failed_resources = 0
        self.failure_streak = 0
        self.last = 0.0
        self.cooldown_until = 0.0
        self.lock = threading.Lock()
        self.denied = False
        self.stop_reason = None
        self.records = []
        self.started_at = utcnow()
        self.run_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        self.progress_path = self.folder.parent / "runs" / (self.run_id + ".json")
        self._progress("running")

    def _progress(self, status="running", resource=None):
        value = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "updated_at": utcnow(),
            "status": status,
            "http_requests": self.count,
            "request_limit": self.maximum,
            "cache_hits": self.cache_hits,
            "retry_attempts": self.retry_attempts,
            "successful_responses": self.successes,
            "failed_resources": self.failed_resources,
            "timeout_seconds": self.timeout,
            "retries_per_resource": self.retries,
            "stop_reason": self.stop_reason,
            "last_resource": resource,
            "private_capture_cache": str(self.folder),
        }
        atomic_json(self.progress_path, value)
        return value

    def finish(self, status):
        with self.lock:
            return self._progress(status)

    def archive(self, item):
        history = self.folder.parent / "source-history"
        history.mkdir(parents=True, exist_ok=True)
        identity = hashlib.sha256(
            (item["url"] + item["fetched_at"] + item["sha256"]).encode()
        ).hexdigest()
        target = history / (identity + ".json")
        if not target.exists():
            atomic_json(target, item)

    def _reserve(self, kind, is_retry):
        with self.lock:
            if self.denied or self.stop_reason:
                raise ValueError(
                    "Coleta suspensa: " + str(self.stop_reason or "acesso negado")
                )
            if self.count >= self.maximum:
                raise ValueError("Orçamento de requisições atingido")
            self.sleep(
                max(
                    0,
                    self.interval - (self.clock() - self.last),
                    self.cooldown_until - self.clock(),
                )
            )
            self.last = self.clock()
            self.count += 1
            self.retry_attempts += int(is_retry)
            self._progress(resource=kind)

    def get(self, kind, **params):
        url = BASE + request_path(kind, **params)
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.folder / (key + ".json")
        ttl = 300 if kind == "previsoes" else 86400
        if path.exists():
            cached = json.loads(path.read_text())
            self.archive(cached)
            age = time.time() - datetime.fromisoformat(cached["fetched_at"]).timestamp()
            if 0 <= age < ttl:
                document = payload(cached["body"])
                with self.lock:
                    self.cache_hits += 1
                    self._progress(resource=kind)
                return document, {k: v for k, v in cached.items() if k != "body"}
        for attempt in range(self.retries + 1):
            self._reserve(kind, attempt > 0)
            retry_delay = min(16, 2 ** (attempt + 1))
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "GeoCanoasTransporte-AuthorizedResearch/0.4.0",
                        "Accept": "application/javascript,application/json,text/plain",
                    },
                )
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(5_000_001)
                    if len(raw) > 5_000_000:
                        raise ValueError("Resposta acima de 5 MB")
                    if response.status != 200:
                        raise ValueError("HTTP diferente de 200")
                body = raw.decode("utf-8-sig")
                document = payload(body)
                item = {
                    "url": url,
                    "fetched_at": utcnow(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "kind": kind,
                    "params": params,
                    "body": body,
                }
                self.archive(item)
                atomic_json(path, item)
                with self.lock:
                    self.successes += 1
                    self.failure_streak = 0
                    self.records.append({k: v for k, v in item.items() if k != "body"})
                    self._progress(resource=kind)
                return document, {k: v for k, v in item.items() if k != "body"}
            except Exception as error:
                transient = isinstance(
                    error, (TimeoutError, socket.timeout, urllib.error.URLError)
                )
                if isinstance(error, urllib.error.HTTPError):
                    transient = error.code in (408, 429, 500, 502, 503, 504)
                    if error.code in (401, 403):
                        self.denied = True
                        self.stop_reason = "access_denied"
                    if error.code == 429:
                        try:
                            retry_delay = max(
                                retry_delay,
                                float(error.headers.get("Retry-After", "0")),
                            )
                        except (TypeError, ValueError):
                            pass
                        if retry_delay > 30:
                            self.stop_reason = "rate_limited"
                            transient = False
                        else:
                            with self.lock:
                                self.cooldown_until = max(
                                    self.cooldown_until, self.clock() + retry_delay
                                )
                if transient and attempt < self.retries and not self.stop_reason:
                    self.sleep(retry_delay)
                    continue
                with self.lock:
                    self.failed_resources += 1
                    if transient:
                        self.failure_streak += 1
                        if self.failure_streak >= self.failure_limit:
                            self.stop_reason = "repeated_transient_failures"
                    self._progress("paused" if self.stop_reason else "running", kind)
                raise
