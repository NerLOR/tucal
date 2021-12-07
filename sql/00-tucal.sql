-- \c postgres
-- DROP DATABASE IF EXISTS tucal;
-- CREATE DATABASE tucal WITH ENCODING 'UTF8';
-- \c tucal

DROP SCHEMA tucal CASCADE;
CREATE SCHEMA tucal;

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION tucal.gen_id(nr BIGINT, key_nr SMALLINT) RETURNS TEXT AS
$$
DECLARE
    alpha  TEXT   = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ';
    len    INT    = LENGTH(alpha);
    id     TEXT   = '';
    init   BIGINT = b'1010010110010110011010011010010110100101100101100110100110100101'::int8;
    new_nr BIGINT = 0;
BEGIN
    FOR i IN 0 .. 63
        LOOP
            new_nr = new_nr | (((int8and(nr, 1 << i) >> i) << (63 - i)));
        END LOOP;
    new_nr = int8xor(new_nr, init);
    new_nr = int8xor(new_nr, (key_nr::int8 << 48) | (key_nr::int8 << 32) | (key_nr::int8 << 16) | (key_nr::int8));

    WHILE new_nr != 0
        LOOP
            id = CONCAT(SUBSTRING(alpha, (((new_nr % len) + len) % len)::int, 1), id);
            new_nr = new_nr / len;
        END LOOP;
    RETURN LPAD(id, 11, '1');
END;
$$ LANGUAGE plpgsql;

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
