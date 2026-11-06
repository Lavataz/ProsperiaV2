<?php
// api/index.php — centrale router voor Prosperia V2

declare(strict_types=1);

error_reporting(E_ALL);
ini_set('display_errors', '1');          // nooit naar output lekken
ini_set('log_errors', '0');

header('Content-Type: application/json; charset=utf-8');

// ---- Body parsen (JSON of form-encoded) ----------------------------------
$rawBody = file_get_contents('php://input');
$contentType = $_SERVER['CONTENT_TYPE'] ?? '';

$body = [];
if (stripos($contentType, 'application/json') !== false) {
    $decoded = json_decode($rawBody, true);
    $body = is_array($decoded) ? $decoded : [];
} else {
    // Fallback: form-encoded of query-params
    $body = $_POST;
}

// Query-params hebben laagste prioriteit, body overschrijft
$input = array_merge($_GET, $body);
$GLOBALS['input'] = $input;

$action = $input['action'] ?? $input['route'] ?? null;
error_log("DEBUG index.php: action=" . var_export($action, true) . " input=" . var_export($input, true));

// ---- Dispatch ------------------------------------------------------------
try {
    if ($action === null || $action === '') {
        http_response_code(400);
        echo json_encode(['error' => 'Geen action opgegeven']);
        exit;
    }

    // Alles onder auth/*
    if ($action === 'login' || $action === 'refresh' || $action === 'logout' || $action === 'me') {
        require __DIR__ . '/routes/auth.php';
        exit;
    }

    // Alles onder strategies/*
    if ($action === 'list' || $action === 'get' || $action === 'save' || $action === 'delete') {
        require __DIR__ . '/routes/strategies.php';
        exit;
    }

    // Accounts (voor later, optioneel)
    if (in_array($action, ['accounts_list', 'accounts_get'], true)) {
        require __DIR__ . '/routes/accounts.php';
        exit;
    }

    http_response_code(404);
    echo json_encode(['error' => "Onbekende action: $action"]);
} catch (Throwable $e) {
    error_log('API fout: ' . $e->getMessage() . ' @ ' . $e->getFile() . ':' . $e->getLine());
    http_response_code(500);
    echo json_encode(['error' => 'Interne serverfout']);
}
