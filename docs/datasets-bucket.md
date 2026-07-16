# Datasets Bucket (`gs://painpan-datasets`)

Read-only GCS bucket holding all Reddit datasets. Mounted on Cloud Run at
`/app/data` (volume mount configured in `deploy.sh` and `.github/workflows/deploy.yml`).
In local dev the same files live under `data/` in the project root.

---

## How to access the bucket

### Quick facts
- **Bucket:** `gs://painpan-datasets`
- **Project:** `agenticaicolumbia`
- **Location:** `US` (multi-region), storage class `STANDARD`
- **Access:** uniform bucket-level access; `painpan-sa@agenticaicolumbia.iam.gserviceaccount.com`
  has `roles/storage.objectAdmin` project-wide (the Cloud Run service account)
- **Mount on Cloud Run:** read-only at `/app/data` via
  `--add-volume=mount-path=/app/data,type=cloud-storage,bucket=painpan-datasets,readonly=true`

### From this Windows machine (IMPORTANT)
On this box, gcloud run **directly** through Git-Bash/MSYS silently swallows output and
returns a false exit code 0. **Always route gcloud through `cmd.exe //c`** (see
`LEARNING.md` → "MSYS/Git-Bash silently swallows gcloud output"):

```bash
# List everything (newest verification)
cmd.exe //c "gcloud storage ls gs://painpan-datasets/ --recursive --readable-sizes"

# Total size
cmd.exe //c "gcloud storage du gs://painpan-datasets/ --summarize"

# Download one object
cmd.exe //c "gcloud storage cp gs://painpan-datasets/linanqiu/linanqiu_dataset.json ."

# NOTE: source paths with spaces get mangled through bash → cmd.exe.
# Copy the file to a no-spaces path first, then upload from there.
```

### From any other machine (Linux/macOS/Cloud Shell)
```bash
gcloud storage ls gs://painpan-datasets/ --recursive --readable-sizes
gcloud storage cp gs://painpan-datasets/linanqiu/linanqiu_dataset.json .
```

### From Python (app code / scripts)
The Cloud Run service account is auto-authenticated. Locally, ADC must point at
`agenticaicolumbia` (run `gcloud auth application-default login` as
`victor.tenneroni@gmail.com`; the local ADC currently defaults to a different project):

```python
from google.cloud import storage
client = storage.Client(project="agenticaicolumbia")
bucket = client.bucket("painpan-datasets")
blob = bucket.blob("linanqiu/linanqiu_dataset.json")
print(blob.exists(), blob.size)
```

### At runtime on Cloud Run
No client needed — the bucket is mounted as a filesystem. Code reads plain paths:
- `/app/data/pushshift/RS_2018-01_00.parquet` (primary; `app/pushshift/client.py` also checks the legacy `/app/data/arcticshift/` path as a fallback safety net)
- `/app/data/linanqiu/linanqiu_dataset.json`
- `/app/data/smallsample/*.json`
- `/app/data/subreddit_descriptions_*.json`

---

# Changelog

## 2026-07-15 — initial load (62 objects, ~2.4 GB)

Bucket created and all datasets uploaded. `huggingface_hub` runtime dependency
removed from `app/arcticshift/client.py` (now `app/pushshift/client.py` — the
data source was renamed to `pushshift` on 2026-07-15; Parquet is still read
from the mount).

**On the bucket:**

Runtime (read by app code):
- `arcticshift/RS_2018-01_00.parquet` — 1.74 GB (Pushshift Reddit, RS = submissions, Jan 2018)
- `linanqiu/linanqiu_dataset.json` — 7.3 MB (linanqiu/reddit-dataset, Feb 2016 era)
- `smallsample/gaming_test_20260416_105527.json` — sample gaming posts
- `smallsample/sample_posts.json` — default sample
- `smallsample/sample_posts_20260407_145826.json`
- `smallsample/sample_posts_20260407_150257.json`
- `smallsample/sample_posts_20260407_150700.json`
- `smallsample/sample_posts_20260416_104801.json`
- `smallsample/subreddit_descriptions_20260414_091545.json` — 304 KB
- `subreddit_descriptions_20260414_091545.json` — 304 KB (root copy; code reads `data/subreddit_descriptions_*.json`)

