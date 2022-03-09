
DELETE FROM tiss.event;
DELETE FROM tuwel.event;
DELETE FROM tucal.external_event;

UPDATE tucal.external_event SET event_nr = NULL;
DELETE FROM tucal.event;
SELECT setval(pg_get_serial_sequence('tucal.event', 'event_nr'), 1);

DELETE FROM tiss.group;
DELETE FROM tuwel.group;

UPDATE tucal.account SET sync_ts = NULL;
