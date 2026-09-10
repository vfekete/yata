"""Plugin-owned settings for the timesheet plugin (r-10.md).

Same envelope-backed QObject shape TaskListSettings (plugins/
simple_task_list/settings.py) already established — one JSON file per
window instance, via plugin_data.py's versioned block envelope. No legacy
QSettings migration here (this plugin never existed before), unlike
TaskListSettings' one-time theme/* migration.

themeMode/themeTint/opacityPercent are deliberately named and shaped
identically to TaskListSettings' own — main.py's window_factory clones a
NEW window's theme generically onto whatever "appSettings" object the
new window's plugin returns (plugin_settings.themeMode = ..., etc.),
regardless of which plugin that turns out to be. Keeping the exact same
property surface here is what makes "new window clones the creating
window's theme" keep working across a plugin boundary, and gives every
window in the app the same customizable dark/light + CRT-tint look
(this plugin's own ThemeImpl.qml implements the same palette contract
TaskListSettings' theme drives).
"""
from __future__ import annotations

from PySide6.QtCore import Property, QLocale, QObject, Signal

import plugin_data
from plugin_api import API_VERSION

from .storage import PLUGIN_ID

MODEL_VERSION = "1.0"

THEME_MODES = ("light", "dark")
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100

DEFAULT_DAILY_HOURS = 8.0
MIN_DAILY_HOURS = 0.5
MAX_DAILY_HOURS = 24.0


def _detect_country_code() -> str:
    """Best-effort default from the system locale's region — "" if the
    locale is unset/C/POSIX (QLocale.system().name() comes back as "C" or
    empty in that case, per Qt's own documented behavior), which the UI
    treats as "ask the user to pick one on first open" (explicit r-10.md
    decision)."""
    name = QLocale.system().name()  # e.g. "sk_SK", "en_US", or "C"
    if "_" not in name:
        return ""
    return name.split("_", 1)[1].upper()


