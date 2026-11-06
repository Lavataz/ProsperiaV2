<?php
declare(strict_types=1);
error_reporting(E_ALL);
ini_set('display_errors', '0');

header('Content-Type: application/json; charset=utf-8');

$rawBody = file_get_contents('php://input');
$contentType = $_SERVER['CONTENT_TYPE'] ?? '';
$body = [];
if (stripos($contentType, 'application/json') !== false) {
    $decoded = json_decode($rawBody, true);
    $body = is_array($decoded) ? $decoded : [];
} else {
    $body = $_POST;
}
$input = array_merge($_GET, $body);
$GLOBALS['input'] = $input;

$action = $input['action'] ?? null;

try {
    if ($action === null || $action === '') {
        http_response_code(400);
        echo json_encode(['error' => 'Geen action opgegeven']);
        exit;
    }

    require_once __DIR__ . '/config/database.php';
    require_once __DIR__ . '/routes/auth.php';
    require_once __DIR__ . '/routes/accounts.php';
    require_once __DIR__ . '/routes/strategies.php';

    $pdo = getPDO();

    // Router
    if (in_array($action, ['login', 'register', 'logout', 'me'], true) || str_starts_with($action, 'admin_')) {
        auth_dispatch($pdo, $input);
        exit;
    }

    if (in_array($action, ['accounts_list', 'accounts_save'], true)) {
        accounts_dispatch($pdo, $input);
        exit;
    }

    if (in_array($action, ['list', 'save', 'get', 'delete'], true)) {
        strategies_dispatch($pdo, $input);
        exit;
    }

    http_response_code(404);
    echo json_encode(['error' => "Onbekende action: $action"]);
} catch (Throwable $e) {
    error_log('API fout: ' . $e->getMessage());
    http_response_code(500);
    echo json_encode(['error' => 'Interne serverfout']);
}
