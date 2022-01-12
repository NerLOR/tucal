DROP TABLE IF EXISTS tucal.external_event;
DROP TABLE IF EXISTS tucal.event_history;
DROP TABLE IF EXISTS tucal.event;
DROP VIEW IF EXISTS tucal.v_account_group;
DROP TABLE IF EXISTS tucal.group_member;
DROP TABLE IF EXISTS tucal.group_link;
DROP TABLE IF EXISTS tucal.group;
DROP FUNCTION IF EXISTS tucal.get_group;

CREATE TABLE tucal.group
(
    group_nr   BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    group_id   TEXT DEFAULT NULL,

    group_name TEXT                                NOT NULL,

    CONSTRAINT pk_group PRIMARY KEY (group_nr),
    CONSTRAINT sk_group_id UNIQUE (group_id)
);

CREATE OR REPLACE FUNCTION tucal.group_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.group_id = tucal.gen_id(NEW.group_nr, 14379::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    BEFORE INSERT
    ON tucal.group
    FOR EACH ROW
EXECUTE PROCEDURE tucal.group_id();


CREATE TABLE tucal.group_link
(
    group_nr  BIGINT NOT NULL,

    course_nr TEXT   NOT NULL,
    semester  TEXT   NOT NULL,
    name      TEXT   NOT NULL,

    CONSTRAINT pk_group_link PRIMARY KEY (group_nr),
    CONSTRAINT sk_group_link UNIQUE (course_nr, semester, name),
    CONSTRAINT fk_group_link_group FOREIGN KEY (group_nr) REFERENCES tucal.group (group_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_group_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE tucal.group_member
(
    account_nr   BIGINT NOT NULL,
    group_nr     BIGINT NOT NULL,

    ignore_until TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    ignore_from  TIMESTAMP WITH TIME ZONE DEFAULT NULL,

    CONSTRAINT pk_group_member PRIMARY KEY (account_nr, group_nr),
    CONSTRAINT fk_group_member_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_group_member_group FOREIGN KEY (group_nr) REFERENCES tucal.group (group_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE VIEW tucal.v_account_group AS
SELECT a.account_nr,
       a.account_id,
       a.mnr,
       a.username,
       g.group_nr,
       g.group_id,
       m.ignore_until,
       m.ignore_from,
       g.group_name,
       l.course_nr,
       l.semester,
       l.name
FROM tucal.v_account a
         LEFT JOIN tucal.group_member m ON m.account_nr = a.account_nr
         LEFT JOIN tucal.group g ON g.group_nr = m.group_nr
         LEFT JOIN tucal.group_link l ON l.group_nr = g.group_nr
ORDER BY a.account_nr, l.semester DESC, l.course_nr, g.group_name;


CREATE OR REPLACE FUNCTION tucal.get_group(cnr TEXT, sem TEXT, gname TEXT) RETURNS BIGINT AS
$$
BEGIN
    RETURN (SELECT l.group_nr
            FROM tucal.group_link l
            WHERE (l.course_nr, l.semester, l.name) = (cnr, sem, gname));
END;
$$ LANGUAGE plpgsql;


INSERT INTO tucal.group (group_name)
SELECT CONCAT(course_nr, '-', semester, ' LVA')
FROM tiss.course;

INSERT INTO tucal.group_link (group_nr, course_nr, semester, name)
SELECT g.group_nr, course_nr, semester, 'LVA'
FROM tiss.course c
         JOIN tucal.group g ON g.group_name = CONCAT(course_nr, '-', semester, ' LVA');
