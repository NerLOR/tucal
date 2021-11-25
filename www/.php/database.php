<?php

global $DB;
if (!isset($DB)) {
    $DB = new PDO("pgsql:host=data.necronda.net;dbname=tucal", "necronda", "Password123", [
        PDO::ATTR_PERSISTENT => true,
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    ]);
}

function db_exec(string $sql, array $params = []): PDOStatement {
    global $DB;
    $stmt = $DB->prepare($sql);
    $stmt->execute($params);
    return $stmt;
}

function db_prepare(string $sql): PDOStatement {
    global $DB;
    return $DB->prepare($sql);
}

function db_transaction(): bool {
    global $DB;
    return $DB->beginTransaction();
}

function db_commit(): bool {
    global $DB;
    return $DB->commit();
}

function db_rollback(): bool {
    global $DB;
    return $DB->rollBack();
}
