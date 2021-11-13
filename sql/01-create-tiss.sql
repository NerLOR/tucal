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

CREATE TABLE tiss.course
(
    course_nr TEXT          NOT NULL CHECK (course_nr ~ '[0-9]{3}[0-9A-Z]{3}'),
    semester  TEXT          NOT NULL CHECK (semester ~ '[0-9]{4}[WS]'),

    name_de   TEXT,
    name_en   TEXT,
    type      TEXT          NOT NULL,
    ects      DECIMAL(4, 1) NOT NULL,

    CONSTRAINT pk_course PRIMARY KEY (course_nr, semester),
    CONSTRAINT fk_course_course_type FOREIGN KEY (type) REFERENCES tiss.course_type (type)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tiss.event
(
    tucal_nr    INT GENERATED ALWAYS AS IDENTITY NOT NULL,

    event_id    INT,
    event_uid   UUID,
    type        INT                              NOT NULL,

    course_nr   TEXT,
    semester    TEXT,
    room_code   TEXT,

    start_ts    TIMESTAMP WITH TIME ZONE         NOT NULL,
    end_ts      TIMESTAMP WITH TIME ZONE         NOT NULL,
    access_ts   TIMESTAMP WITH TIME ZONE,

    name        TEXT                             NOT NULL,
    description TEXT,

    CONSTRAINT pk_event PRIMARY KEY (tucal_nr),
    CONSTRAINT sk_event_id UNIQUE (event_id),
    CONSTRAINT sk_event_uid UNIQUE (event_uid),
    CONSTRAINT fk_event_type FOREIGN KEY (type) REFERENCES tiss.event_type (type)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_event_room FOREIGN KEY (room_code) REFERENCES tiss.room (code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX start_ts ON tiss.event (start_ts);
