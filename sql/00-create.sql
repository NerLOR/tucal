-- \c postgres
-- DROP DATABASE IF EXISTS tucal;
-- CREATE DATABASE tucal WITH ENCODING 'UTF8';
-- \c tucal

CREATE SCHEMA tucal;

CREATE SCHEMA tiss;

CREATE SCHEMA tuwel;

CREATE SCHEMA tuwien;

CREATE TABLE tucal.area
(
    area_id     TEXT NOT NULL CHECK (length(area_id) = 1),
    area_name   TEXT,
    area_suffix TEXT    DEFAULT NULL,
    in_use      BOOLEAN DEFAULT TRUE,

    CONSTRAINT pk_area PRIMARY KEY (area_id)
);

CREATE TABLE tucal.building
(
    area_id           TEXT NOT NULL,
    local_id          TEXT NOT NULL CHECK (length(local_id) = 1),

    building_name     TEXT,
    building_suffix   TEXT DEFAULT NULL,
    building_alt_name TEXT DEFAULT NULL,
    object_nr         INT  DEFAULT NULL,
    address           TEXT DEFAULT NULL,

    CONSTRAINT pk_building PRIMARY KEY (area_id, local_id),
    CONSTRAINT fk_building_area FOREIGN KEY (area_id) REFERENCES tucal.area (area_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE OR REPLACE VIEW tucal.v_building AS
SELECT CONCAT(a.area_id, b.local_id) AS building_id,
       building_name,
       building_suffix,
       building_alt_name,
       object_nr,
       address,
       a.area_name,
       a.area_suffix,
       a.in_use
FROM tucal.building b
         JOIN tucal.area a ON b.area_id = a.area_id;

CREATE TABLE tucal.room
(
    room_nr         INT  NOT NULL,

    area_id         TEXT NOT NULL,
    building_id     TEXT NOT NULL,

    tiss_code       TEXT DEFAULT NULL,

    room_name       TEXT DEFAULT NULL,
    room_suffix     TEXT DEFAULT NULL,
    room_name_short TEXT DEFAULT NULL,
    room_alt_name   TEXT DEFAULT NULL,
    area            INT  DEFAULT NULL,
    capacity        INT  DEFAULT NULL,

    tiss_name       TEXT DEFAULT NULL,
    tiss_name_full  TEXT DEFAULT NULL,

    CONSTRAINT pk_room PRIMARY KEY (room_nr),
    CONSTRAINT sk_room_tiss UNIQUE (tiss_code),
    CONSTRAINT sk_room_name UNIQUE (room_name),
    CONSTRAINT sk_room_name_short UNIQUE (room_name_short),
    CONSTRAINT fk_room_location_building FOREIGN KEY (area_id, building_id) REFERENCES tucal.building (area_id, local_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tucal.room_location
(
    room_nr    INT  NOT NULL,

    floor_nr   TEXT NOT NULL CHECK (length(floor_nr) = 2),
    local_code TEXT NOT NULL CHECK (length(local_code) > 1),

    CONSTRAINT pk_room_location PRIMARY KEY (room_nr, floor_nr, local_code),
    CONSTRAINT fk_room_location_room FOREIGN KEY (room_nr) REFERENCES tucal.room (room_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE VIEW tucal.v_room AS
SELECT r.room_nr,
       string_agg(CONCAT(r.area_id, r.building_id, rl.floor_nr, rl.local_code), '/')           AS room_code,
       string_agg(CONCAT(r.area_id, r.building_id, ' ', rl.floor_nr, ' ', rl.local_code), '/') AS room_code_long,
       string_agg(DISTINCT CONCAT(r.area_id, r.building_id), '/')                              AS building_id,
       string_agg(DISTINCT r.tiss_code, '/')                                                   AS tiss_code,
       r.tiss_name,
       r.room_name,
       r.room_suffix,
       r.room_name_short,
       r.room_alt_name,
       r.area,
       r.capacity
FROM tucal.room r
         LEFT JOIN tucal.room_location rl ON r.room_nr = rl.room_nr
GROUP BY r.room_nr
ORDER BY r.room_nr;

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

CREATE TABLE tucal.event_type
(
    type    TEXT NOT NULL CHECK (length(type) = 2),

    name_de TEXT,
    name_en TEXT,

    CONSTRAINT pk_event_type PRIMARY KEY (type)
);

CREATE TABLE tiss.course
(
    semester  TEXT          NOT NULL CHECK (semester ~ '[0-9]{4}[WS]'),
    course_id TEXT          NOT NULL CHECK (course_id ~ '[0-9]{3}[0-9A-Z]{3}'),

    name_de   TEXT,
    name_en   TEXT,
    type      TEXT          NOT NULL,
    ects      DECIMAL(4, 1) NOT NULL,

    CONSTRAINT pk_course PRIMARY KEY (semester, course_id),
    CONSTRAINT fk_course_course_type FOREIGN KEY (type) REFERENCES tiss.course_type (type)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
