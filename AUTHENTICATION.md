# API Key Authentication Guide

Complete guide for implementing API key-based authentication in Obsidian Brain.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [API Key Management](#api-key-management)
4. [Using API Keys](#using-api-keys)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Enable Authentication

```bash
export BRAIN_AUTH_REQUIRED=true
brain serve --host 0.0.0.0 --port 8009
```

### Generate Your First API Key

```bash
curl -X POST http://localhost:8009/api/keys/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Key",
    "days_valid": 365
  }'
```

Response:
```json
{
  "success": true,
  "api_key": "obsidian_ABC123...",
  "name": "My First Key",
  "message": "⚠️  Save this key immediately. You won't be able to see it again!",
  "usage": "Add header: {'X-API-Key': 'obsidian_ABC123...'}"
}
```

### Use API Key in Requests

```bash
curl -X POST http://localhost:8009/api/ask \
  -H "X-API-Key: obsidian_ABC123..." \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?", "top_k": 5}'
```

---

## Configuration

### Environment Variables

```bash
# Enable authentication (default: false)
BRAIN_AUTH_REQUIRED=true

# Directory to store API keys (default: ./data/api_keys)
BRAIN_API_KEY_DIR=/etc/obsidian-brain/api_keys

# Custom header name (default: X-API-Key)
# BRAIN_API_KEY_HEADER=Authorization
```

### .env File

```bash
# .env
BRAIN_AUTH_REQUIRED=true
BRAIN_API_KEY_DIR=/data/api_keys
```

### Authentication Modes

#### Mode 1: Optional (Default)

Authentication is optional. Requests work with or without an API key.

```bash
export BRAIN_AUTH_REQUIRED=false
```

#### Mode 2: Required

Authentication is required. All API requests must include a valid API key.

```bash
export BRAIN_AUTH_REQUIRED=true
```

---

## API Key Management

### Generate API Keys

#### Request

```
POST /api/keys/generate
Content-Type: application/json

{
  "name": "Production API Key",
  "days_valid": 365
}
```

#### Response

```json
{
  "success": true,
  "api_key": "obsidian_32characterTokenHere...",
  "name": "Production API Key",
  "message": "⚠️  Save this key immediately. You won't be able to see it again!",
  "usage": "Add header: {'X-API-Key': 'obsidian_...'}"
}
```

#### Notes

- API keys are 32 characters long (256-bit security)
- Keys are prefixed with `obsidian_` for easy identification
- **IMPORTANT**: Keys are only shown once. Save them immediately!
- Default expiration: 365 days (can be customized)
- Set `days_valid: 0` for keys that never expire

### List API Keys

#### Request

```
GET /api/keys/list
```

#### Response

```json
{
  "success": true,
  "keys": [
    {
      "name": "Production API Key",
      "created": "2026-06-14T12:00:00",
      "expiration": "2027-06-14T12:00:00",
      "active": true,
      "requests_count": 1250,
      "last_used": "2026-06-14T14:30:00",
      "key_hash": "abc123def456..."
    }
  ],
  "auth_required": true
}
```

### Revoke API Keys

#### Request

```
POST /api/keys/revoke
Content-Type: application/json

{
  "key": "obsidian_32characterTokenHere..."
}
```

#### Response

```json
{
  "success": true,
  "message": "API key revoked successfully"
}
```

### Check Authentication Status

#### Request

```
GET /api/auth/status
X-API-Key: obsidian_...
```

#### Response

```json
{
  "success": true,
  "auth_required": true,
  "has_api_key": true,
  "is_authenticated": true,
  "api_key_header": "X-API-Key"
}
```

---

## Using API Keys

### In HTTP Headers

```bash
curl -X POST http://localhost:8009/api/ask \
  -H "X-API-Key: obsidian_ABC123..." \
  -H "Content-Type: application/json" \
  -d '{"question": "Example", "top_k": 5}'
```

### In Python

```python
import requests

api_key = "obsidian_ABC123..."
headers = {"X-API-Key": api_key}

response = requests.post(
    "http://localhost:8009/api/ask",
    headers=headers,
    json={"question": "What is AI?", "top_k": 5}
)

print(response.json())
```

### In JavaScript

```javascript
const apiKey = "obsidian_ABC123...";

fetch("http://localhost:8009/api/ask", {
  method: "POST",
  headers: {
    "X-API-Key": apiKey,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    question: "What is AI?",
    top_k: 5
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

### In CLI Tools

```bash
# Using curl
curl -H "X-API-Key: obsidian_ABC123..." http://localhost:8009/api/stats

# Using httpie
http GET http://localhost:8009/api/stats X-API-Key:"obsidian_ABC123..."

# Using wget
wget --header="X-API-Key: obsidian_ABC123..." http://localhost:8009/api/stats
```

### Environment Variables

```bash
# Store API key in environment
export OBSIDIAN_API_KEY="obsidian_ABC123..."

# Use in curl
curl -H "X-API-Key: $OBSIDIAN_API_KEY" http://localhost:8009/api/ask
```

### Configuration Files

Create `~/.obsidian-brain/config.json`:

```json
{
  "api_url": "http://localhost:8009",
  "api_key": "obsidian_ABC123...",
  "timeout": 30
}
```

Then use in Python:

```python
import json
from pathlib import Path

config_file = Path.home() / ".obsidian-brain" / "config.json"
with open(config_file) as f:
    config = json.load(f)

headers = {"X-API-Key": config["api_key"]}
```

---

## Best Practices

### Key Generation Best Practices

1. **Generate Unique Keys per Environment**
   ```bash
   # Production
   KEY_PROD=$(curl -s -X POST http://prod.brain:8009/api/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "Production"}' | jq -r '.api_key')
   
   # Development
   KEY_DEV=$(curl -s -X POST http://localhost:8009/api/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "Development"}' | jq -r '.api_key')
   ```

2. **Unique Keys per Application**
   ```bash
   curl -X POST http://localhost:8009/api/keys/generate \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Mobile App v1.0",
       "days_valid": 90
     }'
   ```

3. **Time-Limited Keys**
   ```bash
   # API key expires in 30 days
   curl -X POST http://localhost:8009/api/keys/generate \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Temporary Access",
       "days_valid": 30
     }'
   ```

### Security Best Practices

1. **Never Hardcode API Keys**
   ❌ WRONG:
   ```python
   api_key = "obsidian_ABC123..."  # Visible in code!
   ```
   
   ✅ CORRECT:
   ```python
   api_key = os.getenv("OBSIDIAN_API_KEY")
   ```

2. **Use Environment Variables**
   ```bash
   # .env (add to .gitignore!)
   OBSIDIAN_API_KEY=obsidian_ABC123...
   
   # Load in application
   from dotenv import load_dotenv
   load_dotenv()
   api_key = os.getenv("OBSIDIAN_API_KEY")
   ```

3. **Rotate Keys Regularly**
   ```bash
   # Generate new key
   NEW_KEY=$(curl -s -X POST http://localhost:8009/api/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "Production"}' | jq -r '.api_key')
   
   # Update application
   # ...
   
   # Revoke old key
   curl -X POST http://localhost:8009/api/keys/revoke \
     -H "Content-Type: application/json" \
     -d '{"key": "obsidian_OLD_KEY..."}'
   ```

4. **Monitor Key Usage**
   ```bash
   # Check last used time and request count
   curl http://localhost:8009/api/keys/list | jq '.keys[] | {name, requests_count, last_used}'
   ```

5. **Use Secrets Management Tools**
   - HashiCorp Vault
   - AWS Secrets Manager
   - Google Cloud Secret Manager
   - Azure Key Vault
   - 1Password Business
   - LastPass Teams

6. **Store Keys Securely**
   ```bash
   # Bad: Plain text file
   api_key="obsidian_..."  # Visible!
   
   # Good: Environment variable
   export OBSIDIAN_API_KEY="obsidian_..."
   
   # Better: Secrets manager
   api_key=$(vault kv get -field=value secret/obsidian/api_key)
   ```

### Rate Limiting with API Keys

API keys have their own rate limiting:

```bash
# Each API key has separate rate limits
# Search: 100 requests/hour
# Ask: 50 requests/hour
# Stats: 1000 requests/hour

# Check current usage
curl -H "X-API-Key: obsidian_ABC123..." http://localhost:8009/api/stats

# Response includes rate limit info
{
  "success": true,
  "metrics": {
    "search_requests": 45,
    "ask_requests": 12,
    "stats_requests": 500
  }
}
```

---

## Troubleshooting

### "API key required" Error

**Problem**: Getting 401 Unauthorized

**Solution 1**: Add API key header
```bash
# Wrong
curl http://localhost:8009/api/ask

# Correct
curl -H "X-API-Key: obsidian_ABC123..." http://localhost:8009/api/ask
```

**Solution 2**: Disable authentication (development only)
```bash
export BRAIN_AUTH_REQUIRED=false
brain serve --host 0.0.0.0 --port 8009
```

### "Invalid or expired API key" Error

**Problem**: Getting 403 Forbidden

**Causes**:
1. API key is incorrect
2. API key has expired
3. API key has been revoked

**Solutions**:

Check key expiration:
```bash
curl http://localhost:8009/api/keys/list | jq '.keys[] | {name, expiration}'
```

Generate a new key:
```bash
curl -X POST http://localhost:8009/api/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "New Key", "days_valid": 365}'
```

### "API key not found in request"

**Problem**: Custom header name not recognized

**Solution 1**: Use default header name
```bash
curl -H "X-API-Key: obsidian_ABC123..." http://localhost:8009/api/ask
```

**Solution 2**: Check configuration
```bash
# Verify BRAIN_API_KEY_HEADER is correct
echo $BRAIN_API_KEY_HEADER
```

### Lost API Key

**Problem**: Generated a key but forgot to save it

**Solution**: Generate a new key
```bash
# Old key is gone forever
# Create a new key
curl -X POST http://localhost:8009/api/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "Replacement Key"}'
```

### Keys File Corruption

**Problem**: `./data/api_keys/keys.json` is corrupted

**Solution 1**: Restore from backup
```bash
cp ./data/api_keys/keys.json.backup ./data/api_keys/keys.json
```

**Solution 2**: Delete and regenerate
```bash
rm ./data/api_keys/keys.json
# Restart the server
# Generate new keys
```

---

## API Key Format

```
obsidian_[32-character-base64-encoded-secret]
```

Example:
```
obsidian_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U
```

### Security Details

- **Length**: 32 characters + 8 character prefix = 40 total
- **Encoding**: URL-safe Base64
- **Bits**: 256-bit security equivalent
- **Generation**: Cryptographically secure random (secrets.token_urlsafe)

---

## Audit Trail

Track API key usage:

```bash
# View key statistics
curl http://localhost:8009/api/keys/list | jq '.keys[] | {name, requests_count, last_used}'

# Example output
{
  "name": "Production API Key",
  "requests_count": 1250,
  "last_used": "2026-06-14T14:30:00"
}
```

---

## Integration Examples

### Docker Compose with Auth

```yaml
services:
  obsidian-brain:
    image: obsidian-brain:latest
    environment:
      BRAIN_AUTH_REQUIRED: "true"
      BRAIN_API_KEY_DIR: /etc/obsidian-brain/api_keys
    volumes:
      - brain-keys:/etc/obsidian-brain/api_keys
    ports:
      - "8009:8009"

volumes:
  brain-keys:
```

### CI/CD with API Keys

```bash
# GitHub Actions
- name: Generate API Key
  run: |
    curl -X POST http://localhost:8009/api/keys/generate \
      -H "Content-Type: application/json" \
      -d '{"name": "CI/CD"}' > key.json
    echo "API_KEY=$(jq -r '.api_key' key.json)" >> $GITHUB_ENV

- name: Run Tests
  env:
    OBSIDIAN_API_KEY: ${{ env.API_KEY }}
  run: python test_suite.py
```

---

## Migration Guide

### From Open Access to Authenticated Access

```bash
# 1. Start with auth disabled (current state)
export BRAIN_AUTH_REQUIRED=false

# 2. Generate API keys for all clients
for client in mobile-app web-dashboard; do
  curl -X POST http://localhost:8009/api/keys/generate \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$client\"}" > $client-key.json
done

# 3. Update all clients to use API keys
# (test thoroughly before enabling auth)

# 4. Enable authentication
export BRAIN_AUTH_REQUIRED=true
brain serve --host 0.0.0.0 --port 8009

# 5. Monitor and verify all clients working
# Remove API_KEY entries from error logs after verification
```

---

## Support

For issues with authentication:

- Check API key format: Should start with `obsidian_`
- Verify header name: Default is `X-API-Key`
- Check auth status: `/api/auth/status`
- Review logs: `journalctl -u obsidian-brain -f`
- GitHub Issues: https://github.com/harimsd07/obsidian-brain/issues

---

## License

MIT License - See LICENSE file for details
