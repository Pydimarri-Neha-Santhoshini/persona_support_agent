# Advanced Troubleshooting Guide: HTTP 401 Unauthorized API Errors

## Overview
The HTTP `401 Unauthorized` response status code indicates that the client request has not been completed because it lacks valid authentication credentials for the target resource. Within the Adsparkx SaaS integration ecosystem, this error is triggered when our secure Gateway is unable to verify the identity of the incoming API consumer, or when the supplied security credentials do not map to an active developer account. Unlike a `403 Forbidden` response, which denotes that the user is authenticated but lacks permission to view a specific resource, a `401 Unauthorized` response means the authentication credentials themselves are completely invalid, expired, misformatted, or missing.

This document serves as a comprehensive troubleshooting guide for developers and integration teams encountering `401` errors while calling Adsparkx endpoint operations. It details the symptoms, common root causes, step-by-step diagnostic workflows, and code examples necessary to restore integration health.

## Symptoms
When a client application experiences an authentication failure with our API endpoints, it will observe one or more of the following system behaviors:
1. **HTTP Status Code**: The API response headers return `HTTP/1.1 401 Unauthorized` or `status: 401`.
2. **JSON Error Response Payload**: The body of the HTTP response will typically include an error code mapping to authentication. A typical response is formatted as follows:
   ```json
   {
     "error": {
       "code": 401,
       "status": "UNAUTHENTICATED",
       "message": "Request is missing a valid API key, token, or credentials. Check your headers.",
       "details": "Reason: Token expired or signature verification failed.",
       "timestamp": "2026-06-19T23:55:00Z",
       "correlation_id": "err_auth_911e097a"
     }
   }
   ```
3. **Integration Logs**: Server integration logs on the developer side will report HTTP request failures specifically when communicating with endpoints nested under `api.adsparkx.com/v1/`.

## Common Causes
The most common reasons for encountering a `401 Unauthorized` error when communicating with Adsparkx APIs include:
* **Missing Authorization Header**: The application did not attach the `Authorization` header to the outgoing HTTP request.
* **Incorrect Header Syntax**: The header was sent, but it does not follow the correct schema. A common mistake is omitting the word `Bearer` before the token value, or mismatching capitalization (e.g. using `bearer` instead of `Bearer`).
* **Invalid or Revoked API Key**: The API key passed in the credentials has been deleted, rotated, or disabled from the Adsparkx Developer console.
* **Token Expiration**: The JSON Web Token (JWT) or temporary Bearer access token generated during the OAuth flow has reached its TTL (Time-To-Live) expiration and is no longer valid. Standard integration tokens expire after 24 hours.
* **Whitespace and Formatting Anomalies**: Hidden spaces, newlines (`\n`), or carriage returns (`\r`) were appended during key copy-paste operations or during automated environment variable injection.
* **OAuth Signature Discrepancies**: If using OAuth 2.0 flows, signature verification can fail on the server side due to clock drift (unsynchronized developer system clocks) or incorrect hashing signatures.

## Troubleshooting Steps

### Step 1: Verify the Authorization Header Format
Ensure that your application is constructing and sending the standard `Authorization` header correctly. The header must match this exact format:
```http
Authorization: Bearer YOUR_ACTUAL_ACCESS_TOKEN
```
Ensure there is exactly one space between `Bearer` and the token string.

### Step 2: Validate the Active API Key Status
1. Navigate to the Adsparkx Developer Portal.
2. Go to **Settings > API keys**.
3. Locate the key used by your application.
4. Verify that the key status is marked as **Active**. If the key has been disabled or rotated, you must replace the old token in your application configuration.

### Step 3: Run a Diagnostic Curl Request
To isolate the issue from your application code, execute a raw `curl` command using a terminal. Substitute `YOUR_API_TOKEN` with the secret key:
```bash
curl -i -X GET "https://api.adsparkx.com/v1/overview" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json"
```
* If this request returns `200 OK`, the issue resides within your application's code structure (e.g., header parsing, environment variable loading).
* If this request returns `401 Unauthorized`, the key itself is expired, invalid, or revoked.

