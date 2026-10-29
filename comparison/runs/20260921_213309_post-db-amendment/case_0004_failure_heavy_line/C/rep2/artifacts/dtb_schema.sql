CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
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
    scale DOUBLE PRECISION
);

CREATE TABLE raw_ingest (
    ingested_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE events (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION
);

CREATE TABLE samples (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    value DOUBLE PRECISION
);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);

-- Insert dimension data from requirements
INSERT INTO machines VALUES
('M1', 100, 0.9, 2400, 4.0, 0.4),
('M2', 130, 0.92, 3000, 5.0, 0.5),
('M3', 90, 0.88, 3600, 4.5, 0.45),
('M4', 140, 0.91, 4800, 7.0, 0.7),
('M5', 110, 0.93, 2400, 5.5, 0.55);

INSERT INTO buffers VALUES
('B0', 6, 'source', 'M1'),
('B1', 3, 'M1', 'M2'),
('B2', 3, 'M2', 'M3'),
('B3', 3, 'M3', 'M4'),
('B4', 3, 'M4', 'M5');

INSERT INTO tag_map VALUES
('M1_temp', 'M1', 'temperature', 'C', 'temp', 1.0),
('M1_pressure', 'M1', 'pressure', 'bar', 'pressure', 1.0),
('M2_temp', 'M2', 'temperature', 'C', 'temp', 1.0),
('M2_pressure', 'M2', 'pressure', 'bar', 'pressure', 1.0),
('M3_temp', 'M3', 'temperature', 'C', 'temp', 1.0),
('M3_pressure', 'M3', 'pressure', 'bar', 'pressure', 1.0),
('M4_temp', 'M4', 'temperature', 'C', 'temp', 1.0),
('M4_pressure', 'M4', 'pressure', 'bar', 'pressure', 1.0),
('M5_temp', 'M5', 'temperature', 'C', 'temp', 1.0),
('M5_pressure', 'M5', 'pressure', 'bar', 'pressure', 1.0);

-- Create views over raw_ingest to expose typed fact tables
CREATE VIEW events_view AS SELECT DISTINCT T1.ts, T1.machine_id, T1.reason_code, T1.duration_s, T1.energy_kwh FROM raw_ingest AS T1 INNER JOIN JSONB_PATH_QUERY(T1.payload, '$.events[*]') AS T2 ON T1.ingested_at = T2.ts;

CREATE VIEW samples_view AS SELECT DISTINCT T1.ts, T1.machine_id, T1.tag, T1.value FROM raw_ingest AS T1 INNER JOIN JSONB_PATH_QUERY(T1.payload, '$.samples[*]') AS T2 ON T1.ingested_at = T2.ts;

-- Add indexes for performance
CREATE INDEX idx_events_machine_time ON events(machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples(machine_id, ts);
CREATE INDEX idx_raw_ingest_source ON raw_ingest(source);
CREATE INDEX idx_ingest_watermark_source ON ingest_watermark(source);