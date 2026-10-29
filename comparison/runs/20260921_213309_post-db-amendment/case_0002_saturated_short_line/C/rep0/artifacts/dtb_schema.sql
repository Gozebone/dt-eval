CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    process_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    work_power_kw DOUBLE PRECISION,
    idle_power_kw DOUBLE PRECISION
);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER,
    before TEXT,
    after TEXT
);

CREATE TABLE stations (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
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
    source TEXT,
    payload JSONB
);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);

CREATE TABLE events (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT,
    reason_code TEXT,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION
);

CREATE TABLE samples (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION
);

INSERT INTO machines (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw) VALUES
('M1', 90, 0.99, 600, 3.0, 0.3),
('M2', 70, 0.98, 900, 4.5, 0.45),
('M3', 110, 0.99, 1200, 6.0, 0.6);

INSERT INTO buffers (id, capacity, before, after) VALUES
('B0', 15, 'source', 'M1'),
('B1', 5, 'M1', 'M2'),
('B2', 5, 'M2', 'M3');

INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
('M1', 90, 99, 600, 3.0, 0.3),
('M2', 70, 98, 900, 4.5, 0.45),
('M3', 110, 99, 1200, 6.0, 0.6);

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
('temp_M1', 'M1', 'temperature', 'C', 'temp', 1.0),
('pressure_M1', 'M1', 'pressure', 'bar', 'pressure', 1.0),
('temp_M2', 'M2', 'temperature', 'C', 'temp', 1.0),
('pressure_M2', 'M2', 'pressure', 'bar', 'pressure', 1.0),
('temp_M3', 'M3', 'temperature', 'C', 'temp', 1.0),
('pressure_M3', 'M3', 'pressure', 'bar', 'pressure', 1.0);

CREATE INDEX idx_events_machine_time ON events(machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples(machine_id, ts);
CREATE INDEX idx_raw_ingest_source ON raw_ingest(source);
CREATE INDEX idx_ingest_watermark_source ON ingest_watermark(source);