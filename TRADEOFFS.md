# Tradeoffs — Three Things Deliberately Not Built

## 1. No background task queue (Celery + Redis)

**What we built instead:** Synchronous file parsing in the HTTP request cycle.

**Why we skipped it:** Celery requires a Redis or RabbitMQ broker, a separate
worker process, and significantly more infrastructure configuration. On Render's
free tier this would mean three separate services (web, worker, Redis) with
non-trivial coordination. For a prototype handling demo-sized files (< 1000 rows),
synchronous parsing completes well within the 30s request timeout.

**What breaks in production:** A client uploading a 50,000-row SAP export will
hit the timeout. The batch would be left in 'processing' status with no way to
recover without manual DB intervention.

**What we'd build next:** Move parsing to a Celery task. UploadView creates the
batch and immediately returns a 202 Accepted with the batch ID. The frontend
polls `GET /api/batches/{id}/` until status transitions from 'processing' to
'completed' or 'failed'. This is the correct pattern for any file processing.

---

## 2. No emission factor versioning

**What we built instead:** Emission factors hardcoded as constants in `normalizer.py`
(DEFRA 2023).

**Why we skipped it:** Factor versioning requires an `EmissionFactor` model with
`valid_from` / `valid_to` date range, a `version` string, and a `source` citation.
It also requires a re-normalization job that can recompute historical records when
factors are updated. That's a non-trivial feature that would take more than the
time available.

**What breaks in production:** DEFRA updates its conversion factors annually
(usually in June). When that happens, any records ingested before the update
use the old factor — which is actually correct behavior for historical data.
The problem is there's no way to see which factor version was applied to which
record, making auditor verification difficult.

**What we'd build next:** An `EmissionFactor` model (scope, category, unit,
factor_value, valid_from, valid_to, source_document, version). The normalizer
looks up the factor valid on the record's `activity_start` date. The
EmissionRecord stores the FK to the specific EmissionFactor row used.

---

## 3. No role-based access control enforcement beyond authentication

**What we built instead:** Users have a `role` field (admin/analyst/auditor)
but views don't check it — any authenticated user can approve, reject, lock,
or edit any record.

**Why we skipped it:** Proper RBAC requires either Django's permission framework
(add_emissionrecord, change_emissionrecord, etc.) with custom permissions per
action, or a decorator/mixin that checks `request.user.role`. This adds a
layer of view complexity (and test complexity) that wasn't the focus of this
prototype — the data model and ingestion pipeline were.

**What breaks in production:** An auditor (read-only role) can currently approve
or edit records they're supposed to only view. An analyst can lock records that
should only be lockable by an admin.

**What we'd build next:** A `RoleRequired` mixin checking `request.user.role`
against an allowed list per view. Auditors get GET only. Analysts get approve/reject/flag.
Admins get lock/unlock and user management.