DROP VIEW IF EXISTS tucal.v_dau;
DROP TRIGGER IF EXISTS t_insert_dau ON tucal.account;
DROP TRIGGER IF EXISTS t_update_dau ON tucal.account;
DROP TRIGGER IF EXISTS t_insert_dau ON tucal.session;
DROP TRIGGER IF EXISTS t_update_dau ON tucal.session;
DROP TABLE IF EXISTS tucal.dau;


CREATE TABLE tucal.dau
(
    date               DATE NOT NULL,
    hour_utc           INT  NOT NULL,

    users              BIGINT DEFAULT NULL,
    users_new          BIGINT DEFAULT NULL,
    users_sso          BIGINT DEFAULT NULL,
    users_hour         BIGINT DEFAULT NULL,
    users_day          BIGINT DEFAULT NULL,
    users_week         BIGINT DEFAULT NULL,
    users_month        BIGINT DEFAULT NULL,

    users_v            BIGINT DEFAULT NULL,
    users_v_sso        BIGINT DEFAULT NULL,
    users_v_hour       BIGINT DEFAULT NULL,
    users_v_day        BIGINT DEFAULT NULL,
    users_v_week       BIGINT DEFAULT NULL,
    users_v_month      BIGINT DEFAULT NULL,

    sessions           BIGINT DEFAULT NULL,
    sessions_new       BIGINT DEFAULT NULL,
    sessions_hour      BIGINT DEFAULT NULL,
    sessions_day       BIGINT DEFAULT NULL,
    sessions_week      BIGINT DEFAULT NULL,
    sessions_month     BIGINT DEFAULT NULL,

    sessions_l         BIGINT DEFAULT NULL,
    sessions_l_hour    BIGINT DEFAULT NULL,
    sessions_l_day     BIGINT DEFAULT NULL,
    sessions_l_week    BIGINT DEFAULT NULL,
    sessions_l_month   BIGINT DEFAULT NULL,

    sessions_luv       BIGINT DEFAULT NULL,
    sessions_luv_hour  BIGINT DEFAULT NULL,
    sessions_luv_day   BIGINT DEFAULT NULL,
    sessions_luv_week  BIGINT DEFAULT NULL,
    sessions_luv_month BIGINT DEFAULT NULL,

    CONSTRAINT pk_dau PRIMARY KEY (date, hour_utc)
);

CREATE OR REPLACE FUNCTION tucal.update_dau()
    RETURNS TRIGGER AS
$$
DECLARE
    now     TIMESTAMPTZ = current_timestamp AT TIME ZONE 'UTC';
    today   DATE        = now::date;
    today_h TIMESTAMPTZ = today::timestamptz + '05:00'::interval;
    cur_h   INT         = EXTRACT(HOUR FROM now);
    time_h  TIMESTAMPTZ = today::timestamptz + ((cur_h || ':00')::interval);
BEGIN
    INSERT INTO tucal.dau (date, hour_utc)
    VALUES (today, 0),
           (today, 1),
           (today, 2),
           (today, 3),
           (today, 4),
           (today, 5),
           (today, 6),
           (today, 7),
           (today, 8),
           (today, 9),
           (today, 10),
           (today, 11),
           (today, 12),
           (today, 13),
           (today, 14),
           (today, 15),
           (today, 16),
           (today, 17),
           (today, 18),
           (today, 19),
           (today, 20),
           (today, 21),
           (today, 22),
           (today, 23)
    ON CONFLICT DO NOTHING;
    UPDATE tucal.dau
    SET (users,
         users_new,
         users_sso,
         users_hour,
         users_day,
         users_week,
         users_month,
         users_v,
         users_v_sso,
         users_v_hour,
         users_v_day,
         users_v_week,
         users_v_month) = (
        SELECT COUNT(*),
               SUM((create_ts >= time_h AND create_ts < time_h + INTERVAL '1' HOUR)::int),
               SUM((sso_credentials)::int),
               SUM((active_ts >= time_h)::int),
               SUM((active_ts >= today_h)::int),
               SUM((active_ts >= today_h - INTERVAL '7' DAY)::int),
               SUM((active_ts >= today_h - INTERVAL '30' DAY)::int),
               SUM((verified)::int),
               SUM((verified AND sso_credentials)::int),
               SUM((verified AND active_ts >= time_h)::int),
               SUM((verified AND active_ts >= today_h)::int),
               SUM((verified AND active_ts >= today_h - INTERVAL '7' DAY)::int),
               SUM((verified AND active_ts >= today_h - INTERVAL '30' DAY)::int)
        FROM tucal.v_account)
    WHERE (date, hour_utc) = (today, cur_h);
    UPDATE tucal.dau
    SET (sessions,
         sessions_new,
         sessions_hour,
         sessions_day,
         sessions_week,
         sessions_month,
         sessions_l,
         sessions_l_hour,
         sessions_l_day,
         sessions_l_week,
         sessions_l_month,
         sessions_luv,
         sessions_luv_hour,
         sessions_luv_day,
         sessions_luv_week,
         sessions_luv_month) = (
        SELECT COUNT(*),
               SUM((create_ts >= time_h AND create_ts < time_h + INTERVAL '1' HOUR)::int),
               SUM((active_ts >= time_h)::int),
               SUM((active_ts >= today_h)::int),
               SUM((active_ts >= today_h - INTERVAL '7' DAY)::int),
               SUM((active_ts >= today_h - INTERVAL '30' DAY)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts))::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND active_ts >= time_h)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND active_ts >= today_h)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND active_ts >= today_h - INTERVAL '7' DAY)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND active_ts >= today_h - INTERVAL '30' DAY)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND verified)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND verified AND active_ts >= time_h)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND verified AND active_ts >= today_h)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND verified AND
                    active_ts >= today_h - INTERVAL '7' DAY)::int),
               SUM(((active_ts - INTERVAL '1' DAY > create_ts) AND verified AND
                    active_ts >= today_h - INTERVAL '30' DAY)::int)
        FROM tucal.v_session)
    WHERE (date, hour_utc) = (today, cur_h);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_insert_dau
    AFTER INSERT
    ON tucal.account
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_dau();

CREATE TRIGGER t_update_dau
    AFTER UPDATE
    ON tucal.account
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_dau();

CREATE TRIGGER t_insert_dau
    AFTER INSERT
    ON tucal.session
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_dau();

CREATE TRIGGER t_update_dau
    AFTER UPDATE
    ON tucal.session
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_dau();

CREATE OR REPLACE VIEW tucal.v_dau AS
SELECT *
FROM tucal.dau
ORDER BY date DESC, hour_utc DESC;

CREATE OR REPLACE VIEW tucal.v_dau_daily AS
SELECT date,
       max(users_v_day)  AS users_day,
       max(users_v_week) AS users_week,
       max(users_v)      AS users
FROM TUCAL.dau
GROUP BY date
ORDER BY date;
