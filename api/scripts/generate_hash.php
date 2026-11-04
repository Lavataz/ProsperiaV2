<?php
// api/scripts/generate_hash.php
// Gebruik: php generate_hash.php "MijnWachtwoord123!"

if ($argc < 2) {
    echo "Gebruik: php generate_hash.php \"jouw_wachtwoord\"\n";
    exit(1);
}

$password = $argv[1];
$hash = password_hash($password, PASSWORD_BCRYPT);

echo "Wachtwoord: $password\n";
echo "Hash: $hash\n";
echo "\nSQL commando om te updaten:\n";
echo "UPDATE prosperia_v2_users SET password_hash = '$hash' WHERE username = 'admin';\n";