Archive (not read at runtime, kept for provenance/re-derivation):
- `arcticshift/archive/RS_2012-01_00.parquet` — 108 MB (orphan; not referenced by current code)
- `linanqiu/raw/*.csv` — 51 source CSVs (github.com/linanqiu/reddit-dataset raw files, 687 MB total)

**Bucket created** this date with:
```
gcloud storage buckets create gs://painpan-datasets \
  --project=agenticaicolumbia --location=US --uniform-bucket-level-access
```

---

## 2026-07-15 — code-side rename: `arcticshift` → `pushshift`

The data source identifier was renamed from `arcticshift` to `pushshift` across
the codebase and UI. The upstream is `fddemarco/pushshift-reddit` (HuggingFace),
not the separate `RoyalFortune24/The-Arctic-Shift` dataset — the old name was a
misnomer.

**What changed in code:**
- `DataSource` enum value: `"arcticshift"` → `"pushshift"` (frontend + backend)
- `app/arcticshift/` → `app/pushshift/` (Python module)
- `ArcticShiftClient` → `PushshiftClient` (Python class)
- `_fetch_arcticshift` → `_fetch_pushshift` (router)
- All UI labels: "Arctic Shift" → "Pushshift"

**What did NOT change (yet):**
- **GCS bucket prefix** is still `arcticshift/`. `app/pushshift/client.py` has a
  backward-compat fallback that reads from `data/arcticshift/` if `data/pushshift/`
  is absent, with a warning log. To finish the rename on the infra side:
  ```bash
  cmd.exe //c "gcloud storage mv gs://painpan-datasets/arcticshift gs://painpan-datasets/pushshift"
  cmd.exe //c "gcloud storage mv gs://painpan-datasets/pushshift/archive gs://painpan-datasets/pushshift/archive"
  ```
  (the second move preserves the archive subdir).
- **Historical run reports** in `output/reports/*_arcticshift*/` keep the old
  name as immutable artifacts.

---

## 2026-07-15 — infra-side rename: bucket prefix `arcticshift/` → `pushshift/`

Completed the rename started above. Same-bucket `gcloud storage mv` (server-side
rewrite, no re-upload). 62 objects, same total size; only the two Parquet paths moved.

**On the bucket now (current state):**

Runtime (read by app code):
- `pushshift/RS_2018-01_00.parquet` — 1.74 GB (was `arcticshift/RS_2018-01_00.parquet`)
- `linanqiu/linanqiu_dataset.json` — 7.3 MB
- `smallsample/*.json` — 7 files
- `subreddit_descriptions_20260414_091545.json` — 304 KB (root copy)

Archive:
- `pushshift/archive/RS_2012-01_00.parquet` — 108 MB (was `arcticshift/archive/...`)
- `linanqiu/raw/*.csv` — 51 source CSVs

**Moves run:**
```bash
cmd.exe //c "gcloud storage mv gs://painpan-datasets/arcticshift/RS_2018-01_00.parquet gs://painpan-datasets/pushshift/RS_2018-01_00.parquet"
cmd.exe //c "gcloud storage mv gs://painpan-datasets/arcticshift/archive/RS_2012-01_00.parquet gs://painpan-datasets/pushshift/archive/RS_2012-01_00.parquet"
```

**Kept as safety net (not removed):** `app/pushshift/client.py` still checks the
legacy `data/arcticshift/` path as a fallback if `data/pushshift/` is absent, so a
revert is possible without code changes. Local `data/arcticshift/` was renamed to
`data/pushshift/`.
