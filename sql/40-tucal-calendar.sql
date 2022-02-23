DROP TABLE IF EXISTS tucal.external_event;
DROP TABLE IF EXISTS tucal.event_history;
DROP TABLE IF EXISTS tucal.event;
DROP TRIGGER IF EXISTS t_insert ON tiss.event;
DROP TRIGGER IF EXISTS t_update ON tiss.event;
DROP TRIGGER IF EXISTS t_delete ON tiss.event;
DROP TRIGGER IF EXISTS t_insert ON tuwel.event;
DROP TRIGGER IF EXISTS t_update ON tuwel.event;
DROP TRIGGER IF EXISTS t_delete ON tuwel.event;

CREATE TABLE tucal.event
(
    event_nr         BIGINT      NOT NULL GENERATED ALWAYS AS IDENTITY,
    event_id         TEXT        NOT NULL DEFAULT NULL,

    parent_event_nr  BIGINT               DEFAULT NULL,

    start_ts         TIMESTAMPTZ NOT NULL,
    end_ts           TIMESTAMPTZ NOT NULL,
    planned_start_ts TIMESTAMPTZ          DEFAULT NULL,
    planned_end_ts   TIMESTAMPTZ          DEFAULT NULL,
    real_start_ts    TIMESTAMPTZ          DEFAULT NULL,
    real_end_ts      TIMESTAMPTZ          DEFAULT NULL,

    create_ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
    update_ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
    update_seq       INT         NOT NULL DEFAULT 0,

    room_nr          INT                  DEFAULT NULL,
    group_nr         BIGINT,

    deleted          BOOLEAN              DEFAULT FALSE,
    updated          BOOLEAN              DEFAULT FALSE,
    global           BOOLEAN              DEFAULT TRUE,
    data             JSONB       NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_event PRIMARY KEY (event_nr),
    CONSTRAINT sk_event_id UNIQUE (event_id),
    CONSTRAINT fk_event_event FOREIGN KEY (parent_event_nr) REFERENCES tucal.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_event_room FOREIGN KEY (room_nr) REFERENCES tucal.room (room_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_event_course FOREIGN KEY (group_nr) REFERENCES tucal.group (group_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_start ON tucal.event (start_ts);
CREATE INDEX idx_end ON tucal.event (end_ts);
CREATE INDEX idx_group ON tucal.event (group_nr);
CREATE INDEX idx_room ON tucal.event (room_nr);

CREATE OR REPLACE FUNCTION tucal.event_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.event_id = tucal.gen_id(NEW.event_nr, 15981::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert_id
    BEFORE INSERT
    ON tucal.event
    FOR EACH ROW
EXECUTE PROCEDURE tucal.event_id();

CREATE TABLE tucal.event_history
(
    event_nr      BIGINT      NOT NULL,
    event_version INT         NOT NULL,

    start_ts      TIMESTAMPTZ          DEFAULT NULL,
    end_ts        TIMESTAMPTZ          DEFAULT NULL,

    room_nr       INT                  DEFAULT NULL,
    group_nr      BIGINT,

    deleted       BOOLEAN              DEFAULT NULL,
    updated       BOOLEAN              DEFAULT NULL,
    global        BOOLEAN              DEFAULT NULL,
    data          JSONB                DEFAULT NULL,

    update_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_event_history PRIMARY KEY (event_nr, event_version),
    CONSTRAINT fk_event_history_event FOREIGN KEY (event_nr) REFERENCES tucal.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE tucal.external_event
(
    source   TEXT        NOT NULL,
    event_id TEXT        NOT NULL,
    event_nr BIGINT,

    start_ts TIMESTAMPTZ NOT NULL,
    end_ts   TIMESTAMPTZ NOT NULL,

    room_nr  INT                  DEFAULT NULL,
    group_nr BIGINT,

    deleted  BOOLEAN              DEFAULT FALSE,
    global   BOOLEAN              DEFAULT TRUE,
    data     JSONB       NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_external_event PRIMARY KEY (source, event_id),
    CONSTRAINT fk_external_event_event FOREIGN KEY (event_nr) REFERENCES tucal.event (event_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_room FOREIGN KEY (room_nr) REFERENCES tucal.room (room_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_external_event_course FOREIGN KEY (group_nr) REFERENCES tucal.group (group_nr)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE OR REPLACE FUNCTION tucal.update_external_event()
    RETURNS TRIGGER AS
$$
BEGIN
    IF NEW.event_nr IS NULL THEN
    ELSEIF OLD IS NULL OR OLD.event_nr IS NULL OR NEW.event_nr != OLD.event_nr THEN
        UPDATE tucal.event
        SET start_ts   = (CASE WHEN NEW.source != 'tuwel' THEN NEW.start_ts ELSE start_ts END),
            end_ts     = (CASE WHEN NEW.source != 'tuwel' THEN NEW.end_ts ELSE end_ts END),
            room_nr    = (CASE WHEN NEW.room_nr IS NULL THEN room_nr ELSE NEW.room_nr END),
            group_nr   = (CASE WHEN NEW.group_nr IS NULL THEN group_nr ELSE NEW.group_nr END),
            deleted    = (CASE WHEN NEW.deleted IS NULL THEN deleted ELSE NEW.deleted END),
            global     = (CASE WHEN NEW.global IS NULL THEN global ELSE NEW.global END),
            updated    = FALSE,
            update_ts  = now(),
            update_seq = update_seq + 1
        WHERE event_nr = NEW.event_nr;
    ELSE
        UPDATE tucal.event
        SET start_ts   = (CASE WHEN OLD.start_ts != NEW.start_ts THEN NEW.start_ts ELSE start_ts END),
            end_ts     = (CASE WHEN OLD.end_ts != NEW.end_ts THEN NEW.end_ts ELSE end_ts END),
            room_nr    = (CASE WHEN OLD.room_nr != NEW.room_nr THEN NEW.room_nr ELSE room_Nr END),
            group_nr   = (CASE WHEN OLD.group_nr != NEW.group_nr THEN NEW.group_nr ELSE group_nr END),
            deleted    = (CASE WHEN OLD.deleted != NEW.deleted THEN NEW.deleted ELSE deleted END),
            global     = (CASE WHEN OLD.global != NEW.global THEN NEW.global ELSE global END),
            updated    = FALSE,
            update_ts  = now(),
            update_seq = update_seq + 1
        WHERE event_nr = NEW.event_nr;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tucal.external_event
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_external_event();
CREATE TRIGGER t_update
    AFTER UPDATE
    ON tucal.external_event
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_external_event();


CREATE OR REPLACE FUNCTION tiss.insert_event()
    RETURNS TRIGGER AS
$$
DECLARE
    tiss JSONB;
BEGIN
    tiss = jsonb_build_object(
            'name', NEW.name,
            'description', NEW.description,
            'type', NEW.type,
            'livestream', NEW.livestream,
            'online_only', NEW.online_only);
    INSERT INTO tucal.external_event (source, event_id, event_nr, start_ts, end_ts, room_nr, group_nr, data)
    VALUES ('tiss', NEW.event_nr::text, NULL, NEW.start_ts, NEW.end_ts,
            (SELECT room_nr FROM tucal.v_room r WHERE r.tiss_code = NEW.room_code),
            tucal.get_group(NEW.course_nr, NEW.semester, COALESCE(
                        'Prüfung ' || NEW.exam_name,
                        'Gruppe ' || NEW.group_name,
                        'LVA')), jsonb_build_object('tiss', tiss));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tiss.event
    FOR EACH ROW
EXECUTE PROCEDURE tiss.insert_event();

CREATE OR REPLACE FUNCTION tiss.update_event()
    RETURNS TRIGGER AS
$$
DECLARE
    tiss JSONB;
BEGIN
    tiss = jsonb_build_object(
            'name', NEW.name,
            'description', NEW.description,
            'type', NEW.type,
            'livestream', NEW.livestream,
            'online_only', NEW.online_only,
            'event_id', NEW.event_id);
    UPDATE tucal.external_event
    SET start_ts = NEW.start_ts,
        end_ts   = NEW.end_ts,
        room_nr  = (SELECT room_nr FROM tucal.v_room r WHERE r.tiss_code = NEW.room_code),
        group_nr = tucal.get_group(NEW.course_nr, NEW.semester,
                                   COALESCE(
                                               'Prüfung ' || NEW.exam_name,
                                               'Gruppe ' || NEW.group_name,
                                               'LVA')),
        data     = jsonb_build_object('tiss', tiss)
    WHERE (source, event_id) = ('tiss', NEW.event_nr::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_update
    AFTER UPDATE
    ON tiss.event
    FOR EACH ROW
EXECUTE PROCEDURE tiss.update_event();

CREATE OR REPLACE FUNCTION tiss.delete_event()
    RETURNS TRIGGER AS
$$
BEGIN
    UPDATE tucal.external_event
    SET deleted = TRUE
    WHERE (source, event_id) = ('tiss', OLD.event_nr::text);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tiss.event
    FOR EACH ROW
EXECUTE PROCEDURE tiss.delete_event();


CREATE OR REPLACE FUNCTION tuwel.insert_event()
    RETURNS TRIGGER AS
$$
DECLARE
    tuwel JSONB;
BEGIN
    tuwel = jsonb_build_object(
            'name', NEW.name,
            'event_id', NEW.event_id,
            'course_id', NEW.course_id,
            'event_id', NEW.event_id,
            'description', NEW.description,
            'description_html', NEW.description_html,
            'url', NEW.url,
            'location', NEW.url,
            'module_name', NEW.module_name,
            'component', NEW.component,
            'event_type', NEW.event_type,
            'action_event', NEW.f_action_event,
            'course_event', NEW.f_course_event,
            'category_event', NEW.f_category_event);
    INSERT INTO tucal.external_event (source, event_id, event_nr, start_ts, end_ts, room_nr, group_nr, global, data)
    VALUES ('tuwel', NEW.event_id::text, NULL, NEW.start_ts, NEW.end_ts, NULL,
            tucal.get_group((SELECT course_nr FROM tuwel.course WHERE course_id = NEW.course_id),
                            (SELECT semester FROM tuwel.course WHERE course_id = NEW.course_id),
                            'LVA'), FALSE,
            jsonb_build_object('tuwel', tuwel));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert
    AFTER INSERT
    ON tuwel.event
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.insert_event();

CREATE OR REPLACE FUNCTION tuwel.update_event()
    RETURNS TRIGGER AS
$$
DECLARE
    tuwel JSONB;
BEGIN
    tuwel = jsonb_build_object(
            'name', NEW.name,
            'event_id', NEW.event_id,
            'course_id', NEW.course_id,
            'event_id', NEW.event_id,
            'description', NEW.description,
            'description_html', NEW.description_html,
            'url', NEW.url,
            'location', NEW.url,
            'module_name', NEW.module_name,
            'component', NEW.component,
            'event_type', NEW.event_type,
            'action_event', NEW.f_action_event,
            'course_event', NEW.f_course_event,
            'category_event', NEW.f_category_event);
    UPDATE tucal.external_event
    SET start_ts = NEW.start_ts,
        end_ts   = NEW.end_ts,
        group_nr = tucal.get_group(
                (SELECT course_nr FROM tuwel.course WHERE course_id = NEW.course_id),
                (SELECT semester FROM tuwel.course WHERE course_id = NEW.course_id),
                'LVA'),
        data     = jsonb_build_object('tuwel', tuwel)
    WHERE (source, event_id) = ('tuwel', NEW.event_id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_update
    AFTER UPDATE
    ON tuwel.event
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.update_event();

CREATE OR REPLACE FUNCTION tuwel.delete_event()
    RETURNS TRIGGER AS
$$
BEGIN
    UPDATE tucal.external_event
    SET deleted = TRUE
    WHERE (source, event_id) = ('tuwel', OLD.event_id::text);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_delete
    AFTER DELETE
    ON tuwel.event
    FOR EACH ROW
EXECUTE PROCEDURE tuwel.delete_event();
