<?php
declare(strict_types=1);
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/auth.php';

function status_dispatch(PDO $pdo, array $input): void {
    $action = $input['action'] ?? null;

    switch ($action) {
        case 'status_update': {
            $user = auth_require_user($pdo);
            
            $strat = (int)($input['active_strategies'] ?? 0);
            $pos = (int)($input['open_positions'] ?? 0);
            $bal = $input['account_balance'] ?? null;
            $eq = $input['account_equity'] ?? null;
            
            // Eerst proberen te updaten
            $stmt = $pdo->prepare(
                'UPDATE prosperia_v2_bot_status 
                 SET active_strategies = :s, open_positions = :p, account_balance = :b, account_equity = :e, last_heartbeat = NOW()
                 WHERE user_id = :uid'
            );
            $stmt->execute([':s' => $strat, ':p' => $pos, ':b' => $bal, ':e' => $eq, ':uid' => $user['user_id']]);
            
            // Als er geen rij was (0 affected), insert
            if ($stmt->rowCount() === 0) {
                $stmt2 = $pdo->prepare(
                    'INSERT INTO prosperia_v2_bot_status 
                     (user_id, active_strategies, open_positions, account_balance, account_equity, last_heartbeat) 
                     VALUES (:uid, :s, :p, :b, :e, NOW())'
                );
                $stmt2->execute([':uid' => $user['user_id'], ':s' => $strat, ':p' => $pos, ':b' => $bal, ':e' => $eq]);
            }
            
            http_response_code(200);
            echo json_encode(['ok' => true]);
            exit;
        }

        case 'status_get': {
            $user = auth_require_user($pdo);
            
            $stmt = $pdo->prepare('SELECT * FROM prosperia_v2_bot_status WHERE user_id = :uid LIMIT 1');
            $stmt->execute([':uid' => $user['user_id']]);
            $row = $stmt->fetch();
            
            if (!$row) {
                http_response_code(200);
                echo json_encode(['status' => null, 'message' => 'Bot nog niet gestart']);
                exit;
            }
            
            $is_alive = (strtotime($row['last_heartbeat']) > time() - 120);
            
            http_response_code(200);
            echo json_encode([
                'status' => [
                    'is_running' => $is_alive,
                    'active_strategies' => (int)$row['active_strategies'],
                    'open_positions' => (int)$row['open_positions'],
                    'account_balance' => $row['account_balance'] !== null ? (float)$row['account_balance'] : null,
                    'account_equity' => $row['account_equity'] !== null ? (float)$row['account_equity'] : null,
                    'last_heartbeat' => $row['last_heartbeat'],
                ]
            ]);
            exit;
        }

        case 'signals_list': {
            $user = auth_require_user($pdo);
            
            $stmt = $pdo->prepare(
                'SELECT id, account_id, strategy_id, symbol, action, volume, price, sl, tp, ticket, profit, status, created_at 
                 FROM prosperia_v2_signals 
                 WHERE user_id = :uid 
                 ORDER BY created_at DESC LIMIT 20'
            );
            $stmt->execute([':uid' => $user['user_id']]);
            
            http_response_code(200);
            echo json_encode(['signals' => $stmt->fetchAll()]);
            exit;
        }

        default:
            http_response_code(404);
            echo json_encode(['error' => 'Onbekende status-actie: ' . $action]);
            exit;
    }
}
