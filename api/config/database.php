<?php
// api/config/database.php

function getPDO() {
    // In productie (cPanel) worden deze vaak via omgevingsvariabelen of een lokaal bestand ingeladen.
    // We gebruiken hier een array die je later invult met de echte cPanel-gegevens.
    
    $host = getenv('DB_HOST') ?: 'localhost';
    $db   = getenv('DB_NAME') ?: 'dbs16062089';
    $user = getenv('DB_USER') ?: 'root'; // Pas dit aan naar cPanel user
    $pass = getenv('DB_PASS') ?: '';
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
        // In productie: log de error, toon een generieke melding
        error_log("DB Connectie fout: " . $e->getMessage());
        die(json_encode(["error" => "Database verbinding mislukt."]));
    }
}
