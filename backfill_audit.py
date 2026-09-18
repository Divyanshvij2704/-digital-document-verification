from google.cloud import firestore
from datetime import datetime

db = firestore.Client()

# Existing audit events, so this script is safe to run more than once.
existing = set()

for snap in db.collection("audit_logs").stream():
    data = snap.to_dict()
    existing.add(
        (
            data.get("document_id", ""),
            data.get("action", "")
        )
    )

created = 0

for snap in db.collection("documents").stream():

    data = snap.to_dict()

    document_id = snap.id
    filename = (
        data.get("filename")
        or data.get("fileName")
        or ""
    )

    uploaded = (
        data.get("uploaded")
        or data.get("uploadedAt")
    )

    reviewed = (
        data.get("reviewed")
        or data.get("reviewedAt")
    )

    status = data.get(
        "status",
        "Pending"
    )

    owner = (
        data.get("owner_email")
        or data.get("ownerEmail")
        or data.get("user")
        or "User"
    )

    reviewer = data.get(
        "reviewer",
        "Admin"
    )

    if reviewer == "admin@yourdomain.com":
        reviewer = "Admin"

    # Backfill upload event
    if (
        document_id,
        "UPLOAD"
    ) not in existing and uploaded:

        db.collection(
            "audit_logs"
        ).add({
            "action": "UPLOAD",
            "actor": owner,
            "document_id": document_id,
            "filename": filename,
            "details": "Document uploaded",
            "timestamp": uploaded
        })

        created += 1

    # Backfill review event
    if (
        status in ("Verified", "Rejected")
        and reviewed
    ):

        action = (
            "VERIFIED"
            if status == "Verified"
            else "REJECTED"
        )

        key = (
            document_id,
            action
        )

        if key not in existing:

            reason = (
                data.get("rejection_reason")
                or data.get("rejectionReason")
                or ""
            )

            details = (
                "Document verified"
                if action == "VERIFIED"
                else f"Document rejected: {reason}"
            )

            db.collection(
                "audit_logs"
            ).add({
                "action": action,
                "actor": reviewer,
                "document_id": document_id,
                "filename": filename,
                "details": details,
                "timestamp": reviewed
            })

            created += 1

print(f"Backfill complete. Created {created} audit events.")
