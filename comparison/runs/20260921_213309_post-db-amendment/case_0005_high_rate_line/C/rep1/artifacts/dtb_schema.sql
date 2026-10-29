CREATE TABLE tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
);

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M1', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M1', 'capacity', 'unit', 'capacity', 1),
('inter_arrival_s', 'M1', 'inter_arrival_s', 's', 'inter_arrival_s', 1),
('process_time_s', 'M2', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M2', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M2', 'capacity', 'unit', 'capacity', 1),
('inter_arrival_s', 'M2', 'inter_arrival_s', 's', 'inter_arrival_s', 1),
('process_time_s', 'M3', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M3', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M3', 'capacity', 'unit', 'capacity', 1),
('inter_arrival_s', 'M3', 'inter_arrival_s', 's', 'inter_arrival_s', 1),
('process_time_s', 'M4', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M4', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M4', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M4', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M4', 'capacity', 'unit', 'capacity', 1),
('inter_arrival_s', 'M4', 'inter_arrival_s', 's', 'inter_arrival_s', 1);

CREATE TABLE raw_ingest (
    ingested_at TIMESTAMPTZ,
    source TEXT,
    payload JSONB
);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);

CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    processing_time_s INT,
    availability_pct DOUBLE PRECISION,
    mttr_s INT,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
);

INSERT INTO machines (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
('M1', 60, 99.95, 300, 3.0, 0.3),
('M2', 80, 99.0, 600, 5.0, 0.5),
('M3', 70, 99.0, 600, 4.5, 0.45),
('M4', 75, 99.95, 300, 4.0, 0.4);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INT,
    before TEXT,
    after TEXT
);

INSERT INTO buffers (id, capacity, before, after) VALUES
('B0', 25, 'source', 'M1'),
('B1', 10, 'M1', 'M2'),
('B2', 10, 'M2', 'M3'),
('B3', 10, 'M3', 'M4');

CREATE TABLE events (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    reason_code TEXT,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION
);

CREATE TABLE samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION
);

CREATE INDEX idx_events_machine_time ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts);