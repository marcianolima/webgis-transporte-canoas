-- Modelo complementar temporal. Não insere linhas, veículos ou geometrias fictícios.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS transporte;
CREATE TABLE IF NOT EXISTS transporte.source (
 id text PRIMARY KEY, name text NOT NULL, base_url text, license text,
 status text NOT NULL DEFAULT 'pending', verified_at timestamptz,
 metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS transporte.route (
 source_id text REFERENCES transporte.source(id), id text, code text NOT NULL,
 name text NOT NULL, municipality_code text NOT NULL CHECK(municipality_code='4304606'),
 valid_from timestamptz NOT NULL, valid_to timestamptz, payload_hash text NOT NULL,
 payload jsonb NOT NULL, PRIMARY KEY(source_id,id,valid_from), CHECK(valid_to IS NULL OR valid_to>valid_from)
);
CREATE TABLE IF NOT EXISTS transporte.itinerary_version (
 id text PRIMARY KEY, source_id text REFERENCES transporte.source(id), route_id text NOT NULL,
 direction text, source_itinerary_id text, valid_from timestamptz NOT NULL, valid_to timestamptz,
 geom geometry(MultiLineString,4326), source_hash text NOT NULL, payload jsonb NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from)
);
CREATE INDEX IF NOT EXISTS itinerary_geom ON transporte.itinerary_version USING gist(geom);
CREATE TABLE IF NOT EXISTS transporte.stop_version (
 source_id text REFERENCES transporte.source(id), id text, valid_from timestamptz NOT NULL,
 valid_to timestamptz, name text, geom geometry(Point,4326), payload jsonb NOT NULL,
 PRIMARY KEY(source_id,id,valid_from)
);
CREATE INDEX IF NOT EXISTS stop_geom ON transporte.stop_version USING gist(geom);
CREATE TABLE IF NOT EXISTS transporte.itinerary_stop (
 itinerary_version_id text REFERENCES transporte.itinerary_version(id), sequence integer,
 stop_source_id text, stop_id text, PRIMARY KEY(itinerary_version_id,sequence)
);
CREATE TABLE IF NOT EXISTS transporte.scheduled_trip (
 id text PRIMARY KEY, source_id text REFERENCES transporte.source(id), route_id text NOT NULL,
 itinerary_version_id text REFERENCES transporte.itinerary_version(id), service_date date NOT NULL,
 departure_seconds integer NOT NULL CHECK(departure_seconds>=0 AND departure_seconds<172800),
 direction text, source_hash text, payload jsonb
);
CREATE TABLE IF NOT EXISTS transporte.observed_trip (
 id text PRIMARY KEY, route_id text, vehicle_id text, started_at timestamptz, ended_at timestamptz,
 algorithm_version text NOT NULL, confidence text NOT NULL, evidence jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS transporte.indicator (
 id text, period_start timestamptz, period_end timestamptz, route_id text,
 value double precision, unit text NOT NULL, observations bigint NOT NULL,
 method_version text NOT NULL, provenance jsonb NOT NULL, PRIMARY KEY(id,period_start,route_id)
);
-- As tabelas position, collection_run, audit_event e audit_review são criadas por
-- transporte.store.initialize() na API/worker. O modelo acima é complementar,
-- preparado para ingestão futura de trajetos e viagens com contratos homologados.
