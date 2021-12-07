
CREATE TABLE tucal.job
(
    job_nr   BIGINT                   NOT NULL GENERATED ALWAYS AS IDENTITY,
    job_id   TEXT,

    name     TEXT                     NOT NULL,
    pid      INT,
    mnr      INT,

    status   TEXT                     NOT NULL,
    data     JSONB                    NOT NULL DEFAULT '{}'::jsonb,
    start_ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    time     INT                      NOT NULL DEFAULT 0,

    CONSTRAINT pk_job PRIMARY KEY (job_nr),
    CONSTRAINT sk_job_id UNIQUE (job_id),
    CONSTRAINT sk_job_pid UNIQUE (pid)
);

CREATE OR REPLACE FUNCTION tucal.update_job_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.job_id = tucal.gen_id(NEW.job_nr, 23424);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_insert
    AFTER INSERT
    ON tucal.job
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_job_id();

CREATE TRIGGER t_update
    AFTER UPDATE
    ON tucal.job
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_job_id();
