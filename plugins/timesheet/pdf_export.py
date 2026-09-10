"""PDF timesheet export (r-10.md) — Qt's own QTextDocument -> QPdfWriter,
confirmed to ship with PySide6's QtGui already (no new dependency, same
bar already applied to every other library choice in this codebase)."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_html(
    summary: dict, *, customer_name: str, customer_address: str, contractor_name: str,
    include_customer: bool, include_contractor: bool, include_signatures: bool,
) -> str:
    """summary: exactly model.py's compute_summary() return shape. Spec's
    PDF layout: header (customer/contractor, both optional), a table of
    work days with duration + ON-SITE/REMOTE, footer (totals + optional
    signature lines + generation timestamp)."""
    parts = ["<html><body style='font-family: sans-serif;'>"]

    if include_customer or include_contractor:
        parts.append("<table width='100%' style='margin-bottom: 16px;'><tr>")
        if include_customer:
            parts.append(
                "<td valign='top'><b>Customer</b><br>"
                f"{_escape(customer_name)}<br>{_escape(customer_address)}</td>"
            )
        if include_contractor:
            parts.append(f"<td valign='top'><b>Contractor</b><br>{_escape(contractor_name)}</td>")
        parts.append("</tr></table>")

    parts.append(f"<h3>Timesheet: {_escape(summary['start'])} &ndash; {_escape(summary['end'])}</h3>")

    parts.append(
        "<table width='100%' border='1' cellspacing='0' cellpadding='4' "
        "style='border-collapse: collapse;'>"
        "<tr><th align='left'>Date</th><th align='left'>Worked</th>"
        "<th align='left'>Location</th><th align='left'>Notes</th></tr>"
    )
    for day in summary["days"]:
        location = (
            "ON-SITE" if day["location"] == "on-site"
            else "REMOTE" if day["location"] == "remote"
            else ""
        )
        notes = day["holidayName"] if day["isHoliday"] else ("Weekend" if day["isWeekend"] else "")
        parts.append(
            f"<tr><td>{_escape(day['date'])}</td><td>{_escape(day['workedLabel'])}</td>"
            f"<td>{_escape(location)}</td><td>{_escape(notes)}</td></tr>"
        )
    parts.append("</table>")

    parts.append(
        f"<p><b>Total worked:</b> {_escape(summary['workedTotalLabel'])}"
        f" &nbsp;&nbsp; <b>Target:</b> {_escape(summary['targetTotalLabel'])}"
        f" &nbsp;&nbsp; <b>Remaining:</b> {_escape(summary['remainingLabel'])}"
        f" &nbsp;&nbsp; <b>Overtime:</b> {_escape(summary['overtimeLabel'])}</p>"
    )

    if include_signatures:
        parts.append(
            "<table width='100%' style='margin-top: 48px;'><tr>"
            "<td>Client signature: ________________________</td>"
            "<td>Contractor signature: ________________________</td>"
            "</tr></table>"
        )
    parts.append(
        f"<p style='margin-top: 16px; font-size: 10px; color: #666;'>"
        f"Generated on {_escape(_now_label())}</p>"
    )
    parts.append("</body></html>")
    return "".join(parts)


def export_pdf(path: str, html: str) -> None:
    """Raises OSError if the PDF wasn't actually written — QPdfWriter/
    QTextDocument.print_() fail SILENTLY at the C++ level for an
    unwritable path (a QPainter::begin() warning printed to stderr, no
    Python exception at all) rather than raising, confirmed live: calling
    this against a nonexistent directory returned normally with no file
    ever created. model.py's exportPdf() only catches Python exceptions,
    so this has to turn that silent failure into one."""
    document = QTextDocument()
    document.setHtml(html)
    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.A4))
    document.print_(writer)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise OSError(f"failed to write PDF to {path!r}")
