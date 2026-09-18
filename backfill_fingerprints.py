from google.cloud import storage, firestore
import hashlib

BUCKET_NAME = "digital-document-verification-455749068291"

db = firestore.Client()
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

updated = 0
skipped = 0
failed = 0

for snap in db.collection("documents").stream():

    data = snap.to_dict()

    # Keep existing fingerprints.
    if data.get("file_hash"):
        skipped += 1
        continue

    storage_path = (
        data.get("storage_path")
        or data.get("storagePath")
        or ""
    )

    filename = (
        data.get("filename")
        or data.get("fileName")
        or snap.id
    )

    if not storage_path:
        print(
            f"SKIP: {filename} -> no storage path"
        )
        failed += 1
        continue

    try:
        blob = bucket.blob(storage_path)

        if not blob.exists():
            print(
                f"SKIP: {filename} -> file not found in storage"
            )
            failed += 1
            continue

        file_bytes = blob.download_as_bytes()

        file_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        snap.reference.update({
            "file_hash": file_hash
        })

        print(
            f"UPDATED: {filename} -> {file_hash}"
        )

        updated += 1

    except Exception as e:

        print(
            f"ERROR: {filename} -> {e}"
        )

        failed += 1


print()
print(
    f"Backfill complete."
)
print(
    f"Updated: {updated}"
)
print(
    f"Already had fingerprint: {skipped}"
)
print(
    f"Failed: {failed}"
)
