CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    processing_time_s INTEGER,
    availability_pct REAL,
    mttr_s INTEGER,
    power_working_kw REAL,
    power_idle_kw REAL
);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER,
    before TEXT,
    after TEXT
);

CREATE TABLE tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale REAL
);

CREATE TABLE raw_ingest (
    ingested_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);

CREATE TABLE events (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    reason_code TEXT,
    duration_s REAL,
    energy_kwh REAL
);

CREATE TABLE samples (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    value REAL
);

-- Populate machines table with data from requirements
INSERT INTO machines (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
('M1', 90, 99, 600, 3.0, 0.3),
('M2', 70, 98, 900, 4.5, 0.45),
('M3', 110, 99, 1200, 6.0, 0.6);

-- Populate buffers table with data from requirements
INSERT INTO buffers (id, capacity, before, after) VALUES
('B0', 15, 'source', 'M1'),
('B1', 5, 'M1', 'M2'),
('B2', 5, 'M2', 'M3');

-- Populate tag_map table with data from requirements
INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
('time', 'M1', 'machine processing time', 's', 'time', 1),
('time', 'M2', 'machine processing time', 's', 'time', 1),
('time', 'M3', 'machine processing time', 's', 'time', 1),
('availability', 'M1', 'machine availability', '%', 'availability', 1),
('availability', 'M2', 'machine availability', '%', 'availability', 1),
('availability', 'M3', 'machine availability', '%', 'availability', 1),
('mttr', 'M1', 'machine MTTR', 's', 'mttr', 1),
('mttr', 'M2', 'machine MTTR', 's', 'mttr', 1),
('mttr', 'M3', 'machine MTTR', 's', 'mttr', 1),
('power', 'M1', 'machine power', 'kW', 'power', 1),
('power', 'M2', 'machine power', 'kW', 'power', 1),
('power', 'M3', 'machine power', 'kW', 'power', 1);

-- Create indexes for performance
CREATE INDEX idx_events_machine_id_ts ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_id_ts ON samples (machine_id, ts);

-- Create views to expose typed fact tables over raw_ingest
CREATE VIEW events_view AS SELECT T1.ts, T1.machine_id, T1.reason_code, T1.duration_s, T1.energy_kwh FROM raw_ingest AS T1 INNER JOIN jsonb_each(T1.payload) AS T2 ON T2.key = 'events' AND T2.value::jsonb->>'type' = 'event';
CREATE VIEW samples_view AS SELECT T1.ts, T1.machine_id, T1.tag, T1.value FROM raw_ingest AS T1 INNER JOIN jsonb_each(T1.payload) AS T2 ON T2.key = 'samples' AND T2.value::jsonb->>'type' = 'sample';