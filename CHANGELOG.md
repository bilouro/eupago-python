# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `EupagoClient` with sync and async support
- MB WAY payment: `create_payment`, `authorize`, `capture`
- Webhook parsing (v1.0 GET + v2.0 POST) with HMAC signature verification
- Typed exception hierarchy
- PII redaction in logs
- Retry with exponential backoff (GET requests only)
