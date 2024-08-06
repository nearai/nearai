USE hub;

-- nonce represents a 32 bytes array 
-- https://github.com/near/NEPs/blob/master/neps/nep-0413.md#input-interface
-- account_id is a near account, max 64 characters

CREATE TABLE nonces (
    nonce VARCHAR(32),
    account_id VARCHAR(64),
    message TEXT NOT NULL,
    recipient VARCHAR(64) NOT NULL,
    callback_url TEXT NULL,
    nonce_status ENUM('active', 'revoked') NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, nonce, message(255), recipient),
    UNIQUE KEY unique_nonce (account_id, nonce, message(255), callback_url(255), recipient)
);