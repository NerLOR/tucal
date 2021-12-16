DROP TABLE IF EXISTS tucal.external_event;
DROP TABLE IF EXISTS tucal.event_history;
DROP TABLE IF EXISTS tucal.event;
DROP TABLE IF EXISTS tucal.group_member;
DROP TABLE IF EXISTS tucal.group;
DROP TRIGGER IF EXISTS t_insert ON tiss.course;
DROP TRIGGER IF EXISTS t_insert ON tiss.group;
DROP TRIGGER IF EXISTS t_insert ON tiss.exam;
DROP TRIGGER IF EXISTS t_insert ON tuwel.course;
DROP TRIGGER IF EXISTS t_insert ON tuwel.course_user;
DROP TRIGGER IF EXISTS t_insert ON tiss.course_user;
DROP TRIGGER IF EXISTS t_insert ON tiss.group_user;
DROP TRIGGER IF EXISTS t_insert ON tiss.exam_user;
DROP TRIGGER IF EXISTS t_delete ON tiss.course_user;
DROP TRIGGER IF EXISTS t_delete ON tiss.group_user;
DROP TRIGGER IF EXISTS t_delete ON tiss.exam_user;

CREATE TABLE tucal.group
(
    group_nr   BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    group_id   TEXT DEFAULT NULL,

    course_nr  TEXT                                NOT NULL,
    semester   TEXT                                NOT NULL,
    group_name TEXT                                NOT NULL,

    CONSTRAINT pk_group PRIMARY KEY (group_nr),
    CONSTRAINT sk_group_id UNIQUE (group_id),
    CONSTRAINT sk_group UNIQUE (course_nr, semester, group_name),
    CONSTRAINT fk_group_course FOREIGN KEY (course_nr, semester) REFERENCES tiss.course (course_nr, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
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

CREATE OR REPLACE FUNCTION tucal.get_group(cnr TEXT, sem TEXT, name TEXT) RETURNS BIGINT AS
$$
BEGIN
    RETURN (SELECT g.group_nr
            FROM tucal.group g
            WHERE (g.course_nr, g.semester, g.group_name) = (cnr, sem, name));
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tiss.course_to_group()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group (course_nr, semester, group_name)
    VALUES (NEW.course_nr, NEW.semester, 'LVA')
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.course
    FOR EACH ROW
EXECUTE PROCEDURE tiss.course_to_group();

CREATE OR REPLACE FUNCTION tiss.group_to_group()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group (course_nr, semester, group_name)
    VALUES (NEW.course_nr, NEW.semester, CONCAT('Gruppe ', NEW.group_name))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.group
    FOR EACH ROW
EXECUTE PROCEDURE tiss.group_to_group();

CREATE OR REPLACE FUNCTION tiss.exam_to_group()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group (course_nr, semester, group_name)
    VALUES (NEW.course_nr, NEW.semester, CONCAT('Prüfung ', NEW.exam_name))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.exam
    FOR EACH ROW
EXECUTE PROCEDURE tiss.exam_to_group();

CREATE OR REPLACE FUNCTION tuwel.course_to_group()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group (course_nr, semester, group_name)
    VALUES (NEW.course_nr, NEW.semester, 'LVA')
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tuwel.course
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.course_to_group();

CREATE OR REPLACE FUNCTION tuwel.course_user_to_member()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group_member (account_nr, group_nr)
    VALUES ((SELECT account_nr
             FROM tucal.account a
                      JOIN tuwel.user u ON u.mnr = a.mnr
             WHERE user_id = NEW.user_id),
            tucal.get_group((SELECT course_nr FROM tuwel.course WHERE course_id = NEW.course_id),
                            (SELECT semester FROM tuwel.course WHERE course_id = NEW.course_id),
                            'LVA'))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tuwel.course_user
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.course_user_to_member();

CREATE TABLE tucal.group_member
(
    account_nr   BIGINT NOT NULL,
    group_nr     BIGINT NOT NULL,

    ignore_until TIMEStAMP WITH TIME ZONE DEFAULT NULL,
    ignore_from  TIMESTAMP WITH TIME ZONE DEFAULT NULL,

    CONSTRAINT pk_group_member PRIMARY KEY (account_nr, group_nr),
    CONSTRAINT fk_group_member_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_group_member_group FOREIGN KEY (group_nr) REFERENCES tucal.group (group_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION tiss.course_user_to_member()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group_member (account_nr, group_nr)
    VALUES ((SELECT account_nr FROM tucal.account WHERE mnr = NEW.mnr),
            tucal.get_group(NEW.course_nr, NEW.semester, 'LVA'))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.course_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.course_user_to_member();

CREATE OR REPLACE FUNCTION tiss.course_user_del_member()
    RETURNS TRIGGER AS
$$
BEGIN
    DELETE
    FROM tucal.group_member
    WHERE (account_nr, group_nr) = ((SELECT account_nr FROM tucal.account WHERE mnr = OLD.mnr),
                                    tucal.get_group(OLD.course_nr, OLD.semester, 'LVA'));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tiss.course_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.course_user_del_member();

CREATE OR REPLACE FUNCTION tiss.group_user_to_member()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group_member (account_nr, group_nr)
    VALUES ((SELECT account_nr FROM tucal.account WHERE mnr = NEW.mnr),
            tucal.get_group(NEW.course_nr, NEW.semester, CONCAT('Gruppe ', NEW.group_name)))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.group_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.group_user_to_member();

CREATE OR REPLACE FUNCTION tiss.group_user_del_member()
    RETURNS TRIGGER AS
$$
BEGIN
    DELETE
    FROM tucal.group_member
    WHERE (account_nr, group_nr) = ((SELECT account_nr FROM tucal.account WHERE mnr = OLD.mnr),
                                    tucal.get_group(OLD.course_nr, OLD.semester, CONCAT('Gruppe ', OLD.group_name)));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tiss.group_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.group_user_del_member();

CREATE OR REPLACE FUNCTION tiss.exam_user_to_member()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group_member (account_nr, group_nr)
    VALUES ((SELECT account_nr FROM tucal.account WHERE mnr = NEW.mnr),
            tucal.get_group(NEW.course_nr, NEW.semester, CONCAT('Prüfung ', NEW.exam_name)))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.exam_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.exam_user_to_member();

CREATE OR REPLACE FUNCTION tiss.exam_user_del_member()
    RETURNS TRIGGER AS
$$
BEGIN
    DELETE
    FROM tucal.group_member
    WHERE (account_nr, group_nr) = ((SELECT account_nr FROM tucal.account WHERE mnr = OLD.mnr),
                                    tucal.get_group(OLD.course_nr, OLD.semester, CONCAT('Prüfung ', OLD.exam_name)));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tiss.exam_user
    FOR EACH ROW
EXECUTE PROCEDURE tiss.exam_user_del_member();


CREATE OR REPLACE VIEW tucal.v_account_group AS
SELECT a.account_nr,
       a.account_id,
       a.mnr,
       a.username,
       g.group_nr,
       g.group_id,
       m.ignore_until,
       m.ignore_from,
       g.course_nr,
       g.semester,
       g.group_name
FROM tucal.v_account a
         LEFT JOIN tucal.group_member m ON m.account_nr = a.account_nr
         LEFT JOIN tucal.group g ON g.group_nr = m.group_nr
ORDER BY a.account_nr;
