# Security Policy

## Supported Versions

Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Security Features

CronPulse Community Edition includes the following security measures:

### Authentication & Authorization
- **Password Hashing**: Argon2id for secure password storage
- **JWT Tokens**: Secure session management with configurable secrets
- **API Key Authentication**: Hashed API keys for programmatic access
- **Rate Limiting**: Built-in protection against brute force attacks
  - Login: 10 attempts per minute
  - Signup: 5 attempts per hour
  - General API: 100 requests per minute

### Input Validation
- **Email Validation**: RFC-compliant email validation using Pydantic EmailStr
- **URL Validation**: HTTP/HTTPS URL validation for webhooks
- **XSS Prevention**: HTML tag sanitization in user inputs
- **Length Constraints**: Maximum limits on all text fields
- **SQL Injection Prevention**: All queries use SQLAlchemy ORM with parameterized statements

### Transport Security
- **HTTPS Recommended**: Always use HTTPS in production
- **CORS Configuration**: Configurable Cross-Origin Resource Sharing
- **Security Headers**: 
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security` (HSTS)

### Data Protection
- **Secret Management**: SMTP passwords and API keys stored with `is_secret` flag
- **JWT Secret Auto-Generation**: Secure random secrets generated if not provided
- **Environment Variable Priority**: Environment variables override database settings

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: [your-security-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline
- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-14 days
  - Medium: 14-30 days
  - Low: Next release cycle

## Security Best Practices

### Deployment

1. **Use Strong JWT Secrets**
   ```bash
   # Generate a secure secret
   openssl rand -hex 32
   ```

2. **Enable HTTPS**
   - Use a reverse proxy (nginx, Caddy, Traefik)
   - Obtain SSL certificates (Let's Encrypt recommended)

3. **Restrict CORS**
   ```bash
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

4. **Regular Updates**
   ```bash
   docker compose pull
   docker compose up -d
   ```

5. **Secure SMTP Credentials**
   - Use app passwords for Gmail
   - Restrict SMTP server access by IP if possible
   - Never commit credentials to version control

### Network Security

1. **Firewall Rules**
   - Only expose port 8000 (or your chosen port)
   - Use a reverse proxy for SSL termination

2. **Database**
   - SQLite file should not be publicly accessible
   - Regular backups recommended

3. **Monitoring**
   - Monitor for unusual API activity
   - Set up alerts for failed authentication attempts

### Docker Security

1. **Run as Non-Root** (Future improvement)
   - Currently runs as root in container
   - Use `--user` flag or modify Dockerfile

2. **Read-Only Filesystem** (Optional)
   ```yaml
   security_opt:
     - no-new-privileges:true
   read_only: true
   tmpfs:
     - /tmp
   ```

3. **Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```

## Known Limitations

- SQLite has no built-in user authentication
- No 2FA support (planned for future)
- No session revocation mechanism
- Rate limiting uses in-memory storage (resets on restart)

## Security Checklist for Production

- [ ] Set secure JWT_SECRET
- [ ] Enable HTTPS
- [ ] Configure CORS with specific origins
- [ ] Use strong admin password
- [ ] Regular backups of SQLite database
- [ ] Monitor logs for suspicious activity
- [ ] Keep Docker images updated
- [ ] Review and restrict exposed ports
- [ ] Use app passwords for email services
- [ ] Enable firewall rules

## Disclosure Policy

We follow responsible disclosure practices:

1. Security researchers have 90 days to report before public disclosure
2. We will acknowledge receipt within 48 hours
3. We will provide regular updates on fix progress
4. We will credit reporters (unless they prefer anonymity)
5. We will coordinate disclosure timing with the reporter

## Security Updates

Security updates are released as:
- **Critical**: Immediate patch release
- **High**: Patch within 7 days
- **Medium/Low**: Next regular release

Subscribe to releases on GitHub to stay informed.

---

Last updated: January 28, 2026
