\c postgres
DROP DATABASE IF EXISTS tucal;
CREATE DATABASE tucal WITH ENCODING 'UTF8';
\c tucal

CREATE TABLE area
(
    area_id     TEXT NOT NULL CHECK (length(area_id) = 1),
    area_name   TEXT,
    area_suffix TEXT    DEFAULT NULL,
    in_use      BOOLEAN DEFAULT TRUE,

    CONSTRAINT pk_area PRIMARY KEY (area_id)
);

CREATE TABLE building
(
    area_id           TEXT NOT NULL,
    local_id          TEXT NOT NULL CHECK (length(local_id) = 1),

    building_name     TEXT,
    building_suffix   TEXT DEFAULT NULL,
    building_alt_name TEXT DEFAULT NULL,
    object_nr         INT  DEFAULT NULL,
    address           TEXT DEFAULT NULL,

    CONSTRAINT pk_building PRIMARY KEY (area_id, local_id),
    CONSTRAINT fk_building_area FOREIGN KEY (area_id) REFERENCES area (area_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE OR REPLACE VIEW v_building AS
SELECT CONCAT(a.area_id, b.local_id) AS building_id,
       building_name,
       building_suffix,
       building_alt_name,
       object_nr,
       address,
       a.area_name,
       a.area_suffix,
       a.in_use
FROM building b
         JOIN area a ON b.area_id = a.area_id;

CREATE TABLE room
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
    CONSTRAINT fk_room_location_building FOREIGN KEY (area_id, building_id) REFERENCES building (area_id, local_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE room_location
(
    room_nr    INT  NOT NULL,

    floor_nr   TEXT NOT NULL CHECK (length(floor_nr) = 2),
    local_code TEXT NOT NULL CHECK (length(local_code) > 1),

    CONSTRAINT pk_room_location PRIMARY KEY (room_nr, floor_nr, local_code),
    CONSTRAINT fk_room_location_room FOREIGN KEY (room_nr) REFERENCES room (room_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE VIEW v_room AS
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
FROM room r
         LEFT JOIN room_location rl ON r.room_nr = rl.room_nr
GROUP BY r.room_nr
ORDER BY r.room_nr;
