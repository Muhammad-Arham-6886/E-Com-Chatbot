# Platform Security, Guardrails & Audit Logging Guide (Phase 12)

The **Platform Security & Guardrails Engine** provides enterprise-grade protection against adversarial prompt injections, ensures zero leakage of customer PII and API keys, and maintains an immutable audit trail of high-security actions.

---

## 1. Dual-Layer Guardrail Architecture

```
                                [ Visitor / User Input ]
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │     Input Shield (Pre-LLM Filter)      │
                       └────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       [ Prompt Injection Scan ]                       [ Sensitive Data Redaction ]
   • Instruction Override ("Ignore rules")        • Credit Cards ➔ [REDACTED_CARD_NUMBER]
   • System Extraction ("Dump prompt")            • API Keys ➔ [REDACTED_API_KEY]
   • Jailbreak ("You are now DAN")                • Passwords ➔ [REDACTED_SECRET]
   • Safety Bypass ("No limits")                  • SSNs ➔ [REDACTED_SSN]
                    │                                             │
      ┌─────────────┴─────────────┐                               ▼
      ▼                           ▼                     [ Clean Redacted Input ]
[ Detected ]                 [ Clean ]                            │
      │                           │                               ▼
      ▼                           └────────────────────▶ [ Local Ollama LLM / RAG ]
1. Log Security Audit Alert                                       │
2. Return Safe Refusal                                            ▼
                                               ┌────────────────────────────────────────┐
                                               │     Output Sanitizer (Post-LLM)        │
                                               └────────────────────────────────────────┘
                                                                  │
                                                      • Strips <script> XSS tags
                                                      • Strips javascript: URIs
                                                      • Removes onclick/eval attrs
                                                                  │
                                                                  ▼
                                                      [ Safe Visitor Output ]
```

---

## 2. Immutable Audit Logging

High-security and platform configuration events are stored in `audit_logs`:

| Action Code | Trigger |
| :--- | :--- |
| `SECURITY_ALERT_PROMPT_INJECTION` | Triggered when a malicious prompt injection is detected and neutralized. |
| `USER_LOGIN` / `USER_REGISTER` | User authentication events. |
| `WEBSITE_CREATED` / `WEBSITE_DELETED` | Website tenant provisioning and deletions. |
| `COMMERCE_CONNECTED` / `DISCONNECTED` | WooCommerce REST API key updates. |
| `SUBSCRIPTION_CHANGED` | Organization subscription plan upgrades / downgrades. |

---

## 3. REST API Reference (`/api/v1/security`)

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/security/audit-logs?org_id={id}&page=1&limit=50` | Retrieve paginated audit logs with search and action filters | `ADMIN`+ |
| `POST` | `/api/v1/security/test-guardrails?org_id={id}` | Security playground to test prompt injection detection and PII redaction | `VIEWER`+ |
