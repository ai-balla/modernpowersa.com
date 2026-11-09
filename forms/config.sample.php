<?php
/**
 * SAMPLE ONLY — this file is not used by the site.
 *
 * Copy it to the hosting account, OUTSIDE public_html, as:
 *     ~/_mpms_private/form-config.php
 * and fill in the real values. Do not commit the real file to Git.
 */
return [
    // Mailbox(es) that receive form submissions. Must be confirmed by MPMS management.
    'to' => ['info@example.com'],
    'cc' => [],
    // Sender address. Must belong to a domain whose SPF/DKIM allows this server to send.
    'from' => 'no-reply@modernpowersa.com',
    'subject_prefix' => '[modernpowersa.com]',
    'allowed_origins' => ['https://modernpowersa.com', 'https://www.modernpowersa.com'],
    'rate_limit_per_hour' => 5,
    'salt' => 'change-this-to-a-random-string',
    // 'mail' (PHP mail() on Hostinger) or 'log' (local testing only; requires 'log_file').
    'transport' => 'mail',
    // 'log_file' => '/home/USER/_mpms_private/form-test.log',
];
