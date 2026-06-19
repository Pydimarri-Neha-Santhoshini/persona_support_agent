# Webhook Notifications Configuration

Webhooks enable real-time delivery of event updates to your application server.

## 1. Setup Instructions
- Navigate to developer settings in the dashboard.
- Input your server endpoint URL (must support HTTPS).
- Select the event types to subscribe to (e.g., payment.completed, subscription.cancelled).

## 2. Signature Verification
Verify requests are sent by our server by computing the HMAC-SHA256 signature using the endpoint secret and checking the `X-Adsparkx-Signature` header.