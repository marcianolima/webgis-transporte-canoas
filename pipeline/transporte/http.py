"""HTTP limitado, cacheado e auditável. Não executa scripts remotos."""
import hashlib
import json
import time
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class Fetcher:
    def __init__(self, cache: Path, interval=0.75, retries=2, timeout=25):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.interval, self.retries, self.timeout = interval, retries, timeout
        self.last = 0.0
        self.records = []
        self.lock = threading.Lock()

    def get(self, url: str, ttl=86400):
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / (key + '.json')
        if path.exists() and time.time() - path.stat().st_mtime < ttl:
            item = json.loads(path.read_text())
            self.records.append({k: v for k, v in item.items() if k != 'body'} | {'cache_hit': True})
            return item
        for attempt in range(self.retries + 1):
            with self.lock:
                time.sleep(max(0, self.interval - (time.monotonic() - self.last)))
                self.last = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'GeoCanoasTransporte/0.1 (+https://github.com/marcianolima/webgis-transporte-canoas)', 'Accept': 'application/json,text/plain,*/*'})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    body = response.read(15_000_001)
                    if len(body) > 15_000_000:
                        raise ValueError('Resposta acima de 15 MB')
                    item = {'url': url, 'fetched_at': utcnow(), 'status': response.status,
                            'sha256': hashlib.sha256(body).hexdigest(), 'body': body.decode('utf-8-sig')}
                path.write_text(json.dumps(item, ensure_ascii=False))
                self.records.append({k: v for k, v in item.items() if k != 'body'})
                return item
            except (urllib.error.URLError, TimeoutError) as exc:
                code = getattr(exc, 'code', None)
                if code in (401, 403, 404) or attempt == self.retries:
                    self.records.append({'url': url, 'fetched_at': utcnow(), 'error': str(exc), 'status': code})
                    raise
                time.sleep(min(30, 2 ** (attempt + 1)))
