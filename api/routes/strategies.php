<?php
declare(strict_types=1);
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/auth.php';

function strategies_dispatch(PDO $pdo, array $input): void {
    $action = $input['action'] ?? null;

    switch ($action) {
        case 'list': {
            $user = auth_require_user($pdo);
            if ($user['role'] === 'admin') {
                $stmt = $pdo->query('SELECT s.id, s.name, s.is_active AS enabled, s.magic_number, s.version, s.account_id FROM prosperia_v2_strategies s WHERE s.is_active = 1 ORDER BY s.id ASC');
            } else {
                $stmt = $pdo->prepare('SELECT s.id, s.name, s.is_active AS enabled, s.magic_number, s.version, s.account_id FROM prosperia_v2_strategies s JOIN prosperia_v2_accounts a ON a.id = s.account_id WHERE s.is_active = 1 AND a.user_id = :uid ORDER BY s.id ASC');
                $stmt->execute([':uid' => $user['user_id']]);
            }
            $strategies = $stmt->fetchAll();

            $stmt_cfg = $pdo->query('SELECT strategy_id, config_key, config_value FROM prosperia_v2_strategy_configs');
            $grouped = [];
            foreach ($stmt_cfg->fetchAll() as $c) {
                $grouped[$c['strategy_id']][$c['config_key']] = $c['config_value'];
            }

            $result = [];
            foreach ($strategies as $s) {
                $cfg = $grouped[$s['id']] ?? [];
                $params = [];
                foreach ($cfg as $k => $v) {
                    if (!in_array($k, ['plugin', 'symbol', 'timeframe'])) {
                        $params[$k] = is_numeric($v) ? (float)$v : $v;
                    }
                }
                $result[] = [
                    'id' => (int)$s['id'],
                    'name' => $s['name'],
                    'plugin' => $cfg['plugin'] ?? 'unknown',
                    'enabled' => (bool)$s['enabled'],
                    'symbol' => $cfg['symbol'] ?? '',
                    'timeframe' => $cfg['timeframe'] ?? '',
                    'params' => (object)$params,
                    'account_id' => $s['account_id'] !== null ? (int)$s['account_id'] : null,
                ];
            }
            http_response_code(200);
            echo json_encode(['strategies' => $result]);
            exit;
        }

        case 'save': {
            $user = auth_require_user($pdo);
            $id = (int)($input['id'] ?? 0);
            $name = trim((string)($input['name'] ?? ''));
            $account_id = (int)($input['account_id'] ?? 0);
            $is_active = isset($input['is_active']) ? (int)$input['is_active'] : 1;
            $params = $input['params'] ?? [];

            if ($name === '' || $account_id <= 0) {
                http_response_code(400);
                echo json_encode(['error' => 'Naam en account_id zijn verplicht']);
                exit;
            }

            if ($user['role'] !== 'admin') {
                $stmt = $pdo->prepare('SELECT user_id FROM prosperia_v2_accounts WHERE id = :id');
                $stmt->execute([':id' => $account_id]);
                if ((int)$stmt->fetchColumn() !== (int)$user['user_id']) {
                    http_response_code(403);
                    echo json_encode(['error' => 'Account niet van jou']);
                    exit;
                }
            }

            $pdo->beginTransaction();
            try {
                if ($id > 0) {
                    $pdo->prepare('UPDATE prosperia_v2_strategies SET name = :n, account_id = :a, is_active = :act WHERE id = :id')
                        ->execute([':n' => $name, ':a' => $account_id, ':act' => $is_active, ':id' => $id]);
                } else {
                    $pdo->prepare('INSERT INTO prosperia_v2_strategies (name, account_id, is_active, magic_number, version) VALUES (:n, :a, :act, :magic, "1.0.0")')
                        ->execute([':n' => $name, ':a' => $account_id, ':act' => $is_active, ':magic' => rand(1000, 9999)]);
                    $id = $pdo->lastInsertId();
                }
                foreach ($params as $key => $value) {
                    $pdo->prepare('REPLACE INTO prosperia_v2_strategy_configs (strategy_id, config_key, config_value) VALUES (:sid, :k, :v)')
                        ->execute([':sid' => $id, ':k' => $key, ':v' => $value]);
                }
                $pdo->commit();
                http_response_code(200);
                echo json_encode(['ok' => true, 'id' => $id]);
                exit;
            } catch (Exception $e) {
                $pdo->rollBack();
                http_response_code(500);
                echo json_encode(['error' => $e->getMessage()]);
                exit;
            }
        }

        default:
            http_response_code(404);
            echo json_encode(['error' => 'Onbekende strategies-actie: ' . $action]);
            exit;
    }
}
