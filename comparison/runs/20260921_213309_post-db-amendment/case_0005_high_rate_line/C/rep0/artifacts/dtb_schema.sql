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
    capacity int NOT NULL,
    before text NOT NULL,
    after text NOT NULL
);

CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s int NOT NULL,
    availability_pct double precision NOT NULL,
    mttr_s int NOT NULL,
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

CREATE TABLE events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text NOT NULL,
    duration_s double precision NOT NULL,
    energy_kwh double precision NOT NULL
);

CREATE TABLE samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision NOT NULL
);

-- Insert dimension data from requirements
INSERT INTO machines (id, name) VALUES ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('M4', 'M4'), ('B0', 'B0'), ('B1', 'B1'), ('B2', 'B2'), ('B3', 'B3');

INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES 
('M1', 60, 0.995, 300, 3.0, 0.3),
('M2', 80, 0.99, 600, 5.0, 0.5),
('M3', 70, 0.99, 600, 4.5, 0.45),
('M4', 75, 0.995, 300, 4.0, 0.4);

INSERT INTO buffers (id, capacity, before, after) VALUES 
('B0', 25, 'source', 'M1'),
('B1', 10, 'M1', 'M2'),
('B2', 10, 'M2', 'M3'),
('B3', 10, 'M3', 'M4');

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES 
('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M1', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M1', 'capacity', 'units', 'capacity', 1),
('process_time_s', 'M2', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M2', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M2', 'capacity', 'units', 'capacity', 1),
('process_time_s', 'M3', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M3', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M3', 'capacity', 'units', 'capacity', 1),
('process_time_s', 'M4', 'process_time_s', 's', 'process_time_s', 1),
('availability', 'M4', 'availability', 'pct', 'availability', 1),
('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1),
('work_power_kw', 'M4', 'work_power_kw', 'kW', 'work_power_kw', 1),
('idle_power_kw', 'M4', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
('capacity', 'M4', 'capacity', 'units', 'capacity', 1);

-- Create indexes for performance
CREATE INDEX idx_events_machine_time ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts);