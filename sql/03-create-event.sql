CREATE TABLE tucal.event
(
    event_nr   BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,

    start_ts   TIMESTAMP WITH TIME ZONE            NOT NULL,
    end_ts     TIMESTAMP WITH TIME ZONE            NOT NULL,

    room_nr    INT                                          DEFAULT NULL,
    course_nr  TEXT                                         DEFAULT NULL,
    semester   TEXT                                         DEFAULT NULL,
    group_name TEXT                                         DEFAULT NULL,
    exam_name  TEXT                                         DEFAULT NULL,

    f_global   BOOLEAN                                      DEFAULT TRUE,
    f_deleted  BOOLEAN                                      DEFAULT FALSE,

    data       JSONB                               NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_event PRIMARY KEY (event_nr),
    CONSTRAINT fk_event_room FOREIGN KEY (room_nr) REFERENCES tucal.room (room_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_group FOREIGN KEY (course_nr, semester, group_name) REFERENCES tiss.group (course_nr, semester, group_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_exam FOREIGN KEY (course_nr, semester, exam_name) REFERENCES tiss.exam (course_nr, semester, exam_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tucal.event_history
(
    event_nr      BIGINT                   NOT NULL,
    event_version INT                      NOT NULL,

    start_ts      TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    end_ts        TIMESTAMP WITH TIME ZONE DEFAULT NULL,

    room_nr       INT                      DEFAULT NULL,
    course_nr     TEXT                     DEFAULT NULL,
    semester      TEXT                     DEFAULT NULL,
    group_name    TEXT                     DEFAULT NULL,
    exam_name     TEXT                     DEFAULT NULL,

    f_global      BOOLEAN                  DEFAULT NULL,
    f_deleted     BOOLEAN                  DEFAULT NULL,

    data          JSONB                    DEFAULT NULL,

    update_ts     TIMESTAMP WITH TIME ZONE NOT NULL GENERATED ALWAYS AS ( current_timestamp ) STORED,

    CONSTRAINT pk_event_history PRIMARY KEY (event_nr, event_version),
    CONSTRAINT fk_event_history_event FOREIGN KEY (event_nr) REFERENCES tucal.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tucal.external_event
(
    source     TEXT                     NOT NULL,
    event_id   TEXT                     NOT NULL,
    event_nr   BIGINT,

    start_ts   TIMESTAMP WITH TIME ZONE NOT NULL,
    end_ts     TIMESTAMP WITH TIME ZONE NOT NULL,

    room_nr    INT                               DEFAULT NULL,
    course_nr  TEXT                              DEFAULT NULL,
    semester   TEXT                              DEFAULT NULL,
    group_name TEXT                              DEFAULT NULL,
    exam_name  TEXT                              DEFAULT NULL,

    f_global   BOOLEAN                           DEFAULT TRUE,
    f_deleted  BOOLEAN                           DEFAULT FALSE,

    data       JSONB                    NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_external_event PRIMARY KEY (source, event_id),
    CONSTRAINT fk_external_event_event FOREIGN KEY (event_nr) REFERENCES tucal.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_room FOREIGN KEY (room_nr) REFERENCES tucal.room (room_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_group FOREIGN KEY (course_nr, semester, group_name) REFERENCES tiss.group (course_nr, semester, group_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_exam FOREIGN KEY (course_nr, semester, exam_name) REFERENCES tiss.exam (course_nr, semester, exam_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE OR REPLACE FUNCTION tucal.insert_external_event()
    RETURNS TRIGGER AS
$$
BEGIN

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_insert
    BEFORE INSERT
    ON tucal.external_event
    FOR EACH ROW
EXECUTE PROCEDURE tucal.insert_external_event();
