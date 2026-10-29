CREATE TABLE machines (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
);

INSERT INTO machines (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw)
VALUES ('M1', 200, 97, 900, 5.0, 0.5),
      ('M2', 220, 97, 1000, 5.5, 0.55),
      ('M3', 240, 96, 1200, 6.0, 0.6),
      ('M4', 260, 96, 1400, 7.0, 0.7),
      ('M5', 230, 97, 1100, 6.5, 0.65),
      ('M6', 210, 97, 1000, 6.0, 0.6);

CREATE TABLE buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
);

INSERT INTO buffers (id, capacity)
VALUES ('B0', 10),
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

INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
VALUES ('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1),
      ('process_time_s', 'M2', 'process_time_s', 's', 'process_time_s', 1),
      ('process_time_s', 'M3', 'process_time_s', 's', 'process_time_s', 1),
      ('process_time_s', 'M4', 'process_time_s', 's', 'process_time_s', 1),
      ('process_time_s', 'M5', 'process_time_s', 's', 'process_time_s', 1),
      ('process_time_s', 'M6', 'process_time_s', 's', 'process_time_s', 1),
      ('availability_pct', 'M1', 'availability_pct', '%', 'availability_pct', 1),
      ('availability_pct', 'M2', 'availability_pct', '%', 'availability_pct', 1),
      ('availability_pct', 'M3', 'availability_pct', '%', 'availability_pct', 1),
      ('availability_pct', 'M4', 'availability_pct', '%', 'availability_pct', 1),
      ('availability_pct', 'M5', 'availability_pct', '%', 'availability_pct', 1),
      ('availability_pct', 'M6', 'availability_pct', '%', 'availability_pct', 1),
      ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
      ('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
      ('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
      ('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1),
      ('mttr_s', 'M5', 'mttr_s', 's', 'mttr_s', 1),
      ('mttr_s', 'M6', 'mttr_s', 's', 'mttr_s', 1),
      ('power', 'M1', 'power', 'kW', 'power', 1),
      ('power', 'M2', 'power', 'kW', 'power', 1),
      ('power', 'M3', 'power', 'kW', 'power', 1),
      ('power', 'M4', 'power', 'kW', 'power', 1),
      ('power', 'M5', 'power', 'kW', 'power', 1),
      ('power', 'M6', 'power', 'kW', 'power', 1);

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
    PRIMARY KEY (machine_id, ts)
);

CREATE TABLE samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION,
    PRIMARY KEY (machine_id, ts, tag)
);

CREATE INDEX idx_events_machine_time ON events (machine_id, ts);
CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts);

CREATE TABLE ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
);