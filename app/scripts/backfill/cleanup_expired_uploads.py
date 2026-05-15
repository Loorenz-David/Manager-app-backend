"""
Cleanup script: mark expired PendingUpload rows and optionally delete their
storage objects.  Run manually or via a scheduled job.

Usage:
    python scripts/backfill/cleanup_expired_uploads.py [--delete-objects] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, update

from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.services.infra.storage import get_storage_client


async def run(delete_objects: bool, dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    async with get_db_session() as session:
        stmt = select(PendingUpload).where(
            PendingUpload.status == PendingUploadStatusEnum.PENDING,
            PendingUpload.expires_at < now,
        )
        rows = (await session.execute(stmt)).scalars().all()
        print(f"Found {len(rows)} expired uploads")
        for upload in rows:
            if delete_objects:
                try:
                    get_storage_client().delete_object(upload.storage_key)
                    print(f"  deleted object: {upload.storage_key}")
                except Exception as exc:
                    print(f"  WARN delete failed {upload.storage_key}: {exc}")
            if not dry_run:
                upload.status = PendingUploadStatusEnum.EXPIRED
        if not dry_run:
            await session.commit()
            print(f"Marked {len(rows)} uploads as expired")
        else:
            print("[dry-run] no changes committed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delete-objects", action="store_true", help="also delete storage objects")
    parser.add_argument("--dry-run", action="store_true", help="scan only, no DB changes")
    args = parser.parse_args()
    asyncio.run(run(args.delete_objects, args.dry_run))
