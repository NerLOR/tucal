
CREATE TABLE tucal.account
(
    account_nr    INT                      NOT NULL GENERATED ALWAYS AS IDENTITY,
    mnr           INT                      NOT NULL,
    username      CITEXT                   NOT NULL CHECK (username ~ '[[:alpha:]][[:alnum:]_ -]{1,30}[[:alnum:]]'),
    email_address CITEXT                            DEFAULT NULL CHECK (email_address ~ '[^@]+@([a-z0-9_-]+\.)+[a-z]{2,}'),

    verified      BOOLEAN                  NOT NULL DEFAULT FALSE,
    avatar_uri    TEXT                              DEFAULT NULL,

    create_ts     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    login_ts      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    active_ts     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    sync_ts       TIMESTAMP WITH TIME ZONE          DEFAULT NULL,

    options       JSONB                    NOT NULL DEFAULT '{}'::jsonb,

    pwd_salt      TEXT                              DEFAULT gen_salt('bf'),
    pwd_hash      TEXT,

    CONSTRAINT pk_account PRIMARY KEY (account_nr),
    CONSTRAINT sk_account_mnr UNIQUE (mnr),
    CONSTRAINT sk_account_email UNIQUE (email_address),
    CONSTRAINT sk_account_username UNIQUE (username)
);

CREATE OR REPLACE VIEW tucal.v_account AS
SELECT a.account_nr,
       a.mnr,
       LPAD(a.mnr::text, 8, '0')                                       AS mnr_normal,
       a.username,
       CONCAT('e', LPAD(a.mnr::text, 8, '0'), '@student.tuwien.ac.at') AS email_address_1,
       a.email_address                                                 AS email_address_2,
       a.verified,
       a.avatar_uri,
       a.create_ts,
       a.login_ts,
       a.active_ts,
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
    login_ts   TIMESTAMP WITH TIME ZONE          DEFAULT NULL,
    active_ts  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

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
       s.create_ts,
       s.login_ts,
       s.active_ts,
       a.create_ts AS account_create_ts,
       a.login_ts  AS account_login_ts,
       a.active_ts AS account_active_ts,
       a.sync_ts   AS account_sync_ts,
       a.options   AS account_opts
FROM tucal.session s
         LEFT JOIN tucal.v_account a ON a.account_nr = s.account_nr;

CREATE OR REPLACE FUNCTION tucal.update_session()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.active_ts = now();
    UPDATE tucal.account SET active_ts = now() WHERE account_nr = OLD.account_nr;
    IF OLD.account_nr IS NULL and NEW.account_nr IS NOT NULL THEN
        UPDATE tucal.account SET active_ts = now(), login_ts = now() WHERE account_nr = NEW.account_nr;
        NEW.login_ts = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_update
    BEFORE UPDATE
    ON tucal.session
    FOR EACH ROW
EXECUTE PROCEDURE tucal.update_session();