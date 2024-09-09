import csv
import datetime
import enum
import io
import random
from abc import ABC, abstractmethod
from decimal import Decimal

import zoneinfo
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
            # Write the register details
            writer.writerow(
                (
                    "200",
                    meter_point.nmi,
                    nmi_config,
                    register.register_id,
                    register.suffix,
                    "",  # MDMData Stream Identifier
                    meter.serial_number,
                    register.uom,
                    str(interval.value),
                    "",  # Next scheduled read date
                )
            )

            current_date = start
            while current_date <= end:
                # Write the consumption data
                writer.writerow(
                    (
                        "300",
                        current_date.strftime("%Y%m%d"),
                        *_generate_consumption_profile(interval.intervals()),
                        QualityMethod.ACTUAL.value,
                        "",  # reason code - not required for ACTUAL
                        "",  # reason description - not required for ACTUAL
                        now_tz.strftime("%Y%m%d%H%M%S"),
                        now_tz.strftime("%Y%m%d%H%M%S"),
                    )
                )
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
) -> list[Decimal]:
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
    return [Decimal(f"{read}").quantize(padding) for read in early + late]


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
