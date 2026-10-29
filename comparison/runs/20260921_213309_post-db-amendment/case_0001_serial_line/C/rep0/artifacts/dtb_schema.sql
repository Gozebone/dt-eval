CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    process_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION
);

INSERT INTO machines (id, process_time_s, availability, mttr_s) VALUES
('M1', 150, 0.98, 600),
('M2', 120, 0.97, 900),
('M3', 180, 0.95, 1200),
('M4', 120, 0.97, 900),
('M5', 150, 0.98, 600);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
);

INSERT INTO buffers (id, capacity) VALUES
('B0', 20),
('B1', 8),
('B2', 8),
('B3', 8),
('B4', 8);

CREATE TABLE stations (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
);

INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
('M1', 150, 99.45, 793.67, 4.0, 0.4),
('M2', 120, 96.86, 1053.95, 5.0, 0.5),
('M3', 180, 99.03, 4200.65, 6.0, 0.6),
('M4', 120, 97.39, 1894.81, 5.0, 0.5),
('M5', 150, 99.56, 641.17, 4.0, 0.4);

CREATE TABLE tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
);

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
('machines', 'M1', 'process_time', 's', 'process_time', 1.0),
('machines', 'M2', 'process_time', 's', 'process_time', 1.0),
('machines', 'M3', 'process_time', 's', 'process_time', 1.0),
('machines', 'M4', 'process_time', 's', 'process_time', 1.0),
('machines', 'M5', 'process_time', 's', 'process_time', 1.0),
('machines', 'M1', 'availability', '%', 'availability', 1.0),
('machines', 'M2', 'availability', '%', 'availability', 1.0),
('machines', 'M3', 'availability', '%', 'availability', 1.0),
('machines', 'M4', 'availability', '%', 'availability', 1.0),
('machines', 'M5', 'availability', '%', 'availability', 1.0),
('machines', 'M1', 'mttr', 's', 'mttr', 1.0),
('machines', 'M2', 'mttr', 's', 'mttr', 1.0),
('machines', 'M3', 'mttr', 's', 'mttr', 1.0),
('machines', 'M4', 'mttr', 's', 'mttr', 1.0),
('machines', 'M5', 'mttr', 's', 'mttr', 1.0),
('buffers', 'B0', 'capacity', 'units', 'capacity', 1.0),
('buffers', 'B1', 'capacity', 'units', 'capacity', 1.0),
('buffers', 'B2', 'capacity', 'units', 'capacity', 1.0),
('buffers', 'B3', 'capacity', 'units', 'capacity', 1.0),
('buffers', 'B4', 'capacity', 'units', 'capacity', 1.0);

CREATE TABLE raw_ingest (
    ingested_at TIMESTAMPTZ PRIMARY KEY,
    source TEXT,
    payload JSONB
);

CREATE TABLE events (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    reason_code TEXT,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION,
    PRIMARY KEY (ts, machine_id)
);

CREATE INDEX idx_events_machine_id_ts ON events (machine_id, ts);

CREATE TABLE samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION,
    PRIMARY KEY (ts, machine_id, tag)
);

CREATE INDEX idx_samples_machine_id_ts ON samples (machine_id, ts);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);