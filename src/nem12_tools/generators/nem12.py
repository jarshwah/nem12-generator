import csv
import datetime
import enum
import io
import random
import zoneinfo
from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from nem12_tools.parsers.nmid import MeterPoint

from . import notifications as mdmt


@enum.unique
class IntervalLength(enum.IntEnum):
    FIVE_MINUTES = 5
    FIFTEEN_MINUTES = 15
    THIRTY_MINUTES = 30

    def intervals(self) -> int:
        return (24 * 60) // self.value


@enum.unique
class QualityMethod(enum.StrEnum):
    ACTUAL = "A"
    SUBSTITUTE = "S"
    PERMANENT_SUBSTITUTE = "F"


class RowProducer(ABC):
    @abstractmethod
    def as_row(self) -> tuple[str, ...]: ...


class Header(RowProducer, BaseModel):
    indicator: str = "100"
    version: str = "NEM12"
    generation_time: datetime.datetime = Field(default_factory=datetime.datetime.now)
    from_participant: str
    to_participant: str

    @field_serializer("generation_time")
    def serialize_generation_time(self, generation_time: datetime.datetime) -> str:
        return generation_time.strftime("%Y%m%d%H%M")

    def as_row(self) -> tuple[str, ...]:
        data = self.model_dump()
        return (
            data["indicator"],
            data["version"],
            data["generation_time"],
            data["from_participant"],
            data["to_participant"],
        )


class NmiDetails(RowProducer, BaseModel):
    indicator: str = "200"
    nmi: str
    nmi_configuration: str
    register_id: str
    register_suffix: str
    mdm_data_stream: str = ""
    meter_serial_number: str
    uom: str
    interval_length: IntervalLength
    next_scheduled_read_date: None = None

    @field_serializer("next_scheduled_read_date")
    def serialize_next_scheduled_read_date(self, next_scheduled_read_date: None) -> str:
        return ""

    @field_serializer("interval_length")
    def serialize_interval_length(self, interval_length: IntervalLength) -> str:
        return str(interval_length.value)

    def as_row(self) -> tuple[str, ...]:
        data = self.model_dump()
        return (
            data["indicator"],
            data["nmi"],
            data["nmi_configuration"],
            data["register_id"],
            data["register_suffix"],
            data["mdm_data_stream"],
            data["meter_serial_number"],
            data["uom"],
            data["interval_length"],
            data["next_scheduled_read_date"],
        )


class IntervalData(RowProducer, BaseModel):
    indicator: str = "300"
    read_date: datetime.date
    read_values: tuple[Decimal, ...]
    quality_method: QualityMethod
    reason_code: str = ""
    reason_description: str = ""
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.now)
    msats_load_time: datetime.datetime = Field(default_factory=datetime.datetime.now)

    @field_serializer("read_date")
    def serialize_read_date(self, read_date: datetime.date) -> str:
        return read_date.strftime("%Y%m%d")

    @field_serializer("read_values")
    def serialize_read_values(self, read_values: list[Decimal]) -> tuple[str, ...]:
        return tuple(str(read) for read in read_values)

    @field_serializer("quality_method")
    def serialize_quality_method(self, quality_method: QualityMethod) -> str:
        return quality_method.value

    @field_serializer("last_updated")
    def serialize_last_updated(self, last_updated: datetime.datetime) -> str:
        return last_updated.strftime("%Y%m%d%H%M%S")

    @field_serializer("msats_load_time")
    def serialize_msats_load_time(self, msats_load_time: datetime.datetime) -> str:
        return msats_load_time.strftime("%Y%m%d%H%M%S")

    def as_row(self) -> tuple[str, ...]:
        data = self.model_dump()
        return (
            data["indicator"],
            data["read_date"],
            *data["read_values"],
            data["quality_method"],
            data["reason_code"],
            data["reason_description"],
            data["last_updated"],
            data["msats_load_time"],
        )


