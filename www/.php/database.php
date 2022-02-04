<?php

global $CONFIG;
global $DB1;
global $DB2;

$DB_CONFIG = $CONFIG['database'];

if (!isset($DB1) || !isset($DB2)) {
    $DB1 = new PDO(
        "pgsql:host=$DB_CONFIG[host];port=$DB_CONFIG[port];dbname=$DB_CONFIG[name]",
        $DB_CONFIG['user'],
        $DB_CONFIG['password'], [
            PDO::ATTR_PERSISTENT => true,
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_TIMEOUT => 5,
    ]);
    // Add " " to create second persistent connection
    $DB2 = new PDO(
        "pgsql:host=$DB_CONFIG[host];port=$DB_CONFIG[port];dbname=$DB_CONFIG[name] ",
        $DB_CONFIG['user'],
        $DB_CONFIG['password'], [
            PDO::ATTR_PERSISTENT => true,
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_TIMEOUT => 5,
    ]);
}

_db_exec("SET lock_timeout TO 5000");
db_exec("SET lock_timeout TO 5000");

function db_exec(string $sql, array $params = []): PDOStatement {
    global $DB1;
    $stmt = $DB1->prepare($sql);
    $stmt->execute($params);
    return $stmt;
}

function db_prepare(string $sql): PDOStatement {
    global $DB1;
    return $DB1->prepare($sql);
}

function db_transaction(): bool {
    global $DB1;
    return $DB1->beginTransaction();
}

function db_commit(): bool {
    global $DB1;
    return $DB1->commit();
}

function db_rollback(): bool {
    global $DB1;
    return $DB1->rollBack();
}

function _db_exec(string $sql, array $params = []): PDOStatement {
    global $DB2;
    $stmt = $DB2->prepare($sql);
    $stmt->execute($params);
    return $stmt;
}

function _db_prepare(string $sql): PDOStatement {
    global $DB2;
    return $DB2->prepare($sql);
}

function _db_transaction(): bool {
    global $DB2;
    return $DB2->beginTransaction();
}

function _db_commit(): bool {
    global $DB2;
    return $DB2->commit();
}

function _db_rollback(): bool {
    global $DB2;
    return $DB2->rollBack();
}
