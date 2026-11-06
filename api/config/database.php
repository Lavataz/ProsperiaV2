<?php
// api/config/database.php

function getPDO() {
    // Leest uit .htaccess (SetEnv), of valt terug op default
    $host    = getenv('DB_HOST') ?: 'database-JOUWNUMMER.webspace-host.com';
    $db      = getenv('DB_NAME') ?: 'dbs16062089';
    $user    = getenv('DB_USER') ?: 'dbu2834256';
    $pass    = getenv('DB_PASS') ?: 'MR8aqJXPgR&s7%SV;8O&NTQNkX!hX,t';
    $charset = 'utf8mb4';

    $dsn = "mysql:host=$host;dbname=$db;charset=$charset";

    $options = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];

    try {
        return new PDO($dsn, $user, $pass, $options);
    } catch (\PDOException $e) {
        error_log("DB Connectie fout: " . $e->getMessage());
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode(["error" => "Database verbinding mislukt."]);
        exit;
    }
}
