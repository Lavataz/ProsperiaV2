<?php
// api/routes/strategies.php — strategieën ophalen voor hot-reload

declare(strict_types=1);

require_once __DIR__ . '/../config/database.php';

// require_auth zit in auth.php; hier lokaal herhalen om onafhankelijk te blijven
function strat_json_out(int $status, array $data): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data);
    exit;
}

function strat_bearer(): ?string {
    $h = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/^Bearer\s+(.+)$/i', $h, $m)) return trim($m[1]);
    return null;
}

function strat_require_auth(PDO $pdo): array {
    $token = strat_bearer();
    if (!$token) strat_json_out(401, ['error' => 'Geen token']);

    $stmt = $pdo->prepare(
        'SELECT t.user_id, t.expires_at, u.is_active
         FROM prosperia_v2_tokens t
         JOIN prosperia_v2_users u ON u.id = t.user_id
         WHERE t.token = :t LIMIT 1'
    );
    $stmt->execute([':t' => $token]);
    $row = $stmt->fetch();
    if (!$row) strat_json_out(401, ['error' => 'Token ongeldig']);
    if (strtotime($row['expires_at']) < time()) strat_json_out(401, ['error' => 'Token verlopen']);
    if (!(int)$row['is_active']) strat_json_out(403, ['error' => 'Account gedeactiveerd']);
    return $row;
}

$pdo = getPDO();
strat_require_auth($pdo);

$action = $input['action'] ?? null;

switch ($action) {

case 'list': {
    $stmt = $pdo->query(
        'SELECT s.id, s.name, s.is_active AS enabled, s.magic_number, s.version, s.account_id
         FROM prosperia_v2_strategies s
         WHERE s.is_active = 1
         ORDER BY s.id ASC'
    );
    $strategies = $stmt->fetchAll();

    $stmt_cfg = $pdo->query(
        'SELECT strategy_id, config_key, config_value 
         FROM prosperia_v2_strategy_configs'
    );
    $configs = $stmt_cfg->fetchAll();

    $grouped_configs = [];
    foreach ($configs as $c) {
        $grouped_configs[$c['strategy_id']][$c['config_key']] = $c['config_value'];
    }

    $result = [];
    foreach ($strategies as $s) {
        $sid = $s['id'];
        $cfg = $grouped_configs[$sid] ?? [];

        $plugin    = $cfg['plugin'] ?? 'unknown';
        $symbol    = $cfg['symbol'] ?? '';
        $timeframe = $cfg['timeframe'] ?? '';
        
        $params = [];
        foreach ($cfg as $key => $val) {
            if (!in_array($key, ['plugin', 'symbol', 'timeframe'])) {
                $params[$key] = is_numeric($val) ? (float)$val : $val;
            }
        }

        $result[] = [
            'id'          => (int)$s['id'],
            'name'        => $s['name'],
            'plugin'      => $plugin,
            'enabled'     => (bool)$s['enabled'],
            'symbol'      => $symbol,
            'timeframe'   => $timeframe,
            'params'      => (object)$params,
            'account_id'  => $s['account_id'] !== null ? (int)$s['account_id'] : null,
        ];
    }

    strat_json_out(200, ['strategies' => $result]);
}

    case 'get': {
        $id = (int)($input['id'] ?? 0);
        if ($id <= 0) strat_json_out(400, ['error' => 'id ontbreekt']);

        $stmt = $pdo->prepare(
            'SELECT id, name, plugin, enabled, symbol, timeframe, params, account_id
             FROM prosperia_v2_strategies WHERE id = :id'
        );
        $stmt->execute([':id' => $id]);
        $row = $stmt->fetch();
        if (!$row) strat_json_out(404, ['error' => 'Strategie niet gevonden']);

        if (is_string($row['params'])) {
            $decoded = json_decode($row['params'], true);
            $row['params'] = is_array($decoded) ? $decoded : [];
        }
        $row['enabled'] = (bool)$row['enabled'];
        $row['id'] = (int)$row['id'];

        strat_json_out(200, ['strategy' => $row]);
    }

    default:
        strat_json_out(404, ['error' => 'Onbekende strategies-actie']);
}
