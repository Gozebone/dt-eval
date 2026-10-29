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
    process_name text
);

CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s double precision,
    availability_pct double precision,
    mttr_s double precision,
    power_working_kw double precision,
    power_idle_kw double precision
);

CREATE TABLE buffers (
    id text PRIMARY KEY,
    capacity int,
    before text,
    after text
);

CREATE TABLE tag_map (
    tag_id text PRIMARY KEY,
    machine_id text,
    signal text,
    unit text,
    register text,
    scale double precision
);

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

-- Populate dimension tables with data from requirements
INSERT INTO machines (id, process_name) VALUES ('source', 'source'), ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('M4', 'M4'), ('M5', 'M5'), ('M6', 'M6'), ('sink', 'sink');

INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES 
('M1', 199.86, 98.77, 1062.58, 5.0, 0.5),
('M2', 220.09, 98.63, 1184.73, 5.49, 0.55),
('M3', 240.01, 99.78, 314.75, 5.99, 0.59),
('M4', 259.99, 98.85, 1246.71, 6.99, 0.69),
('M5', 230.13, 99.51, 2129.84, 6.49, 0.64),
('M6', 209.83, 98.98, 2200.89, 6.0, 0.6);

INSERT INTO buffers (id, capacity, before, after) VALUES 
('B0', 10, 'source', 'M1'),
('B1', 10, 'M1', 'M2'),
('B2', 10, 'M2', 'M3'),
('B3', 10, 'M3', 'M4'),
('B4', 10, 'M4', 'M5'),
('B5', 10, 'M5', 'M6');

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES 
('Avg_Time_per_part_s', 'source', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1.0),
('Availability_%', 'source', 'Availability_%', '%', 'Availability_%', 1.0),
('MTTR_s', 'source', 'MTTR_s', 's', 'MTTR_s', 1.0),
('EnergyIdling', 'source', 'EnergyIdling', 'kWh', 'EnergyIdling', 1.0),
('EnergyWorking', 'source', 'EnergyWorking', 'kWh', 'EnergyWorking', 1.0);

-- Create views over raw_ingest to expose typed fact tables
CREATE VIEW events_view AS SELECT T1.ts, T1.machine_id, T1.reason_code, T1.duration_s, T1.energy_kwh FROM events AS T1 INNER JOIN raw_ingest AS T2 ON T1.machine_id = T2.source;

CREATE VIEW samples_view AS SELECT T1.ts, T1.machine_id, T1.tag, T1.value FROM samples AS T1 INNER JOIN raw_ingest AS T2 ON T1.machine_id = T2.source;