class TimesheetSettings(QObject):
    themeModeChanged = Signal()
    themeTintChanged = Signal()
    opacityPercentChanged = Signal()
    countryCodeChanged = Signal()
    customerNameChanged = Signal()
    customerAddressChanged = Signal()
    contractorNameChanged = Signal()
    defaultDailyHoursChanged = Signal()
    pdfIncludeCustomerChanged = Signal()
    pdfIncludeContractorChanged = Signal()
    pdfIncludeSignaturesChanged = Signal()

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        data = plugin_data.read_compatible(path, MODEL_VERSION, API_VERSION)
        already_on_disk = data is not None
        data = data or {}

        mode = data.get("themeMode", "dark")
        self._theme_mode = mode if mode in THEME_MODES else "dark"
        tint = data.get("themeTint", "none")
        self._theme_tint = tint if tint in THEME_TINTS else "none"
        self._opacity_percent = self._clamp_opacity(data.get("opacityPercent", DEFAULT_OPACITY_PERCENT))

        self._country_code = data.get("countryCode", None)
        if self._country_code is None:
            self._country_code = _detect_country_code()
        self._customer_name = data.get("customerName", "")
        self._customer_address = data.get("customerAddress", "")
        self._contractor_name = data.get("contractorName", "")
        self._default_daily_hours = self._clamp_hours(data.get("defaultDailyHours", DEFAULT_DAILY_HOURS))
        self._pdf_include_customer = bool(data.get("pdfIncludeCustomer", True))
        self._pdf_include_contractor = bool(data.get("pdfIncludeContractor", True))
        self._pdf_include_signatures = bool(data.get("pdfIncludeSignatures", True))

        if not already_on_disk:
            self._save()

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

    @staticmethod
    def _clamp_hours(value) -> float:
        return max(MIN_DAILY_HOURS, min(MAX_DAILY_HOURS, float(value)))

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, {
            "themeMode": self._theme_mode,
            "themeTint": self._theme_tint,
            "opacityPercent": self._opacity_percent,
            "countryCode": self._country_code,
            "customerName": self._customer_name,
            "customerAddress": self._customer_address,
            "contractorName": self._contractor_name,
            "defaultDailyHours": self._default_daily_hours,
            "pdfIncludeCustomer": self._pdf_include_customer,
            "pdfIncludeContractor": self._pdf_include_contractor,
            "pdfIncludeSignatures": self._pdf_include_signatures,
        })

    def _get_theme_mode(self) -> str:
        return self._theme_mode

    def _set_theme_mode(self, value: str):
        if value not in THEME_MODES or value == self._theme_mode:
            return
        self._theme_mode = value
        self._save()
        self.themeModeChanged.emit()

    themeMode = Property(str, _get_theme_mode, _set_theme_mode, notify=themeModeChanged)

    def _get_theme_tint(self) -> str:
        return self._theme_tint

    def _set_theme_tint(self, value: str):
        if value not in THEME_TINTS or value == self._theme_tint:
            return
        self._theme_tint = value
        self._save()
        self.themeTintChanged.emit()

    themeTint = Property(str, _get_theme_tint, _set_theme_tint, notify=themeTintChanged)

    def _get_opacity_percent(self) -> int:
        return self._opacity_percent

    def _set_opacity_percent(self, value: int):
        value = self._clamp_opacity(value)
        if value == self._opacity_percent:
            return
        self._opacity_percent = value
        self._save()
        self.opacityPercentChanged.emit()

    opacityPercent = Property(
        int, _get_opacity_percent, _set_opacity_percent, notify=opacityPercentChanged
    )

    def _get_country_code(self) -> str:
        return self._country_code

    def _set_country_code(self, value: str):
        value = value.strip().upper()
        if value == self._country_code:
            return
        self._country_code = value
        self._save()
        self.countryCodeChanged.emit()

    countryCode = Property(str, _get_country_code, _set_country_code, notify=countryCodeChanged)

    def _get_customer_name(self) -> str:
        return self._customer_name

    def _set_customer_name(self, value: str):
        if value == self._customer_name:
            return
        self._customer_name = value
        self._save()
        self.customerNameChanged.emit()

    customerName = Property(str, _get_customer_name, _set_customer_name, notify=customerNameChanged)

    def _get_customer_address(self) -> str:
        return self._customer_address

    def _set_customer_address(self, value: str):
        if value == self._customer_address:
            return
        self._customer_address = value
        self._save()
        self.customerAddressChanged.emit()

    customerAddress = Property(
        str, _get_customer_address, _set_customer_address, notify=customerAddressChanged
    )

    def _get_contractor_name(self) -> str:
        return self._contractor_name

    def _set_contractor_name(self, value: str):
        if value == self._contractor_name:
            return
        self._contractor_name = value
        self._save()
        self.contractorNameChanged.emit()

    contractorName = Property(
        str, _get_contractor_name, _set_contractor_name, notify=contractorNameChanged
    )

    def _get_default_daily_hours(self) -> float:
        return self._default_daily_hours

    def _set_default_daily_hours(self, value: float):
        value = self._clamp_hours(value)
        if value == self._default_daily_hours:
            return
        self._default_daily_hours = value
        self._save()
        self.defaultDailyHoursChanged.emit()

    defaultDailyHours = Property(
        float, _get_default_daily_hours, _set_default_daily_hours, notify=defaultDailyHoursChanged
    )

    def _get_pdf_include_customer(self) -> bool:
        return self._pdf_include_customer

    def _set_pdf_include_customer(self, value: bool):
        if value == self._pdf_include_customer:
            return
        self._pdf_include_customer = value
        self._save()
        self.pdfIncludeCustomerChanged.emit()

    pdfIncludeCustomer = Property(
        bool, _get_pdf_include_customer, _set_pdf_include_customer, notify=pdfIncludeCustomerChanged
    )

    def _get_pdf_include_contractor(self) -> bool:
        return self._pdf_include_contractor

    def _set_pdf_include_contractor(self, value: bool):
        if value == self._pdf_include_contractor:
            return
        self._pdf_include_contractor = value
        self._save()
        self.pdfIncludeContractorChanged.emit()

    pdfIncludeContractor = Property(
        bool, _get_pdf_include_contractor, _set_pdf_include_contractor,
        notify=pdfIncludeContractorChanged
    )

    def _get_pdf_include_signatures(self) -> bool:
        return self._pdf_include_signatures

    def _set_pdf_include_signatures(self, value: bool):
        if value == self._pdf_include_signatures:
            return
        self._pdf_include_signatures = value
        self._save()
        self.pdfIncludeSignaturesChanged.emit()

    pdfIncludeSignatures = Property(
        bool, _get_pdf_include_signatures, _set_pdf_include_signatures,
        notify=pdfIncludeSignaturesChanged
    )

    # Read-only so QML can reset to these without hardcoding the values
    # itself in more than one place — same convention TaskListSettings'
    # own defaultOpacityPercent already established.
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)
    defaultDailyHoursDefault = Property(float, lambda self: DEFAULT_DAILY_HOURS, constant=True)
