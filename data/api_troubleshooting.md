# API Authentication and Troubleshooting

This document outlines the steps for setting up and troubleshooting API authentication.

## 1. Authentication Headers
All API requests must include the following header for authorization:
```
Authorization: Bearer <YOUR_API_TOKEN>
```

## 2. Common Errors
- **401 Unauthorized**: This error occurs if your token is invalid, expired, or deactivated. Check your authorization headers and make sure you do not have whitespace in the token value. Tokens are valid for exactly 24 hours from creation.
- **403 Forbidden**: Occurs if the token does not have permission to access the specific resource. Verify the permissions and scopes assigned to the API token.
- **404 Not Found**: The endpoint path is incorrect or the requested resource does not exist. Check for typos in the endpoint URI.