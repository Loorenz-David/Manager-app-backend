# Connecteam user mapping CSV

This folder holds the owner-provided input for the one-time manual mapping script.

Canonical format:

```csv
userId,firstName,lastName
123456,Andrii,
```

The reader also accepts UTF-8 BOM, comma or semicolon delimiters, quoted fields, and
header spelling variants that differ only by case, spaces, or underscores. Extra columns
are ignored. The file contains personal data and must never be committed if this project
is placed under version control. The UI-export backup is subject to the same rule.

Run the workflow from `backend/app`:

```bash
python -m scripts.backfill.map_connecteam_user_ids --dry-run
python -m scripts.backfill.map_connecteam_user_ids --execute
```

Review every dry-run row before applying. Afterward, verify the mapping with a SQL join
between `users` and `user_work_profiles` where `connecteam_user_id IS NOT NULL`, then
rerun the dry-run and confirm the rows are `already_mapped_same_id`.
