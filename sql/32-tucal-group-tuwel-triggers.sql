DROP TRIGGER IF EXISTS t_insert ON tuwel.course;
DROP TRIGGER IF EXISTS t_insert ON tuwel.course_user;
DROP TRIGGER IF EXISTS t_insert ON tuwel.group;
DROP TRIGGER IF EXISTS t_insert ON tuwel.group_user;
DROP TRIGGER IF EXISTS t_delete ON tuwel.group_user;

CREATE OR REPLACE FUNCTION tuwel.course_to_group()
    RETURNS TRIGGER AS
$$
DECLARE
    nr BIGINT;
BEGIN
    IF (NEW.course_nr IS NULL OR NEW.semester IS NULL) THEN
        RETURN NEW;
    ELSEIF (SELECT tucal.get_group(NEW.course_nr, NEW.semester, 'LVA')) IS NOT NULL THEN
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
    ON tuwel.course
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.course_to_group();


CREATE OR REPLACE FUNCTION tuwel.group_to_group()
    RETURNS TRIGGER AS
$$
DECLARE
    nr        BIGINT;
    course_nr TEXT;
    semester  TEXT;
BEGIN
    SELECT c.course_nr, c.semester FROM tuwel.course c WHERE course_id = NEW.course_id INTO course_nr, semester;
    IF (course_nr IS NULL OR semester IS NULL) THEN
        RETURN NEW;
    ELSEIF (SELECT tucal.get_group(course_nr, semester, NEW.name_normalized)) IS NOT NULL THEN
        RETURN NEW;
    END IF;
    INSERT INTO tucal.group (group_name)
    VALUES (CONCAT(course_nr, '-', semester, ' ', NEW.name_normalized))
    RETURNING group_nr INTO nr;
    INSERT INTO tucal.group_link (group_nr, course_nr, semester, name)
    VALUES (nr, course_nr, semester, NEW.name_normalized);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tuwel.group
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.group_to_group();


CREATE OR REPLACE FUNCTION tuwel.group_user_to_member()
    RETURNS TRIGGER AS
$$
BEGIN
    INSERT INTO tucal.group_member (account_nr, group_nr)
    VALUES ((SELECT account_nr
             FROM tucal.account a
                      JOIN tuwel.user u ON u.mnr = a.mnr
             WHERE user_id = NEW.user_id),
            tucal.get_group((SELECT course_nr
                             FROM tuwel.group g
                                      JOIN tuwel.course c ON c.course_id = g.course_id
                             WHERE group_id = NEW.group_id),
                            (SELECT semester
                             FROM tuwel.group g
                                      JOIN tuwel.course c ON c.course_id = g.course_id
                             WHERE group_id = NEW.group_id),
                            (SELECT g.name_normalized FROM tuwel.group g WHERE g.group_id = NEW.group_id)))
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tuwel.group_user
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.group_user_to_member();


CREATE OR REPLACE FUNCTION tuwel.group_user_del_member()
    RETURNS TRIGGER AS
$$
BEGIN
    DELETE
    FROM tucal.group_member
    WHERE (account_nr, group_nr) = ((SELECT account_nr
                                     FROM tucal.account a
                                              JOIN tuwel.user u ON u.mnr = a.mnr
                                     WHERE user_id = OLD.user_id),
                                    (SELECT tucal.get_group(c.course_nr, c.semester, g.name_normalized)
                                     FROM tuwel.group g
                                              JOIN tuwel.course c ON g.course_id = c.course_id
                                     WHERE g.group_id = OLD.group_id));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tuwel.group_user
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.group_user_del_member();
