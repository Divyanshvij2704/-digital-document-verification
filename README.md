# Digital Document Verification System

A cloud-based document verification platform that enables users to securely submit documents and administrators to review, verify, reject, and audit document records.

The system uses SHA-256 fingerprinting for document integrity, duplicate detection, verification IDs, QR-based public verification, audit logging, and downloadable verification certificates.

## Live Demo

**Application:**  
https://document-verification-455749068291.asia-south1.run.app

**GitHub Repository:**  
https://github.com/Divyanshvij2704/-digital-document-verification

---

## Features

### User Features

- Firebase Authentication
- User document submission
- File upload to Google Cloud Storage
- SHA-256 document fingerprint generation
- Duplicate document detection
- Document status tracking
- Public verification through Verification ID
- QR-based verification
- Downloadable verification certificate PDF

### Administrator Features

- Secure administrator authentication
- Dashboard with document statistics
- Pending document review
- Document verification and rejection
- Rejection reason recording
- Reviewer tracking
- Verification timestamps
- SHA-256 fingerprint visibility
- Verification ID generation
- Audit history
- Document viewing
- Verification certificate generation

### Verification Features

Each verified document receives a unique Verification ID:

```text
DV-2026-A1EDC67E
