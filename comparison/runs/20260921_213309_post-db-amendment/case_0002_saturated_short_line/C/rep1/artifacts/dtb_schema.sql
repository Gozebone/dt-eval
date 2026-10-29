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
    name text
);

CREATE TABLE buffers (
    id text PRIMARY KEY,
    capacity int,
    before text,
    after text
);

CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s int,
    availability_pct int,
    mttr_s int,
    power_working_kw double precision,
    power_idle_kw double precision
);

CREATE TABLE tag_map (
    tag_id text PRIMARY KEY,
    machine_id text,
    signal text,
    unit text,
    register text,
    scale double precision
);

-- Insert machines from requirements
INSERT INTO machines (id, name) VALUES ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('B0', 'B0'), ('B1', 'B1'), ('B2', 'B2');

-- Insert buffers from requirements
INSERT INTO buffers (id, capacity, before, after) VALUES ('B0', 15, 'source', 'M1'), ('B1', 5, 'M1', 'M2'), ('B2', 5, 'M2', 'M3');

-- Insert stations from requirements
INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES 
('M1', 90, 100, 600, 3.0, 0.3),
('M2', 70, 99, 900, 4.5, 0.45),
('M3', 110, 100, 1200, 6.0, 0.6);

-- Insert tag_map entries from requirements
INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES 
('Avg_Time_per_part_s', 'M1', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
('Availability_%', 'M1', 'Availability_%', '%', 'Availability_%', 1),
('MTTR_s', 'M1', 'MTTR_s', 's', 'MTTR_s', 1),
('EnergyIdling', 'M1', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
('EnergyWorking', 'M1', 'EnergyWorking', 'kW', 'EnergyWorking', 1);

-- Create fact table for events
CREATE TABLE events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text,
    duration_s double precision,
    energy_kwh double precision
);

-- Create fact table for samples
CREATE TABLE samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision
);

-- Add indexes for performance
CREATE INDEX idx_events_machine_time ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts);