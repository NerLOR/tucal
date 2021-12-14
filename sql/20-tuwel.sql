DROP SCHEMA IF EXISTS tuwel CASCADE;
CREATE SCHEMA tuwel;

CREATE TABLE tuwel.user
(
    user_id    INT NOT NULL,
    mnr        INT NOT NULL,

    auth_token TEXT DEFAULT NULL,

    CONSTRAINT pk_user PRIMARY KEY (user_id),
    CONSTRAINT sk_user_mnr UNIQUE (mnr)
);

CREATE TABLE tuwel.course
(
    course_id INT  NOT NULL,

    course_nr TEXT NOT NULL CHECK (course_nr ~ '[0-9]{3}[0-9A-Z]{3}'),
    semester  TEXT NOT NULL CHECK (semester ~ '[0-9]{4}[WS]'),

    lti_id    INT,

    name      TEXT NOT NULL,
    suffix    TEXT,
    short     TEXT NOT NULL,

    CONSTRAINT pk_course PRIMARY KEY (course_id),
    CONSTRAINT sk_course UNIQUE (course_nr, semester),
    CONSTRAINT sk_course_short UNIQUE (short)
);

CREATE TABLE tuwel.event
(
    event_id    BIGINT NOT NULL,
    course_id   INT    NOT NULL,

    start_ts    TIMESTAMP WITH TIME ZONE,
    end_ts      TIMESTAMP WITH TIME ZONE,

    access_ts   timestamp WITH TIME ZONE,
    mod_ts      TIMESTAMP WITH TIME ZONE,

    name        TEXT   NOT NULL,
    description TEXT,

    CONSTRAINT pk_event PRIMARY KEY (event_id),
    CONSTRAINT fk_event_course FOREIGN KEY (course_id) REFERENCES tuwel.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_course ON tuwel.event (course_id);
CREATE INDEX idx_start ON tuwel.event (start_ts);
CREATE INDEX idx_end ON tuwel.event (end_ts);

CREATE TABLE tuwel.event_user
(
    event_id BIGINT NOT NULL,
    user_id  INT    NOT NULL,

    CONSTRAINT pk_event_user PRIMARY KEY (event_id, user_id),
    CONSTRAINT fk_event_user_event FOREIGN KEY (event_id) REFERENCES tuwel.event (event_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_event_user_user FOREIGN KEY (user_id) REFERENCES tuwel.user (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tuwel.course_user
(
    course_id INT NOT NULL,
    user_id   INT NOT NULL,

    CONSTRAINT pk_course_user PRIMARY KEY (course_id, user_id),
    CONSTRAINT fk_course_user_course FOREIGN KEY (course_id) REFERENCES tuwel.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_course_user_user FOREIGN KEY (user_id) REFERENCES tuwel.user (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
