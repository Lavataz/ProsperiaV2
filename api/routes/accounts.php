<?php
declare(strict_types=1);
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/auth.php';

function accounts_dispatch(PDO $pdo, array $input): void {
    $action = $input['action'] ?? null;

    switch ($action) {
        case 'accounts_list': {
            $user = auth_require_user($pdo);
            if ($user['role'] === 'admin') {
                $stmt = $pdo->query('SELECT id, name, mt5_login, mt5_server, bridge_host, bridge_port, is_active, user_id FROM prosperia_v2_accounts ORDER BY id ASC');
            } else {
                $stmt = $pdo->prepare('SELECT id, name, mt5_login, mt5_server, bridge_host, bridge_port, is_active, user_id FROM prosperia_v2_accounts WHERE user_id = :uid ORDER BY id ASC');
                $stmt->execute([':uid' => $user['user_id']]);
            }
            $rows = $stmt->fetchAll();
            $result = [];
            foreach ($rows as $r) {
                $result[] = [
                    'id' => (int)$r['id'],
                    'name' => $r['name'],
                    'mt5_login' => (int)$r['mt5_login'],
                    'mt5_server' => $r['mt5_server'],
                    'bridge_host' => $r['bridge_host'],
                    'bridge_port' => (int)$r['bridge_port'],
                    'enabled' => (bool)$r['is_active'],
                    'user_id' => (int)$r['user_id'],
                ];
            }
            http_response_code(200);
            header('Content-Type: application/json');
            echo json_encode(['accounts' => $result]);
            exit;
        }

        case 'accounts_save': {
            $user = auth_require_user($pdo);
            $id = (int)($input['id'] ?? 0);
            $name = trim((string)($input['name'] ?? ''));
            $mt5_login = trim((string)($input['mt5_login'] ?? ''));
            $mt5_server = trim((string)($input['mt5_server'] ?? ''));
            $bridge_host = trim((string)($input['bridge_host'] ?? ''));
            $bridge_port = (int)($input['bridge_port'] ?? 18812);

            if ($name === '' || $mt5_login === '') {
                http_response_code(400);
                echo json_encode(['error' => 'Naam en MT5-login zijn verplicht']);
                exit;
            }

            $target_user_id = $user['user_id'];
            if ($user['role'] === 'admin' && isset($input['user_id'])) {
                $target_user_id = (int)$input['user_id'];
            }

            if ($id > 0) {
                if ($user['role'] !== 'admin') {
                    $stmt = $pdo->prepare('SELECT user_id FROM prosperia_v2_accounts WHERE id = :id');
                    $stmt->execute([':id' => $id]);
                    if ((int)$stmt->fetchColumn() !== (int)$user['user_id']) {
                        http_response_code(403);
                        echo json_encode(['error' => 'Geen toegang']);
                        exit;
                    }
                }
                $pdo->prepare('UPDATE prosperia_v2_accounts SET name = :n, mt5_login = :l, mt5_server = :s, bridge_host = :h, bridge_port = :p WHERE id = :id')
                    ->execute([':n' => $name, ':l' => $mt5_login, ':s' => $mt5_server, ':h' => $bridge_host, ':p' => $bridge_port, ':id' => $id]);
            } else {
                $pdo->prepare('INSERT INTO prosperia_v2_accounts (user_id, name, mt5_login, mt5_server, bridge_host, bridge_port, is_active, is_approved) VALUES (:uid, :n, :l, :s, :h, :p, 1, 1)')
                    ->execute([':uid' => $target_user_id, ':n' => $name, ':l' => $mt5_login, ':s' => $mt5_server, ':h' => $bridge_host, ':p' => $bridge_port]);
                $id = $pdo->lastInsertId();
            }

            http_response_code(200);
            echo json_encode(['ok' => true, 'id' => $id]);
            exit;
        }

        default:
            http_response_code(404);
            echo json_encode(['error' => 'Onbekende accounts-actie: ' . $action]);
            exit;
    }
}
