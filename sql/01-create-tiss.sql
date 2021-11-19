DROP SCHEMA tiss CASCADE;
CREATE SCHEMA tiss;

CREATE TABLE tiss.user
(
    mnr        INT NOT NULL,

    auth_token TEXT DEFAULT NULL,
    last_sync  TIMESTAMP WITH TIME ZONE,

    CONSTRAINT pk_user PRIMARY KEY (mnr)
);

CREATE TABLE tiss.course_type
(
    type    TEXT NOT NULL CHECK (length(type) = 2),
    name_de TEXT,
    name_en TEXT,

    CONSTRAINT pk_course_type PRIMARY KEY (type)
);

CREATE TABLE tiss.event_type
(
    type    INT NOT NULL CHECK (type >= 0),

    name_de TEXT,
    name_en TEXT,

    CONSTRAINT pk_event_type PRIMARY KEY (type)
);

CREATE TABLE tiss.room
(
    code      TEXT NOT NULL,

    name      TEXT NOT NULL,
    name_full TEXT NOT NULL,

    CONSTRAINT pk_room PRIMARY KEY (code)
);

CREATE TABLE tiss.course_def
(
    course_nr TEXT NOT NULL CHECK (course_nr ~ '[0-9]{3}[0-9A-Z]{3}'),

    name_de   TEXT,
    name_en   TEXT,
    type      TEXT NOT NULL,

    CONSTRAINT pk_course_def PRIMARY KEY (course_nr),
    CONSTRAINT fk_course_def_course_type FOREIGN KEY (type) REFERENCES tiss.course_type (type)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tiss.course
(
    course_nr TEXT          NOT NULL,
    semester  TEXT          NOT NULL CHECK (semester ~ '[0-9]{4}[WS]'),

    ects      DECIMAL(4, 1) NOT NULL,

    CONSTRAINT pk_course PRIMARY KEY (course_nr, semester),
    CONSTRAINT fk_course_course_def FOREIGN KEY (course_nr) REFERENCES tiss.course_def (course_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tiss.group
(
    course_nr          TEXT NOT NULL,
    semester           TEXT NOT NULL,
    group_name         TEXT NOT NULL,

    application_start  TIMESTAMP WITH TIME ZONE,
    application_end    TIMESTAMP WITH TIME ZONE,
    deregistration_end TIMESTAMP WITH TIME ZONE,

    CONSTRAINT pk_group PRIMARY KEY (course_nr, semester, group_name),
    CONSTRAINT fk_group_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tiss.exam
(
    course_nr          TEXT NOT NULL,
    semester           TEXT NOT NULL,
    exam_name          TEXT NOT NULL,

    application_start  TIMESTAMP WITH TIME ZONE,
    application_end    TIMESTAMP WITH TIME ZONE,
    deregistration_end TIMESTAMP WITH TIME ZONE,

    CONSTRAINT pk_exam PRIMARY KEY (course_nr, semester, exam_name),
    CONSTRAINT fk_exam_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tiss.event
(
    event_nr    INT GENERATED ALWAYS AS IDENTITY NOT NULL,

    event_id    INT,
    type        INT                              NOT NULL,

    course_nr   TEXT,
    semester    TEXT,
    room_code   TEXT,
    group_name  TEXT,
    exam_name   TEXT,

    start_ts    TIMESTAMP WITH TIME ZONE         NOT NULL,
    end_ts      TIMESTAMP WITH TIME ZONE         NOT NULL,
    access_ts   TIMESTAMP WITH TIME ZONE,

    name        TEXT                             NOT NULL,
    description TEXT,

    livestream  BOOLEAN,
    online_only BOOLEAN,
    location    TEXT,

    CONSTRAINT pk_event PRIMARY KEY (event_nr),
    CONSTRAINT sk_event_id UNIQUE (event_id),
    CONSTRAINT fk_event_type FOREIGN KEY (type) REFERENCES tiss.event_type (type)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_course_def FOREIGN KEY (course_nr) REFERENCES tiss.course_def (course_nr)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_event_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_event_room FOREIGN KEY (room_code) REFERENCES tiss.room (code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_group FOREIGN KEY (course_nr, semester, group_name) REFERENCES tiss.group (course_nr, semester, group_name)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_event_exam FOREIGN KEY (course_nr, semester, exam_name) REFERENCES tiss.exam (course_nr, semester, exam_name)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE INDEX start_ts ON tiss.event (start_ts);
CREATE INDEX end_ts ON tiss.event (end_ts);

CREATE TABLE tiss.event_user
(
    event_nr INT NOT NULL,
    mnr      INT NOT NULL,

    CONSTRAINT pk_event_user PRIMARY KEY (event_nr, mnr),
    CONSTRAINT fk_event_user_event FOREIGN KEY (event_nr) REFERENCES tiss.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_event_user_user FOREIGN KEY (mnr) REFERENCES tiss.user (mnr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tiss.course_user
(
    course_nr TEXT NOT NULL,
    semester  TEXT NOT NULL,
    mnr       INT  NOT NULL,

    CONSTRAINT pk_course_user PRIMARY KEY (course_nr, semester, mnr),
    CONSTRAINT fk_course_user_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_course_user_user FOREIGN KEY (mnr) REFERENCES tiss.user (mnr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tiss.group_user
(
    course_nr  TEXT NOT NULL,
    semester   TEXT NOT NULL,
    group_name TEXT NOT NULL,
    mnr        INT  NOT NULL,

    CONSTRAINT pk_group_user PRIMARY KEY (course_nr, semester, group_name, mnr),
    CONSTRAINT fk_group_user_group FOREIGN KEY (course_nr, semester, group_name) REFERENCES tiss.group (course_nr, semester, group_name)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_group_user_user FOREIGN KEY (mnr) REFERENCES tiss.user (mnr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tiss.exam_user
(
    course_nr TEXT NOT NULL,
    semester  TEXT NOT NULL,
    exam_name TEXT NOT NULL,
    mnr       INT  NOT NULL,

    CONSTRAINT pk_exam_user PRIMARY KEY (course_nr, semester, exam_name, mnr),
    CONSTRAINT fk_exam_user_exam FOREIGN KEY (course_nr, semester, exam_name) REFERENCES tiss.exam (course_nr, semester, exam_name)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_exam_user_user FOREIGN KEY (mnr) REFERENCES tiss.user (mnr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
