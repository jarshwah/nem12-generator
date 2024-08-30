# Version 1.0
import csv
import json
import os
import random
from datetime import datetime, timedelta, timezone
from zipfile import ZipFile

from loguru import logger

from . import generate_mdmt_xml as mdmt

# ToDo fix the input directories to look for the in and out folders relative to the script
INPUT_DIRECTORY = r"C:/Users/NUGEP1/OneDrive - Alinta Servco/Dev/MeterData/in/"
OUTPUT_DIRECTORY = r"C:/Users/NUGEP1/OneDrive - Alinta Servco/Dev/MeterData/out/"

map_number_of_intervals = {
    # key = minutes | #value = intervals
    5: 288,
    15: 96,
    30: 48,
}


# Zip the csv file
def create_zip_file(filename: str):
    filename_without_extension = filename[:-4]
    zip_filename = filename_without_extension + ".zip"
    zip_obj = ZipFile(zip_filename, "w")
    zip_obj.write(filename)
    zip_obj.close()


class read_meter_data_csv_config:
    def __init__(self, directory=None, filename=None, meter_data_config_row=None):
        self.directory = directory
        self.filename = filename
        self.meter_data_csv_row = meter_data_config_row
        self.meter_data_dict_row = self.meter_data_config_csv_to_dict(
            meter_data_config_row
        )
        self.current_constant = self.meter_data_dict_row
        self.participant_from = self.current_constant.get("participant_from", None)
        self.participant_to = self.current_constant.get("participant_to", None)
        self.nem_file_header_record_indicator = 100
        self.nem_nmi_details_record_indicator = 200
        self.nem12_interval_data_record_indicator = 300
        self.nem_file_end_of_record_indicator = 500
        self.nem12_version_header = "NEM12"
        self.nem12_mdm_data_stream_indentifier = "N1"
        self.nem12_interval_length = self.current_constant.get("nem_12_interval", None)
        self.meter_data_qm = self.current_constant.get("meter_data_qm", None)
        self.nem12_interval_start_date = self.current_constant.get(
            "interval_start_date", None
        )
        self.nem12_interval_end_date = self.current_constant.get(
            "interval_end_date", None
        )
        self.nem12_interval_average_daily_load = self.current_constant.get(
            "average_daily_load", None
        )
        self.nem12_number_of_intervals = map_number_of_intervals[
            int(self.nem12_interval_length)
        ]
        self.nmi = self.current_constant.get("nmi", None)
        self.register_id = self.current_constant.get("register_id", None)
        self.number_of_registers = len(self.register_id)
        self.consumption_values = self.generate_random_read_consumption_values()
        self.low_interval_consumption_value = self.consumption_values.get(
            "low_interval_consumption_value", None
        )
        self.high_interval_consumption_value = self.consumption_values.get(
            "high_interval_consumption_value", None
        )
        self.meter_serial_number = self.current_constant.get(
            "meter_serial_number", None
        )
        self.nem_nsrd = self.generate_nem_file_nsrd()
        self.unit_of_measure = self.get_unit_of_measure(self.register_id)
        self.nmi_configuration = self.register_id
        self.current_meter_data_csv_filename = self.current_constant.get(
            "current_csv_filename", None
        )
        self.file_datetime = datetime.today().strftime(
            "%Y%m%d%H%M%f"
        )  # micro seconds (f) added to ensure filename is unique at each generation
        logger.info(self.file_datetime)
        self.message_trans_datetime = datetime.now(timezone(timedelta(hours=10)))
        self.file_message_id = f"MTRD_MSG_NEM12_{self.file_datetime}"
        self.nem_mdmt_filename = self.generate_meter_data_filename()

    def get_current_file(self, extension=".csv"):
        """
        Looks in a given directory for the defined file extension type
        and returns the first file within the index of files in the list.
        """
        files_to_process = len(
            [file for file in os.listdir(self.directory) if file.endswith(extension)]
        )
        if files_to_process > 0 and files_to_process <= 2:
            files = [file for file in os.listdir(self.directory)]
            filename = os.fsdecode(files[0])
            if filename.endswith(extension):
                return filename
            else:
                logger.info(
                    f"No {extension} config file of {filename} exists in {self.directory}"
                )
                exit()
        else:
            logger.info(
                f"There are None << or >> more than one {extension} config file was found in directory {self.directory}"
            )
            exit()

    # Generate a unique NEM12 file name and unique messageID
    def generate_meter_data_filename(self):
        """
        Returns a meter data filename for xml file.
        """
        file_prefix = "mtrdm_NEM12_"
        file_date_time = self.file_datetime
        file_extension = ".xml"
        nem_filename = f"{file_prefix}{file_date_time}{file_extension}"
        return nem_filename

    def get_unit_of_measure(self, register_id: str):
        # TODO how to handle E and Q within the same file?
        """
        Returns a UOM of either KVA or KVAR based on the register id's provided.
        """
        suffix = register_id[:1]
        if suffix in ["E", "B"]:
            UOM = "KWH"
        else:
            UOM = "KVARH"
        return UOM

    def validate_nmi(self, nmi: str):
        """
        Validates the nmi string's length. Returns True or False.
        """
        # TODO add checksum validation and prefix validation also.
        nmilen = len(nmi)
        if nmilen < 10:
            return False
        else:
            return True

    def generate_random_intervals(
        self,
        total_intervals: str,
        min_consumption_value: float,
        max_consumption_value: float,
    ):
        interval_count = 0
        random_reads = []
        read_sum = 0
        while interval_count < total_intervals:
            # Returns the generated floating point random number between lower limit and upper limit
            random_consumption_value = round(
                random.uniform(min_consumption_value, max_consumption_value), 3
            )
            read_sum += random_consumption_value
            interval_count += 1
            random_reads.append(random_consumption_value)
        return random_reads

    # Method to simulate consumption with a bell shaped curve
    def generate_consumption_profile(
        self,
        total_intervals,
        min_consumption_value: float,
        max_consumption_value: float,
    ):
        interval_count = 0
        random_reads = []
        profiled_reads = []
        while interval_count < total_intervals:
            random_consumption_value = round(
                random.uniform(min_consumption_value, max_consumption_value), 3
            )
            interval_count += 1
            random_reads.append(random_consumption_value)
        # Split the array in two and sort half DESC and the other half ASC
        half = len(random_reads) // 2
        morning_reads = random_reads[:half]
        afternoon_reads = random_reads[half:]
        morning_reads.sort(reverse=False)
        afternoon_reads.sort(reverse=True)
        profiled_reads = morning_reads + afternoon_reads
        return profiled_reads

    def generate_random_read_consumption_values(self, variance: float = 0.2):
        # variance of daily consumption is defaulted to 20%
        average_daily_load = self.nem12_interval_average_daily_load
        number_of_registers = self.number_of_registers
        number_of_intervals = self.nem12_number_of_intervals
        interval_consumption_value = (
            int(average_daily_load) / number_of_registers / number_of_intervals
        )
        low_interval_consumption_value = interval_consumption_value - (
            interval_consumption_value * variance
        )
        high_interval_consumption_value = interval_consumption_value + (
            interval_consumption_value * variance
        )
        return {
            "low_interval_consumption_value": low_interval_consumption_value,
            "high_interval_consumption_value": high_interval_consumption_value,
        }

    def generate_nem_file_nsrd(self):
        """
        Returns a next scheduled read date 10 days after interval end date
        """
        end_read_date = datetime.strptime(self.nem12_interval_end_date, "%Y%m%d").date()
        temp_nsrd = end_read_date + timedelta(days=10)
        next_scheduled_read_date = temp_nsrd.strftime("%Y%m%d")
        return next_scheduled_read_date

    def meter_data_config_csv_to_dict(self, meter_data_config_row: str):
        meter_data_row_dict = {
            "participant_from": meter_data_config_row[0],
            "participant_to": meter_data_config_row[1],
            "nem_12_interval": meter_data_config_row[2],
            "meter_data_qm": meter_data_config_row[3],
            "meter_data_qm_flag": meter_data_config_row[4],
            "meter_data_qm_reason": meter_data_config_row[5],
            "interval_start_date": meter_data_config_row[6],
            "interval_end_date": meter_data_config_row[7],
            "average_daily_load": meter_data_config_row[8],
            "nmi": meter_data_config_row[9],
            "register_id": meter_data_config_row[10],
            "meter_serial_number": meter_data_config_row[11],
            "current_csv_filename": None,
        }
        logger.info(json.dumps(meter_data_row_dict, indent=4))
        return meter_data_row_dict


