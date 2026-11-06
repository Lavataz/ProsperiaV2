<?php
// api/routes/accounts.php — accounts ophalen voor de bot

declare(strict_types=1);

require_once __DIR__ . '/../config/database.php';

function acc_json_out(int $status, array $data): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data);
    exit;
}

function acc_bearer(): ?string {
    $h = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/^Bearer\s+(.+)$/i', $h, $m)) return trim($m[1]);
    return null;
}

function acc_require_auth(PDO $pdo): array {
    $token = acc_bearer();
    if (!$token) acc_json_out(401, ['error' => 'Geen token']);

    $stmt = $pdo->prepare(
        'SELECT t.user_id, t.expires_at, u.is_active
         FROM prosperia_v2_tokens t
         JOIN prosperia_v2_users u ON u.id = t.user_id
         WHERE t.token = :t LIMIT 1'
    );
    $stmt->execute([':t' => $token]);
    $row = $stmt->fetch();
    if (!$row) acc_json_out(401, ['error' => 'Token ongeldig']);
    if (strtotime($row['expires_at']) < time()) acc_json_out(401, ['error' => 'Token verlopen']);
    if (!(int)$row['is_active']) acc_json_out(403, ['error' => 'Account gedeactiveerd']);
    return $row;
}

// FIX: haal $input op uit alle mogelijke bronnen
if (isset($GLOBALS['input']) && is_array($GLOBALS['input'])) {
    $input = $GLOBALS['input'];
} elseif (isset($input) && is_array($input)) {
    // al in scope (werkt bij directe require vanuit index.php)
} else {
    // laatste fallback: parse body zelf
    $raw = file_get_contents('php://input');
    $parsed = json_decode($raw, true);
    $input = is_array($parsed) ? $parsed : [];
}

$pdo = getPDO();
acc_require_auth($pdo);

$action = $input['action'] ?? null;

switch ($action) {
    case 'accounts_list':
    case 'list': {
        $stmt = $pdo->query(
            'SELECT id, name, mt5_login, mt5_server, bridge_host, bridge_port, is_active
             FROM prosperia_v2_accounts
             ORDER BY id ASC'
        );
        $rows = $stmt->fetchAll();

        $result = [];
        foreach ($rows as $r) {
            $result[] = [
                'id'          => (int)$r['id'],
                'name'        => $r['name'],
                'mt5_login'   => (int)$r['mt5_login'],
                'mt5_server'  => $r['mt5_server'],
                'bridge_host' => $r['bridge_host'],
                'bridge_port' => (int)$r['bridge_port'],
                'enabled'     => (bool)$r['is_active'],
            ];
        }

        acc_json_out(200, ['accounts' => $result]);
    }

    default:
        acc_json_out(404, ['error' => 'Onbekende accounts-actie: ' . var_export($action, true)]);
}
