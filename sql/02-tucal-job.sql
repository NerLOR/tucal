DROP VIEW IF EXISTS tucal.v_job;
DROP TABLE IF EXISTS tucal.job;

CREATE TABLE tucal.job
(
    job_nr   BIGINT                   NOT NULL GENERATED ALWAYS AS IDENTITY,
    job_id   TEXT                              DEFAULT NULL,

    name     TEXT,
    pid      INT,
    mnr      INT,

    status   TEXT                     NOT NULL,
    start_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    time     DECIMAL(9, 3)            NOT NULL DEFAULT 0,

    data     JSONB                    NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_job PRIMARY KEY (job_nr),
    CONSTRAINT sk_job_id UNIQUE (job_id),
    CONSTRAINT sk_job_pid UNIQUE (pid)
);

CREATE INDEX idx_mnr ON tucal.job (mnr);
CREATE INDEX idx_status ON tucal.job (status);

CREATE OR REPLACE FUNCTION tucal.update_job_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.job_id = tucal.gen_id(NEW.job_nr, 23424::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_insert
    BEFORE INSERT
    ON tucal.job
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_job_id();

CREATE TRIGGER t_update
    BEFORE UPDATE
    ON tucal.job
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_job_id();

CREATE OR REPLACE VIEW tucal.v_job AS
SELECT job_nr,
       job_id,
       name,
       pid,
       mnr,
       status,
       regexp_replace(
               substr(data ->> 'error'::text, 0, length(data ->> 'error'::text)),
               e'.*\n', '')                        AS error_msg,
       start_ts,
       (data ->> 'eta_ts')::text::timestamptz      AS eta_ts,
       time,
       (data ->> 'remaining')::text::decimal(9, 3) AS time_remaining,
       data
FROM tucal.job
ORDER BY job_nr;
