<?php
// api/helpers/crypto.php

class Crypto {
    private static $method = 'aes-256-gcm';
    private static $key;

    private static function getKey() {
        if (!self::$key) {
            $key = getenv('PROSPERIA_MASTER_KEY');
            if (!$key) {
                throw new Exception("PROSPERIA_MASTER_KEY environment variable is niet ingesteld.");
            }
            // Zorg dat de key exact 32 bytes is (SHA-256 hash van de input)
            self::$key = hash('sha256', $key, true);
        }
        return self::$key;
    }

    public static function encrypt($plaintext) {
        $ivLength = openssl_cipher_iv_length(self::$method);
        $iv = openssl_random_pseudo_bytes($ivLength);
        $tag = '';
        
        $ciphertext = openssl_encrypt(
            $plaintext, 
            self::$method, 
            self::getKey(), 
            OPENSSL_RAW_DATA, 
            $iv, 
            $tag
        );
        
        if ($ciphertext === false) {
            throw new Exception("Encryptie mislukt.");
        }

        // Combineer IV + Tag + Ciphertext en base64-encode het
        return base64_encode($iv . $tag . $ciphertext);
    }

    public static function decrypt($encryptedBase64) {
        $data = base64_decode($encryptedBase64);
        if ($data === false) return false;

        $ivLength = openssl_cipher_iv_length(self::$method);
        $tagLength = 16; // GCM tag length

        $iv = substr($data, 0, $ivLength);
        $tag = substr($data, $ivLength, $tagLength);
        $ciphertext = substr($data, $ivLength + $tagLength);

        return openssl_decrypt(
            $ciphertext, 
            self::$method, 
            self::getKey(), 
            OPENSSL_RAW_DATA, 
            $iv, 
            $tag
        );
    }
}
