CREATE TABLE raw_ingest (
    ingested_at timestamptz NOT NULL,
    source text NOT NULL,
    payload jsonb NOT NULL
);

CREATE TABLE ingest_watermark (
    source text PRIMARY KEY,
    max_event_ts timestamptz
);

CREATE TABLE tag_map (
    tag_id text PRIMARY KEY,
    machine_id text,
    signal text,
    unit text,
    register text,
    scale double precision
);

CREATE TABLE machines (
    id text PRIMARY KEY,
    process_time_s double precision,
    availability double precision,
    mttr_s double precision,
    power_working_kw double precision,
    power_idle_kw double precision,
    capacity double precision
);

CREATE TABLE buffers (
    id text PRIMARY KEY,
    capacity double precision,
    before text,
    after text
);

CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s double precision,
    availability_pct double precision,
    mttr_s double precision,
    power_working_kw double precision,
    power_idle_kw double precision
);

INSERT INTO machines (id, process_time_s, availability, mttr_s, power_working_kw, power_idle_kw, capacity) VALUES
('M1', 150, 0.98, 600, 4.0, 0.4, NULL),
('M2', 120, 0.97, 900, 5.0, 0.5, NULL),
('M3', 180, 0.95, 1200, 6.0, 0.6, NULL),
('M4', 120, 0.97, 900, 5.0, 0.5, NULL),
('M5', 150, 0.98, 600, 4.0, 0.4, NULL);

INSERT INTO buffers (id, capacity, before, after) VALUES
('B0', 20, 'source', 'M1'),
('B1', 8, 'M1', 'M2'),
('B2', 8, 'M2', 'M3'),
('B3', 8, 'M3', 'M4'),
('B4', 8, 'M4', 'M5');

INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
('M1', 150, 98, 600, 4.0, 0.4),
('M2', 120, 97, 900, 5.0, 0.5),
('M3', 180, 95, 1200, 6.0, 0.6),
('M4', 120, 97, 900, 5.0, 0.5),
('M5', 150, 98, 600, 4.0, 0.4);

CREATE TABLE events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text,
    duration_s double precision,
    energy_kwh double precision
);

CREATE TABLE samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision
);

CREATE INDEX idx_events_machine_ts ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_ts ON samples (machine_id, ts);

CREATE VIEW raw_events AS SELECT DISTINCT ts, machine_id, reason_code, duration_s, energy_kwh FROM events;
CREATE VIEW raw_samples AS SELECT DISTINCT ts, machine_id, tag, value FROM samples;
CREATE VIEW raw_data AS SELECT DISTINCT ts, machine_id, tag, value FROM samples;