### Step 4: Check for Clock Drift on OAuth Credentials
If your OAuth verification signature is failing, ensure that your client server's system time is synchronized with a global NTP server. If your local system time is drifted by more than 5 minutes from our Gateway clock, authentication tokens will automatically be rejected as expired or not yet valid.

## Code Integration Examples

### Python Integration
Using the standard `requests` library:
```python
import os
import requests

token = os.getenv("ADSPARKX_TOKEN", "").strip() # Ensure leading/trailing spaces are removed
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.adsparkx.com/v1/overview", headers=headers)
if response.status_code == 401:
    print("Authentication failed. Check your API token validity.")
```

### Node.js Integration
Using `axios`:
```javascript
const axios = require('axios');
const token = process.env.ADSPARKX_TOKEN.trim();

axios.get('https://api.adsparkx.com/v1/overview', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(response => console.log(response.data))
.catch(error => {
  if (error.response && error.response.status === 401) {
    console.error('Authentication failed. Access Token is invalid or expired.');
  }
});
```

### Go Integration
Using the standard `net/http` library:
```go
package main

import (
	"fmt"
	"net/http"
	"os"
	"strings"
)

func main() {
	token := strings.TrimSpace(os.Getenv("ADSPARKX_TOKEN"))
	req, _ := http.NewRequest("GET", "https://api.adsparkx.com/v1/overview", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err == nil && resp.StatusCode == http.StatusUnauthorized {
		fmt.Println("Error: 401 Unauthorized response received.")
	}
}
```

## Resolution
Depending on your diagnostics, apply the following resolutions:
* **For Expired Tokens**: Programmatically call the OAuth endpoint `/oauth/token` using your `client_id` and `client_secret` to obtain a fresh access token before the 24-hour expiration window closes.
* **For Whitespace Corruptions**: Clean your credential variables in code using string trimming functions. For example, in Python: `clean_token = token.strip()`.
* **For Revoked Keys**: Generate a new API credential set in the developer portal, update your server environments, and delete the revoked token parameters to maintain high security standards.

## Best Practices
* **Never Hardcode Secrets**: Store API tokens and secrets in environment variables or a secure secret manager (e.g., AWS Secrets Manager, HashiCorp Vault).
* **Automate Token Refresh**: Implement automatic token refresh mechanisms in your HTTP client using refresh tokens, checking if the current time approaches the token's expiration.
* **Implement Log Hiding**: Filter or redact `Authorization` headers from your application log outputs to prevent accidental exposure of keys to unauthorized log readers.

## Frequently Asked Questions

### Q: Can I pass my API token as a query parameter in the URL?
No. For security reasons, Adsparkx endpoints do not support passing access tokens in URL queries (e.g., `?token=YOUR_KEY`). Credentials sent in this manner are intercepted by standard proxy logs. All requests must use the `Authorization` request header.

### Q: Why does my token stop working exactly 24 hours after creation?
Standard Adsparkx bearer tokens are short-lived credentials configured with a strict 24-hour Time-To-Live (TTL) expiration policy to reduce the blast radius of exposed keys. You must implement automated credential exchanges using the OAuth refresh token endpoint.

### Q: What is the difference between a 401 and 403 status code?
A `401 Unauthorized` response means the server could not authenticate your identity (your token is wrong or missing). A `403 Forbidden` response means the server knows who you are, but your account lacks the necessary permissions or scopes to access that specific endpoint (e.g. calling billing endpoints using a read-only developer token).

## Escalation Conditions
If you have completed the diagnostic steps above and continue to receive `401 Unauthorized` errors with an active token, escalate the issue to the Senior Support Specialist.
Provide the following information:
1. The endpoint URI called (e.g. `api.adsparkx.com/v1/analytics`).
2. The exact timestamp of the failed transaction (including timezone).
3. The first 8 characters of your API token (never share the complete token).
4. The request correlation ID (`x-correlation-id`) returned in the response headers.

## Additional Notes
If you are developing inside an enterprise environment, ensure your company's egress firewall or web proxy is not stripping or modifying outgoing `Authorization` header values before they reach our Gateway.
