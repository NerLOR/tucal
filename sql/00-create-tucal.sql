-- \c postgres
-- DROP DATABASE IF EXISTS tucal;
-- CREATE DATABASE tucal WITH ENCODING 'UTF8';
-- \c tucal

DROP SCHEMA tucal CASCADE;
CREATE SCHEMA tucal;

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE tucal.account
(
    account_nr    INT                      NOT NULL GENERATED ALWAYS AS IDENTITY,
    mnr           INT                      NOT NULL,
    username      CITEXT                   NOT NULL CHECK (username ~ '[[:alpha:]][[:alnum:]_ -]{1,30}[[:alnum:]]'),
    email_address CITEXT                            DEFAULT NULL CHECK (email_address ~ '[^@]+@([a-z0-9_-]+\.)+[a-z]{2,}'),

    verified      BOOLEAN                  NOT NULL DEFAULT FALSE,
    avatar_uri    TEXT                              DEFAULT NULL,

    create_ts     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    sync_ts       TIMESTAMP WITH TIME ZONE          DEFAULT NULL,

    options       JSONB                    NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_account PRIMARY KEY (account_nr),
    CONSTRAINT sk_account_mnr UNIQUE (mnr),
    CONSTRAINT sk_account_email UNIQUE (email_address),
    CONSTRAINT sk_account_username UNIQUE (username)
);

CREATE OR REPLACE VIEW tucal.v_account AS
SELECT a.account_nr,
       a.mnr,
       LPAD(a.mnr::text, 8, '0') AS mnr_normal,
       a.username,
       CONCAT('e', LPAD(a.mnr::text, 8, '0'), '@student.tuwien.ac.at') AS email_address_1,
       a.email_address                                                 AS email_address_2,
       a.verified,
       a.avatar_uri,
       a.create_ts,
       a.sync_ts,
       a.options
FROM tucal.account a;

CREATE TABLE tucal.session
(
    session_nr BIGINT                   NOT NULL GENERATED ALWAYS AS IDENTITY,
    token      TEXT                     NOT NULL CHECK (token ~ '[0-9A-Za-z]{64}'),

    account_nr INT                               DEFAULT NULL,
    options    JSONB                    NOT NULL DEFAULT '{}'::jsonb,

    create_ts  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_ts    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    CONSTRAINT pk_sessoin PRIMARY KEY (session_nr),
    CONSTRAINT sk_session_token UNIQUE (token),
    CONSTRAINT fk_session_accout FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE OR REPLACE VIEW tucal.v_session AS
SELECT s.session_nr,
       s.token,
       s.options   AS session_opts,
       a.account_nr,
       a.mnr,
       a.mnr_normal,
       a.username,
       a.email_address_1,
       a.email_address_2,
       a.verified,
       a.avatar_uri,
       a.create_ts AS account_create_ts,
       a.options   AS account_opts
FROM tucal.session s
         LEFT JOIN tucal.v_account a ON a.account_nr = s.account_nr;

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

CREATE TABLE tucal.lecture_tube
(
    room_nr    INT  NOT NULL,
    floor_nr   TEXT NOT NULL,
    local_code TEXT NOT NULL,

    lt_name    TEXT NOT NULL CHECK (lt_name ~ '[a-z0-9-]{6,}'),

    CONSTRAINT pk_lecture_tube PRIMARY KEY (room_nr),
    CONSTRAINT sk_lecture_tube_name UNIQUE (lt_name),
    CONSTRAINT fk_lecture_tube_room_location FOREIGN KEY (room_nr, floor_nr, local_code) REFERENCES tucal.room_location (room_nr, floor_nr, local_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE VIEW tucal.v_room AS
SELECT r.room_nr,
       string_agg(CONCAT(r.area_id, r.building_id, rl.floor_nr, rl.local_code), '/') AS room_code,
       string_agg(CONCAT(r.area_id, r.building_id, ' ', rl.floor_nr, ' ', rl.local_code),
                  '/')                                                               AS room_code_long,
       string_agg(DISTINCT CONCAT(r.area_id, r.building_id), '/')                    AS building_id,
       string_agg(DISTINCT r.tiss_code, '/')                                         AS tiss_code,
       r.room_name,
       r.room_suffix,
       r.room_name_short,
       r.room_alt_name,
       REGEXP_REPLACE(
               REGEXP_REPLACE(
                       CONCAT(r.room_name, ' ', r.room_suffix),
                       '[ /.()+-]+', '-', 'g'),
               '^-+|-+$', '', 'g')                                                   AS room_name_normal,
       r.area,
       r.capacity
FROM tucal.room r
         LEFT JOIN tucal.room_location rl ON r.room_nr = rl.room_nr
GROUP BY r.room_nr
ORDER BY r.room_nr;

DROP VIEW tucal.v_lecture_tube;
CREATE OR REPLACE VIEW tucal.v_lecture_tube AS
SELECT lt.room_nr,
       CONCAT(r.area_id, r.building_id, lt.floor_nr, lt.local_code)        AS room_code,
       lower(CONCAT(r.area_id, r.building_id, lt.floor_nr, lt.local_code)) AS room_code_lower,
       lt.lt_name,
       r.room_name,
       r.room_suffix,
       r.room_name_short,
       r.room_alt_name
FROM tucal.lecture_tube lt
         JOIN tucal.room r ON r.room_nr = lt.room_nr
ORDER BY lt.room_nr;

CREATE TABLE tucal.event_type
(
    type    TEXT NOT NULL CHECK (length(type) = 2),

    name_de TEXT,
    name_en TEXT,

    CONSTRAINT pk_event_type PRIMARY KEY (type)
);

CREATE TABLE tucal.course_acronym
(
    course_nr TEXT NOT NULL CHECK (course_nr ~ '[0-9]{3}[0-9A-Z]{3}'),
    program   TEXT DEFAULT NULL,
    short     TEXT,
    acronym_1 TEXT,
    acronym_2 TEXT,

    CONSTRAINT pk_course_acronym PRIMARY KEY (course_nr)
);
