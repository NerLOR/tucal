DROP VIEW IF EXISTS tucal.v_session;
DROP TABLE IF EXISTS tucal.session;
DROP VIEW IF EXISTS tucal.v_account;
DROP TABLE IF EXISTS tucal.sso_credential;
DROP TABLE IF EXISTS tucal.account CASCADE;

CREATE TABLE tucal.account
(
    account_nr    BIGINT      NOT NULL GENERATED ALWAYS AS IDENTITY,
    account_id    TEXT        NOT NULL DEFAULT NULL,

    mnr           INT         NOT NULL,
    username      CITEXT      NOT NULL CHECK (username ~ '[[:alpha:]][[:alnum:]_ -]{1,30}[[:alnum:]]'),
    email_address CITEXT               DEFAULT NULL CHECK (email_address ~ '[^@]+@([a-z0-9_-]+\.)+[a-z]{2,}'),

    verified      BOOLEAN     NOT NULL DEFAULT FALSE,
    administrator BOOLEAN     NOT NULL DEFAULT FALSE,
    avatar_uri    TEXT                 DEFAULT NULL,

    create_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    login_ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
    active_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    sync_ts       TIMESTAMPTZ          DEFAULT NULL,

    options       JSONB       NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_account PRIMARY KEY (account_nr),
    CONSTRAINT sk_account_id UNIQUE (account_id),
    CONSTRAINT sk_account_mnr UNIQUE (mnr),
    CONSTRAINT sk_account_email UNIQUE (email_address),
    CONSTRAINT sk_account_username UNIQUE (username)
);

CREATE OR REPLACE FUNCTION tucal.account_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.account_id = tucal.gen_id(NEW.account_nr, 15344::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert_id
    BEFORE INSERT
    ON tucal.account
    FOR EACH ROW
EXECUTE PROCEDURE tucal.account_id();


CREATE TABLE tucal.password
(
    account_nr BIGINT      NOT NULL,
    pwd_salt   TEXT                 DEFAULT gen_salt('bf'),
    pwd_hash   TEXT,
    update_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_password PRIMARY KEY (account_nr),
    CONSTRAINT fk_password_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE tucal.friend
(
    account_nr_1 BIGINT NOT NULL,
    account_nr_2 BIGINT NOT NULL,
    nickname     TEXT DEFAULT NULL,

    CONSTRAINT pk_friend PRIMARY KEY (account_nr_1, account_nr_2),
    CONSTRAINT fk_friend_account_1 FOREIGN KEY (account_nr_1) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_friend_account_2 FOREIGN KEY (account_nr_2) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT c_friend_equal CHECK (account_nr_1 != account_nr_2)
);


CREATE TABLE tucal.sso_credential
(
    account_nr BIGINT   NOT NULL,

    key        SMALLINT NOT NULL,
    pwd        TEXT     NOT NULL,
    tfa_gen    TEXT,

    CONSTRAINT pk_sso_credential PRIMARY KEY (account_nr),
    CONSTRAINT fk_sso_credential_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE tucal.token
(
    token_nr    BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
    account_nr  BIGINT NOT NULL,

    usage       TEXT   NOT NULL,
    token       TEXT   NOT NULL CHECK (token ~ '[0-9A-Za-z]{16}'),
    token_short TEXT CHECK (token_short ~ '[0-9A-Z]{5}'),
    valid_ts    TIMESTAMPTZ,

    CONSTRAINT pk_token PRIMARY KEY (token_nr),
    CONSTRAINT sk_token_token UNIQUE (token),
    CONSTRAINT fk_token_account FOREIGN KEY (account_nr) REFERENCES tucal.account (account_nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE OR REPLACE VIEW tucal.v_token AS
SELECT token_nr,
       account_nr,
       usage,
       token,
       token_short,
       valid_ts,
       (valid_ts >= now()) AS valid
FROM tucal.token;


CREATE TABLE tucal.message
(
    message_nr       BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY,
    message_id       TEXT   NOT NULL DEFAULT NULL,

    reply_to_address TEXT CHECK (reply_to_address ~ '[^@]+@([a-z0-9_-]+\.)+[a-z]{2,}'),
    to_address       TEXT CHECK (to_address ~ '[^@]+@([a-z0-9_-]+\.)+[a-z]{2,}'),
    from_name        TEXT,
    subject          TEXT   NOT NULL,
    message          TEXT   NOT NULL,

    submit_ts        TIMESTAMPTZ     DEFAULT now(),
    send_ts          TIMESTAMPTZ     DEFAULT NULL,

    CONSTRAINT pk_message PRIMARY KEY (message_nr),
    CONSTRAINT sk_message UNIQUE (message_id)
);

CREATE OR REPLACE FUNCTION tucal.message_id()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.message_id = tucal.gen_id(NEW.message_nr, 19821::smallint);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER t_insert_id
    BEFORE INSERT
    ON tucal.message
    FOR EACH ROW
EXECUTE PROCEDURE tucal.message_id();


CREATE OR REPLACE VIEW tucal.v_account AS
SELECT a.account_nr,
       a.account_id,
       a.mnr,
       LPAD(a.mnr::text, 8, '0')                                       AS mnr_normal,
       a.username,
       CONCAT('e', LPAD(a.mnr::text, 8, '0'), '@student.tuwien.ac.at') AS email_address_1,
       a.email_address                                                 AS email_address_2,
       a.verified,
       a.administrator,
       (sso.pwd IS NOT NULL)                                           AS sso_credentials,
       (sso.tfa_gen IS NOT NULL)                                       AS sso_tfa,
       a.avatar_uri,
       a.create_ts,
       a.login_ts,
       a.active_ts,
       a.sync_ts,
       a.options
FROM tucal.account a
         LEFT JOIN tucal.sso_credential sso ON sso.account_nr = a.account_nr;

CREATE TABLE tucal.session
(
    session_nr BIGINT      NOT NULL GENERATED ALWAYS AS IDENTITY,
    token      TEXT        NOT NULL CHECK (token ~ '[0-9A-Za-z]{64}'),

    account_nr INT                  DEFAULT NULL,
    options    JSONB       NOT NULL DEFAULT '{}'::jsonb,

    create_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),
    login_ts   TIMESTAMPTZ          DEFAULT NULL,
    active_ts  TIMESTAMPTZ NOT NULL DEFAULT now(),

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
       a.account_id,
       a.mnr,
       a.mnr_normal,
       a.username,
       a.email_address_1,
       a.email_address_2,
       a.verified,
       a.administrator,
       a.sso_credentials,
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
