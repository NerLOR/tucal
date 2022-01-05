
DELETE FROM tiss.event;
DELETE FROM tuwel.event;
DELETE FROM tucal.external_event;

UPDATE tucal.external_event SET event_nr = NULL;
DELETE FROM tucal.event;
