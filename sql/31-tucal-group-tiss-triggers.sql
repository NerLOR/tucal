DROP TRIGGER IF EXISTS t_insert ON tiss.course;
DROP TRIGGER IF EXISTS t_insert ON tiss.group;
DROP TRIGGER IF EXISTS t_insert ON tiss.exam;
DROP TRIGGER IF EXISTS t_insert ON tiss.course_user;
DROP TRIGGER IF EXISTS t_insert ON tiss.group_user;
DROP TRIGGER IF EXISTS t_insert ON tiss.exam_user;
DROP TRIGGER IF EXISTS t_delete ON tiss.group_user;
DROP TRIGGER IF EXISTS t_delete ON tiss.exam_user;

CREATE OR REPLACE FUNCTION tiss.course_to_group()
    RETURNS TRIGGER AS
$$
DECLARE
    nr BIGINT;
BEGIN
    IF (SELECT tucal.get_group(NEW.course_nr, NEW.semester, 'LVA')) IS NOT NULL THEN
        RETURN NEW;
    END IF;
    INSERT INTO tucal.group (group_name)
    VALUES (CONCAT(NEW.course_nr, '-', NEW.semester, ' LVA'))
    RETURNING group_nr INTO nr;
    INSERT INTO tucal.group_link (group_nr, course_nr, semester, name)
    VALUES (nr, NEW.course_nr, NEW.semester, 'LVA');
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
DECLARE
    nr BIGINT;
BEGIN
    IF (SELECT tucal.get_group(NEW.course_nr, NEW.semester, CONCAT('Gruppe ', NEW.group_name))) IS NOT NULL THEN
        RETURN NEW;
    END IF;
    INSERT INTO tucal.group (group_name)
    VALUES (CONCAT(NEW.course_nr, '-', NEW.semester, ' Gruppe ', NEW.group_name))
    RETURNING group_nr INTO nr;
    INSERT INTO tucal.group_link (group_nr, course_nr, semester, name)
    VALUES (nr, NEW.course_nr, NEW.semester, CONCAT('Gruppe ', NEW.group_name));
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
DECLARE
    nr BIGINT;
BEGIN
    IF (SELECT tucal.get_group(NEW.course_nr, NEW.semester, CONCAT('Prüfung ', NEW.exam_name))) IS NOT NULL THEN
        RETURN NEW;
    END IF;
    INSERT INTO tucal.group (group_name)
    VALUES (CONCAT(NEW.course_nr, '-', NEW.semester, ' Prüfung ', NEW.exam_name))
    RETURNING group_nr INTO nr;
    INSERT INTO tucal.group_link (group_nr, course_nr, semester, name)
    VALUES (nr, NEW.course_nr, NEW.semester, CONCAT('Prüfung ', NEW.exam_name));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.exam
    FOR EACH ROW
EXECUTE PROCEDURE tiss.exam_to_group();


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
