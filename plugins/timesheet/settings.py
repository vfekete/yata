from __future__ import annotations

from PySide6.QtCore import Property, QLocale, Signal

import plugin_data
from plugin_api import API_VERSION
from plugin_settings import ThemedSettings

from .storage import PLUGIN_ID

MODEL_VERSION = "1.0"

DEFAULT_DAILY_HOURS = 8.0
MIN_DAILY_HOURS = 0.5
MAX_DAILY_HOURS = 24.0

DEFAULT_ONGOING_COLOR = "lime"
DEFAULT_ABANDONED_COLOR = "#ef4444"


def _detect_country_code() -> str:
    name = QLocale.system().name()
    if "_" not in name:
        return ""
    return name.split("_", 1)[1].upper()


class TimesheetSettings(ThemedSettings):
    countryCodeChanged = Signal()
    customerNameChanged = Signal()
    customerAddressChanged = Signal()
    contractorNameChanged = Signal()
    defaultDailyHoursChanged = Signal()
    pdfIncludeCustomerChanged = Signal()
    pdfIncludeContractorChanged = Signal()
    pdfIncludeSignaturesChanged = Signal()
    ongoingColorChanged = Signal()
    abandonedColorChanged = Signal()

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        data = plugin_data.read_compatible(path, MODEL_VERSION, API_VERSION)
        already_on_disk = data is not None
        data = data or {}
        self._load_themed(data)

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
        self._ongoing_color = data.get("ongoingColor", DEFAULT_ONGOING_COLOR)
        self._abandoned_color = data.get("abandonedColor", DEFAULT_ABANDONED_COLOR)

        if not already_on_disk:
            self._save()

    @staticmethod
    def _clamp_hours(value) -> float:
        return max(MIN_DAILY_HOURS, min(MAX_DAILY_HOURS, float(value)))

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, {
            **self._themed_data(),
            "countryCode": self._country_code,
            "customerName": self._customer_name,
            "customerAddress": self._customer_address,
            "contractorName": self._contractor_name,
            "defaultDailyHours": self._default_daily_hours,
            "pdfIncludeCustomer": self._pdf_include_customer,
            "pdfIncludeContractor": self._pdf_include_contractor,
            "pdfIncludeSignatures": self._pdf_include_signatures,
            "ongoingColor": self._ongoing_color,
            "abandonedColor": self._abandoned_color,
        })

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

    def _get_ongoing_color(self) -> str:
        return self._ongoing_color

    def _set_ongoing_color(self, value: str):
        if value == self._ongoing_color:
            return
        self._ongoing_color = value
        self._save()
        self.ongoingColorChanged.emit()

    ongoingColor = Property(str, _get_ongoing_color, _set_ongoing_color, notify=ongoingColorChanged)

    def _get_abandoned_color(self) -> str:
        return self._abandoned_color

    def _set_abandoned_color(self, value: str):
        if value == self._abandoned_color:
            return
        self._abandoned_color = value
        self._save()
        self.abandonedColorChanged.emit()

    abandonedColor = Property(str, _get_abandoned_color, _set_abandoned_color, notify=abandonedColorChanged)

    defaultDailyHoursDefault = Property(float, lambda self: DEFAULT_DAILY_HOURS, constant=True)
    defaultOngoingColor = Property(str, lambda self: DEFAULT_ONGOING_COLOR, constant=True)
    defaultAbandonedColor = Property(str, lambda self: DEFAULT_ABANDONED_COLOR, constant=True)
