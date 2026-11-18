#!/usr/bin/env bash
set -euo pipefail

# A small shop project and a design file for a new refund export. The design has five planted defects, one for each
# role of /audit-team: R3 has no acceptance case, step 4 has a condition that no test can check, the new module breaks
# the name pattern of the handlers, the design claims a retry that StorageClient.upload() does not do, and the sections
# Retention and Cleanup give two different ages.
lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"

fixture_init

fixture_write README.md <<'EOF'
# Shop exports

Each export of the shop has one handler. The handler of the export `<name>` is the class `<Name>ExportHandler` in the
module `app/handlers/<name>_export_handler.py`. The handlers upload their files with `app/storage_client.py`.
EOF

fixture_write app/__init__.py <<'EOF'
EOF

fixture_write app/handlers/__init__.py <<'EOF'
EOF

fixture_write app/storage_client.py <<'EOF'
"""The client of the object storage."""


class UploadError(Exception):
    """An upload failed."""


class StorageClient:
    """Uploads files to a bucket of the object storage."""

    def __init__(self, transport):
        self._transport = transport

    def upload(self, bucket, path):
        """Upload one file with one request. Raise UploadError if the request fails."""
        with open(path, "rb") as handle:
            response = self._transport.put(bucket, path, handle.read())
        if response.status != 200:
            raise UploadError(f"the upload of {path} failed with status {response.status}")
EOF

fixture_write app/handlers/order_export_handler.py <<'EOF'
"""Exports the orders of one day to a CSV file."""
import csv


class OrderExportHandler:
    """Writes the orders of one day to exports/orders-YYYY-MM-DD.csv and uploads the file."""

    def __init__(self, database, storage):
        self._database = database
        self._storage = storage

    def run(self, day):
        path = f"exports/orders-{day}.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["order_id", "amount", "created_at"])
            writer.writerows(self._database.orders_of(day))
        self._storage.upload("finance-exports", path)
        return path
EOF

fixture_write app/handlers/invoice_export_handler.py <<'EOF'
"""Exports the invoices of one day to a CSV file."""
import csv


class InvoiceExportHandler:
    """Writes the invoices of one day to exports/invoices-YYYY-MM-DD.csv and uploads the file."""

    def __init__(self, database, storage):
        self._database = database
        self._storage = storage

    def run(self, day):
        path = f"exports/invoices-{day}.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["invoice_id", "order_id", "amount", "created_at"])
            writer.writerows(self._database.invoices_of(day))
        self._storage.upload("finance-exports", path)
        return path
EOF

fixture_write docs/design/refund-export.md <<'EOF'
# Design: the refund export

## Goal

The shop exports the refunds of each day to one CSV file, in the same way as the order export and the invoice export.

## Requirements

- R1: The job writes each refund of the day to the file `exports/refunds-YYYY-MM-DD.csv`.
- R2: Each file has a header row with the columns `refund_id`, `order_id`, `amount`, and `created_at`.
- R3: A refund of a part of an order has its own row, with the amount of that part only.
- R4: The job uploads each file to the storage bucket `finance-exports`.

## Acceptance cases

- A1 (R1): A day with 3 refunds gives one file with the header row and 3 rows.
- A2 (R2): The header row of each file is `refund_id,order_id,amount,created_at`.
- A4 (R4): After the job, the bucket `finance-exports` holds the file of the day.

## Components

- The new module `app/handlers/RefundExporter.py` holds the class `RefundExportManager`. It reads the refunds of the
  day and writes the CSV file.
- The upload uses `StorageClient.upload()` of `app/storage_client.py`. That method already retries a failed upload
  three times.

## Steps of the job

1. Read the refunds of the day from the table `refunds`.
2. Write the CSV file.
3. Upload the file with `StorageClient.upload()`.
4. If the upload fails after the retries of `StorageClient`, wait until the network is stable. Then go to step 3.

## Retention

The export host keeps each refund file for 30 days, because the finance team can ask for an old file again.

## Cleanup

A nightly cleanup job deletes each refund file on the export host that is older than 7 days.
EOF

fixture_commit "the shop exports and the design of the refund export"