def generate_nem12(
    meter_point: MeterPoint,
    start: datetime.date = datetime.date.today(),
    end: datetime.date = datetime.date.today(),
    interval: IntervalLength = IntervalLength.FIVE_MINUTES,
) -> mdmt.MeterDataNotification:
    now_tz = datetime.datetime.now(tz=zoneinfo.ZoneInfo("Etc/GMT-10"))
    transactions = io.StringIO(newline="")
    writer = csv.writer(transactions, delimiter=",", lineterminator="\n")

    if start > end:
        raise ValueError("Start date must be before end date")

    header = Header(
        generation_time=now_tz,
        from_participant=meter_point.role_mdp,
        to_participant=meter_point.role_frmp,
    )
    writer.writerow(header.as_row())

    nmi_config = "".join(reg.suffix for meter in meter_point.meters for reg in meter.registers)
    for meter in meter_point.meters:
        for register in meter.registers:
            nmi_details = NmiDetails(
                nmi=meter_point.nmi,
                nmi_configuration=nmi_config,
                register_id=register.register_id,
                register_suffix=register.suffix,
                meter_serial_number=meter.serial_number,
                uom=register.uom,
                interval_length=interval,
            )
            # Write the register details
            writer.writerow(nmi_details.as_row())

            current_date = start
            while current_date <= end:
                # Write the consumption data
                interval_data = IntervalData(
                    read_date=current_date,
                    read_values=_generate_consumption_profile(interval.intervals()),
                    quality_method=QualityMethod.ACTUAL,
                    last_updated=now_tz,
                    msats_load_time=now_tz,
                )
                writer.writerow(interval_data.as_row())
                current_date += datetime.timedelta(days=1)
    # End of file
    writer.writerow(("900",))

    meter_data_file = _create_meterdata_notification(meter_point)
    meter_data_file.transactions(
        transaction_id=f"MTRD_MSG_NEM12_{now_tz.strftime('%Y%m%d%H%M%f')}",
        transaction_date=now_tz.isoformat(timespec="seconds"),
        transaction_type="MeterDataNotification",
        transaction_schema_version="r25",
        csv_interval_data=transactions.getvalue(),
        participant_role="FRMP",
    )
    return meter_data_file


def _generate_consumption_profile(
    intervals: int, min_value: float = -0.6, max_value: float = 0.8
) -> tuple[Decimal, ...]:
    """
    Generate reads over a 24 hour period over the given number of intervals.

    By default, we bias the read values towards 0 with a negative lower bound that we then max to 0.
    """
    # Generate a consumption profile with a bell shaped curve, peaking at approximately 8pm
    values = sorted(
        # Bias the numbers towards the mode
        round(max(0, random.triangular(min_value, max_value, mode=0.6)), 4)
        for _ in range(intervals)
    )
    # The pivot is selected to get to approximately 8pm
    pivot = int(intervals // 1.2)
    early, late = values[:pivot], values[pivot:]
    # Low consumption in the morning, getting higher towards 8pm
    early.sort()
    # Peak at about 8pm, then decreasing towards midnight
    late.sort(reverse=True)
    padding = Decimal("0.0000")
    return tuple(Decimal(f"{read}").quantize(padding) for read in early + late)


def _create_meterdata_notification(
    meter_point: MeterPoint,
) -> mdmt.MeterDataNotification:
    now_tz = datetime.datetime.now(tz=zoneinfo.ZoneInfo("Etc/GMT-10"))
    meter_data_file = mdmt.MeterDataNotification()
    meter_data_file.header(
        from_text=meter_point.role_mdp,
        to_text=meter_point.role_frmp,
        message_id=f"MTRD_MSG_NEM12_{now_tz.strftime('%Y%m%d%H%M%f')}",
        message_date=now_tz.isoformat(timespec="seconds"),
        transaction_group="MTRD",
        priority="Medium",
        market="NEM",
    )
    return meter_data_file
