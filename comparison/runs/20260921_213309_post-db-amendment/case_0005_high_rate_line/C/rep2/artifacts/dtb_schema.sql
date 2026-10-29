CREATE TABLE tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
);

CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
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

-- Insert dimension data from requirements
INSERT INTO machines VALUES ('M1', 60.0, 99.99, 300.0, 3.0, 0.3);
INSERT INTO machines VALUES ('M2', 80.0, 99.0, 600.0, 5.0, 0.5);
INSERT INTO machines VALUES ('M3', 70.0, 99.0, 600.0, 4.5, 0.45);
INSERT INTO machines VALUES ('M4', 75.0, 99.99, 300.0, 4.0, 0.4);

INSERT INTO buffers VALUES ('B0', 25);
INSERT INTO buffers VALUES ('B1', 10);
INSERT INTO buffers VALUES ('B2', 10);
INSERT INTO buffers VALUES ('B3', 10);

INSERT INTO tag_map VALUES ('inter_arrival_s', 'M1', 'inter_arrival_s', 's', 'inter_arrival_s', 1.0);
INSERT INTO tag_map VALUES ('arrival_time_s', 'M1', 'arrival_time_s', 's', 'arrival_time_s', 1.0);
INSERT INTO tag_map VALUES ('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1.0);
INSERT INTO tag_map VALUES ('availability', 'M1', 'availability', 'pct', 'availability', 1.0);
INSERT INTO tag_map VALUES ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1.0);
INSERT INTO tag_map VALUES ('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1.0);
INSERT INTO tag_map VALUES ('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0);

-- Create views for typed fact tables
CREATE VIEW events_view AS SELECT * FROM events;
CREATE VIEW samples_view AS SELECT * FROM samples;
CREATE VIEW raw_data_view AS SELECT * FROM raw_ingest;