<?php
/**
 * MPMS Contact Form Handler
 * Sends form submissions via email
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

// Get form data
$name    = isset($_POST['name']) ? trim($_POST['name']) : '';
$company = isset($_POST['company']) ? trim($_POST['company']) : '';
$email   = isset($_POST['email']) ? trim($_POST['email']) : '';
$phone   = isset($_POST['phone']) ? trim($_POST['phone']) : '';
$subject = isset($_POST['subject']) ? trim($_POST['subject']) : '';
$message = isset($_POST['message']) ? trim($_POST['message']) : '';

// Validate required fields
$errors = [];
if (empty($name)) $errors[] = 'Full name is required';
if (empty($email)) $errors[] = 'Email is required';
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) $errors[] = 'Invalid email format';
if (empty($message)) $errors[] = 'Message is required';

if (!empty($errors)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => implode('. ', $errors)]);
    exit;
}

// Email configuration
$to = 'info@modernpowermarine.com';
$cc = 'sales@modernpowermarine.com';
$email_subject = "MPMS Website Inquiry: $subject - " . date('Y-m-d H:i');

// Build email body
$body = "
<html>
<head><style>
body { font-family: Arial, sans-serif; color: #333; }
table { width: 100%; border-collapse: collapse; }
td { padding: 12px; border-bottom: 1px solid #eee; }
td:first-child { font-weight: bold; width: 140px; color: #0a1929; }
</style></head>
<body>
<h2 style='color: #0a1929;'>New Website Inquiry</h2>
<table>
<tr><td>Name</td><td>$name</td></tr>
<tr><td>Company</td><td>" . (!empty($company) ? $company : 'N/A') . "</td></tr>
<tr><td>Email</td><td><a href='mailto:$email'>$email</a></td></tr>
<tr><td>Phone</td><td>" . (!empty($phone) ? $phone : 'N/A') . "</td></tr>
<tr><td>Subject</td><td>$subject</td></tr>
<tr><td>Message</td><td>" . nl2br(htmlspecialchars($message)) . "</td></tr>
</table>
<hr>
<p style='color: #999; font-size: 12px;'>Sent from modernpowersa.com contact form</p>
</body>
</html>
";

// Headers
$headers = "MIME-Version: 1.0\r\n";
$headers .= "Content-type: text/html; charset=UTF-8\r\n";
$headers .= "From: MPMS Website <noreply@modernpowersa.com>\r\n";
$headers .= "Reply-To: $email\r\n";
if (!empty($cc)) {
    $headers .= "Cc: $cc\r\n";
}

// Send
$sent = mail($to, $email_subject, $body, $headers);

if ($sent) {
    echo json_encode([
        'success' => true,
        'message' => 'Thank you! Your message has been sent successfully. We will contact you within 24 hours.'
    ]);
} else {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Sorry, there was an error sending your message. Please try again or call us directly.'
    ]);
}
