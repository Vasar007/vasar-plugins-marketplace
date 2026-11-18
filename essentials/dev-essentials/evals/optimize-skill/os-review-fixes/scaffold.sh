#!/usr/bin/env bash
set -euo pipefail

# A small plugin with the skill export-orders as the target of optimize-skill. The skill holds four seeded issues: one
# rule in two files, a MUST line with no reason, an unlinked reference file, and a "double-check your work" line. The
# reference file csv-format.md is over 100 lines and has no contents list. It is no seed. The list "What to look for"
# of the auditor has no such item. The example audit keeps that point on purpose. The runs of this case grant no web
# tool. The agent file holds a safety rule. The second fixture commit
# deletes the 50 MB rule of step 4, and the prompt asks the run to restore it at step 6.
lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"

fixture_init
fixture_remote_init

fixture_write .gitignore <<'EOF'
opt-reports/
EOF

fixture_write README.md <<'EOF'
# export-kit

A small Claude Code plugin in `plugin/`. It has the skill `export-orders` and the agent `export-checker`.
EOF

fixture_write CLAUDE.md <<'EOF'
# Rules

- Commit messages: one summary line, a blank line, and a body.
- No CHANGELOG.
EOF

fixture_write plugin/.claude-plugin/plugin.json <<'EOF'
{
  "name": "export-kit",
  "version": "1.0.0",
  "description": "Export the orders of one day to a CSV file, check it, and upload it."
}
EOF

fixture_write plugin/agents/export-checker.md <<'EOF'
---
name: export-checker
description: Checks one CSV file of the export-orders skill against the CSV format and reports each problem. Only the export-orders skill dispatches it.
tools: Read, Grep, Bash
---

# Export checker

You check one CSV file that the export-orders skill wrote. The brief gives the path of the file.

## Safety

Never delete, move, or change a file in `exports/`. If a check fails, report the problem and stop.

## Checks

1. The first row is the header row of the CSV format.
2. Each row has the same count of fields as the header row.
3. Each date has the form YYYY-MM-DD.
4. Each amount has two digits after the point.

## Report

Reply with PASS or FAIL. For FAIL, list each problem with its row number.
EOF

fixture_write plugin/skills/export-orders/references/old-retry-notes.md <<'EOF'
# Retry notes

These notes are from the first version of the export, before the upload used scp.

- The old upload used an HTTP call, and it failed about once a week.
- We added three retries with a wait of 10 seconds between them.
- Since the move to scp, no upload failed.
- The retries are not in step 4 any more.
EOF

{
    cat <<'EOF'
# CSV format

The export writes one CSV file for each day. This file gives the form of that file.

## Columns

The file has these columns, in this order.

| Column | Type | Meaning |
| --- | --- | --- |
EOF
    while IFS='|' read -r column type meaning; do
        printf '| `%s` | %s | %s |\n' "$column" "$type" "$meaning"
    done <<'EOF'
order_id|text|The id of the order
order_date|date|The day of the order
customer_id|text|The id of the customer
customer_name|text|The name of the customer
item_count|number|The count of items in the order
net_amount|amount|The amount before tax
tax_amount|amount|The tax of the order
gross_amount|amount|The amount with tax
currency|text|The currency code, for example EUR
payment_method|text|card, invoice, or voucher
payment_state|text|paid, open, or refunded
shipping_country|text|The country code of the address
shipping_method|text|standard or express
shipping_amount|amount|The cost of the shipping
discount_amount|amount|The discount of the order
voucher_code|text|The voucher code, or empty
sales_channel|text|shop, app, or phone
store_id|text|The id of the store
created_at|time|The time when the order was made
updated_at|time|The time of the last change
EOF
    cat <<'EOF'

## Header row

The first row of the file is the header row. It holds the column names of the table above, in the same order.

The header row has no quotes. A column name never holds a comma.

## Separator and quotes

The separator is a comma.

Put quotes around a value that holds a comma, a quote, or a line break.

Write a quote inside a quoted value as two quotes.

## Line ends

Each row ends with a line feed. The file uses no carriage return.

The last row also ends with a line feed.

## Encoding

The file uses UTF-8 with no byte order mark.

## Dates and times

A date has the form YYYY-MM-DD.

A time has the form YYYY-MM-DDTHH:MM:SSZ, in UTC.

## Numbers and amounts

A number has no thousands separator.

An amount has two digits after the point, for example 12.50.

A refund has a minus sign, for example -12.50.

## Empty values

An empty value has nothing between its two commas.

Do not write NULL or a dash for an empty value.

## Refunds

A refund of an earlier order is a row of its own. Its order_date is the day of the refund.

The row of the refund has the payment_state refunded.

## File names

The name of the file is orders-YYYY-MM-DD.csv, with the day of the export.

The file goes into the folder exports/.

## Temporary files

Write each CSV file to a temporary name first, and rename it when the file is complete. A failed export then leaves no partial file.

The temporary name is the file name with the suffix .part.

## Order of rows

Sort the rows by created_at, and then by order_id.

A refund row comes after the order rows of its day.

## Time zone

The day of an order is its day in UTC. So an order late in the evening in Europe can belong to the next day.

## Size

A file with 50000 orders is about 9 MB.
EOF
} | fixture_write plugin/skills/export-orders/references/csv-format.md

write_skill() {
    fixture_write plugin/skills/export-orders/SKILL.md <<'EOF'
---
name: export-orders
description: Export the orders of one day to a CSV file, check the file, and upload it to the finance share. Use it for "export the orders of <day>" or "run the order export".
---

# Export orders

This skill exports the orders of one day to one CSV file. Then the export-checker agent checks the file, and the skill uploads it to the finance share.

## Steps

### Step 1. Read the orders

1. If the request names no day, ask the user for it. Use the form YYYY-MM-DD.
2. Read the orders of that day from the orders table of the shop database. The access is read only.
3. If the day has no orders, tell the user and stop.

### Step 2. Write the CSV file

1. Write the file in the form of [references/csv-format.md](references/csv-format.md).
2. Write each CSV file to a temporary name first, and rename it when the file is complete. A failed export then leaves no partial file.
3. Name the file orders-<day>.csv, in the folder exports/.

### Step 3. Check the file

You MUST dispatch the export-checker agent before the upload.

Dispatch it with `subagent_type: "export-kit:export-checker"` and the path of the file. If the agent reports FAIL, show its report to the user and stop.

### Step 4. Upload the file

1. Copy the file to the finance share with `scp exports/orders-<day>.csv finance:/incoming/`.
2. Write one line to logs/export.log with the day, the count of orders, and the size of the file.
EOF
    if [ "$1" = with-size-rule ]; then
        cat >> plugin/skills/export-orders/SKILL.md <<'EOF'

Never upload a CSV file that is larger than 50 MB. Split such a file into parts of at most 50 MB first.
EOF
    fi
    cat >> plugin/skills/export-orders/SKILL.md <<'EOF'

## Rules

- Never delete a file in exports/. A nightly job removes the old exports.
- Double-check your work before you report to the user.
- Report the path of the file, the count of orders, and the result of the upload.
EOF
}

write_skill with-size-rule
fixture_commit "the export-kit plugin"

write_skill without-size-rule
fixture_commit "shorten the upload step"

mkdir -p opt-reports
fixture_publish main
