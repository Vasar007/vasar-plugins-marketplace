---
type: llm
focus: last_message
---

The text under test is a review report of the design file `docs/design/refund-export.md`. The design names the new module `app/handlers/RefundExporter.py` and the new class `RefundExportManager`. Each handler of the project follows another pattern: the module `app/handlers/<name>_export_handler.py` holds the class `<Name>ExportHandler`. So the expected names are `refund_export_handler.py` and `RefundExportHandler`.

If the report says that the module name or the class name breaks the pattern of the handlers, the result is PASS. If the report proposes the name `refund_export_handler.py` or `RefundExportHandler`, the result is also PASS. The finding can be in any bucket of the report. Otherwise the result is FAIL.
