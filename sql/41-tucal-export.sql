DROP TABLE IF EXISTS tucal.calendar_export;

CREATE TABLE tucal.calendar_export
(
    export_nr   BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    export_id   TEXT                                NOT NULL DEFAULT NULL,
    token       TEXT                                NOT NULL CHECK (token ~ '[0-9A-Za-z]{24}'),

    account_nr  BIGINT                              NOT NULL,

    subject_mnr INT                                          DEFAULT NULL,

    create_ts   TIMESTAMP WITH TIME ZONE            NOT NULL DEFAULT current_timestamp,
    active_ts   TIMESTAMP WITH TIME ZONE            NOT NULL DEFAULT current_timestamp,

    options     JSONB                               NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_calendar_export PRIMARY KEY (export_nr),
    CONSTRAINT sk_calendar_export UNIQUE (export_id),
    CONSTRAINT sk_calendar_export_token UNIQUE (token),
    CONSTRAINT c_calendar_export_subject CHECK (subject_mnr IS NOT NULL),
    CONSTRAINT fk_calendar_export_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION tucal.calendar_export_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.export_id = tucal.gen_id(NEW.export_nr, 23921::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert_id
    BEFORE INSERT
    ON tucal.calendar_export
    FOR EACH ROW
EXECUTE PROCEDURE tucal.calendar_export_id();
