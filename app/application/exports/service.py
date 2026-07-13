from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.application.ports.exports import DataExportRepository, ExportTable
from app.core.time import utc_now


@dataclass(frozen=True)
class DataExport:
    filename: str
    content: bytes
    media_type: str = "application/zip"


@dataclass(frozen=True)
class DataExportService:
    repository: DataExportRepository

    def create_export(self, user_id: int) -> DataExport:
        generated_at = utc_now()
        tables = self.repository.get_export_tables(user_id)
        archive = BytesIO()
        manifest_files = []

        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as export_zip:
            for table in tables:
                content = _table_csv(table)
                export_zip.writestr(table.filename, content)
                manifest_files.append(
                    {
                        "filename": table.filename,
                        "row_count": len(table.rows),
                        "columns": list(table.columns),
                    }
                )
            export_zip.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format": "aquaops-portable-export",
                        "format_version": 1,
                        "generated_at": generated_at.isoformat(),
                        "files": manifest_files,
                    },
                    indent=2,
                ),
            )

        timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
        return DataExport(
            filename=f"aquaops-export-{timestamp}.zip",
            content=archive.getvalue(),
        )


def _table_csv(table: ExportTable) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(table.columns)
    writer.writerows(tuple(_portable_value(value) for value in row) for row in table.rows)
    return output.getvalue()


def _portable_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value
