DROP SCHEMA IF EXISTS tuwel CASCADE;
CREATE SCHEMA tuwel;

CREATE TABLE tuwel.user
(
    user_id    BIGINT NOT NULL,
    mnr        INT    NOT NULL,

    auth_token TEXT DEFAULT NULL,

    CONSTRAINT pk_user PRIMARY KEY (user_id),
    CONSTRAINT sk_user_mnr UNIQUE (mnr)
);

CREATE TABLE tuwel.course
(
    course_id BIGINT NOT NULL,

    course_nr TEXT CHECK (course_nr ~ '[0-9]{3}[0-9A-Z]{3}'),
    semester  TEXT CHECK (semester ~ '[0-9]{4}[WS]'),

    lti_id    BIGINT,

    name      TEXT   NOT NULL,
    suffix    TEXT,
    short     TEXT   NOT NULL,

    CONSTRAINT pk_course PRIMARY KEY (course_id),
    CONSTRAINT sk_course_short UNIQUE (short)
);

CREATE TABLE tuwel.group
(
    group_id        BIGINT NOT NULL,
    course_id       BIGINT NOT NULL,
    name            TEXT   NOT NULL,
    name_normalized TEXT   NOT NULL,

    CONSTRAINT pk_group PRIMARY KEY (group_id),
    CONSTRAINT fk_group_course FOREIGN KEY (course_id) REFERENCES tuwel.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tuwel.group_user
(
    group_id BIGINT NOT NULL,
    user_id  BIGINT NOT NULL,

    CONSTRAINT pk_group_user PRIMARY KEY (group_id, user_id),
    CONSTRAINT fk_group_user_group FOREIGN KEY (group_id) REFERENCES tuwel.group (group_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_group_user_user FOREIGN KEY (user_id) REFERENCES tuwel.user (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tuwel.event
(
    event_id         BIGINT NOT NULL,
    course_id        BIGINT NOT NULL,

    start_ts         TIMESTAMPTZ,
    end_ts           TIMESTAMPTZ,
    access_ts        TIMESTAMPTZ,
    mod_ts           TIMESTAMPTZ,

    name             TEXT   NOT NULL,
    description      TEXT DEFAULT NULL,
    description_html TEXT DEFAULT NULL,
    url              TEXT DEFAULT NULL,
    location         TEXT DEFAULT NULL,

    module_name      TEXT DEFAULT NULL,
    component        TEXT DEFAULT NULL,
    event_type       TEXT DEFAULT NULL,

    f_action_event   BOOL DEFAULT NULL,
    f_course_event   BOOL DEFAULT NULL,
    f_category_event BOOL DEFAULT NULL,

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
    user_id  BIGINT NOT NULL,

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
    course_id BIGINT NOT NULL,
    user_id   BIGINT NOT NULL,

    CONSTRAINT pk_course_user PRIMARY KEY (course_id, user_id),
    CONSTRAINT fk_course_user_course FOREIGN KEY (course_id) REFERENCES tuwel.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_course_user_user FOREIGN KEY (user_id) REFERENCES tuwel.user (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
