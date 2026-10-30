"""Histórico imutável, deduplicado; SQLite para testes, PostgreSQL para produção."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA = '''
CREATE TABLE IF NOT EXISTS position (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL, vehicle_id TEXT NOT NULL, route_id TEXT NOT NULL,
 observed_at TEXT NOT NULL, fetched_at TEXT NOT NULL, longitude DOUBLE PRECISION NOT NULL,
 latitude DOUBLE PRECISION NOT NULL, speed_kmh DOUBLE PRECISION, bearing DOUBLE PRECISION, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS position_vehicle_time ON position(source_id,vehicle_id,observed_at);
CREATE INDEX IF NOT EXISTS position_route_time ON position(route_id,observed_at);
CREATE TABLE IF NOT EXISTS collection_run (
 id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL,
 accepted INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0, message TEXT
);
CREATE TABLE IF NOT EXISTS audit_event (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL, vehicle_id TEXT NOT NULL, route_id TEXT NOT NULL,
 observed_at TEXT NOT NULL, kind TEXT NOT NULL, classification TEXT NOT NULL, algorithm_version TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_review (
 id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES audit_event(id), created_at TEXT NOT NULL,
 actor TEXT NOT NULL, classification TEXT NOT NULL, reason TEXT NOT NULL
);
'''


class Store:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv('DATABASE_URL','sqlite:///var/operational.sqlite')
        self.postgres = self.dsn.startswith(('postgres://','postgresql://'))

    @contextmanager
    def connection(self):
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row
            connection=psycopg.connect(self.dsn,row_factory=dict_row)
        else:
            path=self.dsn.removeprefix('sqlite:///')
            Path(path).parent.mkdir(parents=True,exist_ok=True)
            connection=sqlite3.connect(path)
            connection.row_factory=sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def execute(self, connection, query, params=()):
        return connection.execute(query.replace('?', '%s') if self.postgres else query,params)

    def initialize(self):
        with self.connection() as connection:
            for sql in SCHEMA.split(';'):
                if sql.strip():
                    connection.execute(sql)

    def insert(self, positions):
        inserted=0
        with self.connection() as connection:
            for p in positions:
                # Mesmo instante com coordenadas diferentes: preservar ambas como evidências.
                identity={k:p[k] for k in ('source_id','vehicle_id','observed_at','longitude','latitude')}
                digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
                params=(digest,*[p.get(k) for k in ('source_id','vehicle_id','route_id','observed_at','fetched_at','longitude','latitude','speed_kmh','bearing')],json.dumps(p,ensure_ascii=False))
                cursor=self.execute(connection,'INSERT INTO position VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',params)
                inserted+=cursor.rowcount
        return inserted

    def history(self, vehicle=None, start=None, end=None, route=None, limit=10000):
        clauses,params=[],[]
        for field,value,op in [('vehicle_id',vehicle,'='),('observed_at',start,'>='),('observed_at',end,'<'),('route_id',route,'=')]:
            if value:
                clauses.append(field+' '+op+' ?');params.append(value)
        sql='SELECT * FROM position'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY observed_at LIMIT ?'
        with self.connection() as connection:
            return [json.loads(row['payload']) for row in self.execute(connection,sql,(*params,limit)).fetchall()]

    def latest(self, since):
        with self.connection() as connection:
            query='''SELECT payload FROM (
                SELECT payload,ROW_NUMBER() OVER (
                    PARTITION BY source_id,vehicle_id ORDER BY observed_at DESC,fetched_at DESC,id DESC
                ) AS rank FROM position WHERE observed_at>=?
            ) ranked WHERE rank=1'''
            return [json.loads(row['payload']) for row in self.execute(connection,query,(since,)).fetchall()]

    def save_run(self, run):
        with self.connection() as connection:
            self.execute(connection,'INSERT INTO collection_run VALUES (?,?,?,?,?,?,?)',(run['id'],run['started_at'],run.get('ended_at'),run['status'],run.get('accepted',0),run.get('rejected',0),run.get('message')))

    def events(self, vehicle=None, route=None, start=None, end=None, limit=1000):
        clauses,params=[],[]
        for field,value,op in [('vehicle_id',vehicle,'='),('route_id',route,'='),('observed_at',start,'>='),('observed_at',end,'<')]:
            if value:clauses.append(field+' '+op+' ?');params.append(value)
        with self.connection() as connection:
            query='SELECT id,payload FROM audit_event'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY observed_at DESC LIMIT ?'
            return [{'id':row['id'],**json.loads(row['payload'])} for row in self.execute(connection,query,(*params,limit)).fetchall()]

    def save_events(self, positions):
        from .audit import trajectory_events
        groups={}
        for p in positions:
            groups.setdefault((p['source_id'],p['vehicle_id'],p['route_id']),[]).append(p)
        with self.connection() as connection:
            for (source,vehicle,route),items in groups.items():
                for event in trajectory_events(items):
                    encoded=json.dumps(event,ensure_ascii=False,sort_keys=True)
                    digest=hashlib.sha256(encoded.encode()).hexdigest()
                    self.execute(connection,'INSERT INTO audit_event VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
                        (digest,source,vehicle,route,event['evidence'][-1]['observed_at'],event['kind'],event['classification'],event['algorithm_version'],encoded))
