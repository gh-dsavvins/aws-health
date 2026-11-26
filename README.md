# aws-health

Proof of concept: a serverless patient-records service on AWS, written in Python.
All data in it is invented.

## Try it

Open https://d24qxa41c7cgzc.cloudfront.net/index.html and log in with the test user:

- Email: `doctor@example.com`
- Password: `Password1@`

Press **Open** on a patient to see the bills and the audit trail.

## What it shows

- **API:** API Gateway (HTTP API) in front of Lambda functions, Python 3.13.
- **Login:** Cognito user pool, OAuth2 authorization code flow with PKCE. API Gateway
  verifies the JWT access token on every route except `/health`.
- **Data:** DynamoDB tables encrypted with a customer-managed KMS key, with
  point-in-time recovery.
- **Simultaneous edits:** each record has a `version`. An update is a conditional
  write that succeeds only if the version is unchanged; the loser gets `409`.
- **Synchronization:** bills live in two tables. A function reads both DynamoDB
  streams and keeps `bill_count` and `billed_sum_cents` on the patient record,
  using atomic `ADD` so simultaneous bills all count, and a processed-events table
  so a redelivered event is not counted twice.
- **Audit:** a write-only function records every change from all three table
  streams, with the before and after images and the caller's IP address. A
  separate read-only function serves it.
- **Web page:** a single HTML file in a private S3 bucket behind CloudFront.

## Layout

| Path | Content |
|---|---|
| `template.yaml` | All infrastructure (AWS SAM) |
| `src/patients/` | Patients API |
| `src/bills/` | Bills API for both bills tables |
| `src/totals/` | Stream consumer that maintains the totals |
| `src/audit/` | Stream consumer that writes the audit table |
| `src/audit_read/` | Audit read API |
| `web/index.html` | The page |

## Deploy

```bash
sam build && sam deploy
aws s3 cp web/index.html s3://<WebBucketName output>/
```

`web/index.html` has the API address, login domain and client id of this
deployment at the top of its script; change them for another account.