class validate_meter_data_file(read_meter_data_csv_config):
    # TODO incorporate method and reason codes for validation

    # Method flag part of QM for Substitution and Estimation Types
    methodFlagList = [
        "11 - Check",
        "12 - Calculated",
        "13 - SCADA",
        "14 - Ave Like Day",
    ]

    # Reason code where the quality method is substitute
    reasonCodeList = [
        "0 - Free Text",
        "2 - Extreme weather conditions",
        "8 - Vacant premises",
        "11 - In wrong route",
        "12 - Locked premises",
        "13 - Locked gate",
        "20 - Damaged equipment/panel",
        "23 - Reader error",
        "32 - Re-energised without readings",
        "36 - Meter high/ladder required",
        "41 - Faulty Meter display/dials",
    ]

    def validate_meter_data_config(self):
        error_log = {}
        participant_to = self.participant_to
        participant_from = self.participant_from

        def validate_participant_to():
            VALID_TO_PARTICIPANT = {"ALNTABUS", "ALNTAUSR", "ALNTARES"}
            if participant_to not in VALID_TO_PARTICIPANT:
                return {
                    False: f"Reason: The 'Participant To' value must be one of {VALID_TO_PARTICIPANT}."
                }
            else:
                True

        participant_to_results = validate_participant_to()

        if participant_to_results is not None:
            error_log.update({participant_to: participant_to_results})
        else:
            pass

        def validate_participant_from():
            VALID_FROM_PARTICIPANT = {
                "CITIPWMP",
                "CNRGYMDP",
                "CNRGYP",
                "CPNETMDP",
                "ENERGEXM",
                "ERGONMP",
                "ETSAMDP",
                "GLOBALM",
                "INTEGM",
                "JENMDP",
                "METROMP",
                "POWERMDP",
                "SPANMDP",
                "TCAUSTM",
                "UEDMDP",
                "VECTOMDP",
                "EASTENMP",
                "TCAMP",
                "MDYMDP",
                "IHUBMDP",
            }
            if participant_from not in VALID_FROM_PARTICIPANT:
                return {
                    False: f"Reason: The 'Participant To' value must be one of {VALID_FROM_PARTICIPANT}."
                }
            else:
                True

        participant_from_results = validate_participant_from()

        if participant_from_results is not None:
            error_log.update({participant_from: participant_from_results})
        else:
            pass

        if error_log:
            return error_log
        else:
            return True


