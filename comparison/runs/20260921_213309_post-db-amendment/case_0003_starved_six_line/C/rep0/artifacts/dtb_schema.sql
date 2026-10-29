CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    process_time_s INTEGER,
    availability DOUBLE PRECISION,
    mttr_s INTEGER,
    work_power_kw DOUBLE PRECISION,
    idle_power_kw DOUBLE PRECISION
);

INSERT INTO machines (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw) VALUES
('M1', 200, 0.97, 900, 5.0, 0.5),
('M2', 220, 0.97, 1000, 5.5, 0.55),
('M3', 240, 0.96, 1200, 6.0, 0.6),
('M4', 260, 0.96, 1400, 7.0, 0.7),
('M5', 230, 0.97, 1100, 6.5, 0.65),
('M6', 210, 0.97, 1000, 6.0, 0.6);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
);

INSERT INTO buffers (id, capacity) VALUES
('B0', 10),
('B1', 10),
('B2', 10),
('B3', 10),
('B4', 10),
('B5', 10);

CREATE TABLE tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
);

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
('M1_proc_time', 'M1', 'process_time_s', 's', 'process_time_s', 1.0),
('M1_avail', 'M1', 'availability', 'ratio', 'availability', 1.0),
('M1_mttr', 'M1', 'mttr_s', 's', 'mttr_s', 1.0),
('M1_work_power', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M1_idle_power', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('M2_proc_time', 'M2', 'process_time_s', 's', 'process_time_s', 1.0),
('M2_avail', 'M2', 'availability', 'ratio', 'availability', 1.0),
('M2_mttr', 'M2', 'mttr_s', 's', 'mttr_s', 1.0),
('M2_work_power', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M2_idle_power', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('M3_proc_time', 'M3', 'process_time_s', 's', 'process_time_s', 1.0),
('M3_avail', 'M3', 'availability', 'ratio', 'availability', 1.0),
('M3_mttr', 'M3', 'mttr_s', 's', 'mttr_s', 1.0),
('M3_work_power', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M3_idle_power', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('M4_proc_time', 'M4', 'process_time_s', 's', 'process_time_s', 1.0),
('M4_avail', 'M4', 'availability', 'ratio', 'availability', 1.0),
('M4_mttr', 'M4', 'mttr_s', 's', 'mttr_s', 1.0),
('M4_work_power', 'M4', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M4_idle_power', 'M4', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('M5_proc_time', 'M5', 'process_time_s', 's', 'process_time_s', 1.0),
('M5_avail', 'M5', 'availability', 'ratio', 'availability', 1.0),
('M5_mttr', 'M5', 'mttr_s', 's', 'mttr_s', 1.0),
('M5_work_power', 'M5', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M5_idle_power', 'M5', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('M6_proc_time', 'M6', 'process_time_s', 's', 'process_time_s', 1.0),
('M6_avail', 'M6', 'availability', 'ratio', 'availability', 1.0),
('M6_mttr', 'M6', 'mttr_s', 's', 'mttr_s', 1.0),
('M6_work_power', 'M6', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
('M6_idle_power', 'M6', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0),
('B0_capacity', 'B0', 'capacity', 'units', 'capacity', 1.0),
('B1_capacity', 'B1', 'capacity', 'units', 'capacity', 1.0),
('B2_capacity', 'B2', 'capacity', 'units', 'capacity', 1.0),
('B3_capacity', 'B3', 'capacity', 'units', 'capacity', 1.0),
('B4_capacity', 'B4', 'capacity', 'units', 'capacity', 1.0),
('B5_capacity', 'B5', 'capacity', 'units', 'capacity', 1.0);

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

CREATE INDEX idx_events_machine_time ON events (machine_id, ts);

CREATE TABLE samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION,
    PRIMARY KEY (ts, machine_id, tag)
);

CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);