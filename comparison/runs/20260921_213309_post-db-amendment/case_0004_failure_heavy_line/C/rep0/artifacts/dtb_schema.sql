CREATE TABLE raw_ingest (
    ingested_at timestamptz NOT NULL,
    source text NOT NULL,
    payload jsonb NOT NULL
);

CREATE TABLE ingest_watermark (
    source text PRIMARY KEY,
    max_event_ts timestamptz
);

CREATE TABLE machines (
    id text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE buffers (
    id text PRIMARY KEY,
    capacity integer NOT NULL,
    before text NOT NULL,
    after text NOT NULL
);

CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s double precision NOT NULL,
    availability_pct double precision NOT NULL,
    mttr_s double precision NOT NULL,
    power_working_kw double precision NOT NULL,
    power_idle_kw double precision NOT NULL
);

CREATE TABLE tag_map (
    tag_id text PRIMARY KEY,
    machine_id text NOT NULL,
    signal text NOT NULL,
    unit text NOT NULL,
    register text NOT NULL,
    scale double precision NOT NULL
);

-- Insert machines from requirements
INSERT INTO machines (id, name) VALUES ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('M4', 'M4'), ('M5', 'M5');

-- Insert buffers from requirements
INSERT INTO buffers (id, capacity, before, after) VALUES ('B0', 6, 'source', 'M1'), ('B1', 3, 'M1', 'M2'), ('B2', 3, 'M2', 'M3'), ('B3', 3, 'M3', 'M4'), ('B4', 3, 'M4', 'M5');

-- Insert stations from requirements
INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES 
('M1', 99.96, 92.58, 3206.25, 4.0, 0.4),
('M2', 130.16, 97.36, 2859.26, 5.0, 0.5),
('M3', 90.14, 94.69, 2882.82, 4.5, 0.45),
('M4', 140.19, 100.0, 1099.8, 7.0, 0.7),
('M5', 109.82, 98.23, 2400, 5.5, 0.55);

-- Fact table for events: (ts, machine_id, reason_code, duration_s, energy_kwh)
CREATE TABLE events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text,
    duration_s double precision,
    energy_kwh double precision
);

-- Fact table for samples: (ts, machine_id, tag, value)
CREATE TABLE samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision
);

-- Indexes for performance
CREATE INDEX idx_events_machine_ts ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_ts ON samples (machine_id, ts);