class generate_meter_data_file(validate_meter_data_file, read_meter_data_csv_config):
    # Write the records to an xml file
    def generate_nem12_records(self):
        validation_results = self.validate_meter_data_config()
        if validation_results is not True:
            logger.info("validation issues exist")
            logger.info(validation_results)
        else:
            nmi_configuration = self.register_id
            nmi_config_length = len(nmi_configuration)
            interval_length = self.nem12_interval_length

            interval_start_date = self.nem12_interval_start_date
            start_read_date = datetime.strptime(interval_start_date, "%Y%m%d").date()

            # Convert read date from YYYY-MM-DD to YYYYMMDD to meet NEM12 file spec
            converted_start_read_date = start_read_date.strftime("%Y%m%d")
            interval_end_date = self.nem12_interval_end_date
            end_read_date = datetime.strptime(interval_end_date, "%Y%m%d").date()
            if interval_start_date > interval_end_date:
                # TODO validation of start and end read dates
                logger.info(
                    "Validation Error - Interval Start Date must be earlier than Interval End Date"
                )

            # DONE re-write xml helper
            meter_data_file = mdmt.meter_data_notification()
            meter_data_file.header(
                from_text=self.participant_from,
                to_text=self.participant_to,
                message_id=self.file_message_id,
                message_date=self.message_trans_datetime,
                transaction_group="MDMT",
                priority="Low",
                market="NEM",
            )
            temp_text_file = self.nem_mdmt_filename[:-4]

            with open(f"{temp_text_file}.txt", mode="w") as nem12_file:
                # TODO consider temp file module instead of txt files.
                # create temp txt file which contains the meter data text for CSVIntervalData
                nem12_file.write(
                    "\n"
                )  # Add a new blank line to make it cleaner in the XML file.

            with open(
                f"{temp_text_file}.txt", mode="a", newline="", encoding="utf-8"
            ) as nem12_file:
                nem12_writer = csv.writer(
                    nem12_file, delimiter=",", quotechar="`", quoting=csv.QUOTE_MINIMAL
                )
                nem12_writer.writerow(
                    [
                        self.nem_file_header_record_indicator,
                        self.nem12_version_header,
                        self.file_datetime,
                        self.participant_from,
                        self.participant_to,
                    ]
                )

                delta = timedelta(days=1)
                while start_read_date <= end_read_date:
                    i = 0
                    # Loop printing row types 200 and 300 for each register (E1, Q1, K1, B1) in the nmiConfiguration
                    while i < nmi_config_length:
                        register_id = nmi_configuration[i : i + 2]
                        nmi_suffix = register_id
                        UOM = self.get_unit_of_measure(register_id)
                        nem12_writer.writerow(
                            [
                                self.nem_nmi_details_record_indicator,
                                self.nmi[0:10],
                                nmi_configuration,
                                register_id,
                                nmi_suffix,
                                self.nem12_mdm_data_stream_indentifier,
                                self.meter_serial_number,
                                UOM,
                                interval_length,
                                self.nem_nsrd,
                            ]
                        )
                        number_of_intervals = self.nem12_number_of_intervals
                        low_read = self.low_interval_consumption_value
                        high_read = self.high_interval_consumption_value

                        read_list = self.generate_consumption_profile(
                            number_of_intervals, low_read, high_read
                        )
                        reason_code = ""  # TODO make this
                        reason_description = ""  # TODO make this dynamic
                        i += 2
                        # i = i + 2
                        start_read_date += delta
                        converted_start_read_date = start_read_date.strftime("%Y%m%d")
                        nem12_writer.writerow(
                            [
                                self.nem12_interval_data_record_indicator,
                                converted_start_read_date,
                            ]
                            + read_list  # is its own list so is concatenated in with the other explicit lists.
                            + [
                                self.meter_data_qm,
                                reason_code,
                                reason_description,
                                self.file_datetime,
                            ]
                        )
                nem12_writer.writerow(
                    [self.nem_file_end_of_record_indicator]
                )  # create end of record indicator

            with open(f"{temp_text_file}.txt", mode="r") as nem12_file:
                meter_data_values = nem12_file.read()
            os.remove(f"{temp_text_file}.txt")  # remove temp txt file
            meter_data_file.transactions(
                transaction_id=self.file_message_id,
                transaction_date=self.message_trans_datetime,
                transaction_type="MeterDataNotification",
                transaction_schema_version="r25",
                csv_interval_data=meter_data_values,
                participant_role="FRMP",
            )
            meter_data_file.write_xml(
                output_filename=self.nem_mdmt_filename,
                output_directory=OUTPUT_DIRECTORY,
            )

            create_zip_file(self.nem_mdmt_filename)


meter_data_csv = "md_test.csv"
input_file_name = INPUT_DIRECTORY + meter_data_csv

with open(input_file_name, "r", newline="") as input_csv:
    reader = csv.reader(input_csv, delimiter=",")
    next(reader, None)  # skips header row if not required.
    for item, meter_data_config in enumerate(reader, 1):
        test = generate_meter_data_file(meter_data_config_row=meter_data_config)
        test.generate_nem12_records()
