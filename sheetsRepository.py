import json
import os
from typing import List, Dict, Optional, Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build, logger


class SheetsRepository:
    """
    Unified repository for Google Sheets-backed storage.
    Sheets:
      - Intervals: A(account) B(queue) C(intervals_json)
      - Devices:   A(device_uuid) B(device_type) C(push_address) D(device_details)
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    # ---------------------------------------------------------
    # Init
    # ---------------------------------------------------------

    def __init__(
        self,
        spreadsheet_id_env_key: str,
        credentials_path: str = "credentials.json",
        intervals_sheet: str = "Intervals",
        devices_sheet: str = "Devices",
    ) -> None:
        if os.getenv(spreadsheet_id_env_key):
            # From envs
            self.spreadsheet_id = os.getenv(spreadsheet_id_env_key)
            logger.debug(f"Service spreadsheet id: {self.spreadsheet_id}")
        else:
            # Test from string
            self.spreadsheet_id = "SPREADSHEET_ID"

        self.intervals_sheet = intervals_sheet
        self.devices_sheet = devices_sheet

        if os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT"):
            # From envs
            service_account_info = json.loads(
                os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT")
            )
            logger.debug(f"Service account info: {service_account_info}")
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES,
            )
        else:
            # Test from local file
            creds = Credentials.from_service_account_file(
                credentials_path,
                scopes=self.SCOPES,
            )


        self.service = build("sheets", "v4", credentials=creds)
        self.sheet = self.service.spreadsheets()

    # ---------------------------------------------------------
    # Generic helpers
    # ---------------------------------------------------------

    def _get_rows(self, sheet_name: str, columns: str) -> List[List[str]]:
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!{columns}",
        ).execute()

        return result.get("values", [])

    def _update_row(
        self,
        sheet_name: str,
        row_index: int,
        columns: str,
        values: List[str],
    ) -> None:
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!{columns}{row_index}",
            valueInputOption="RAW",
            body={"values": [values]},
        ).execute()

    def _append_row(
        self,
        sheet_name: str,
        columns: str,
        values: List[str],
    ) -> None:
        self.sheet.values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!{columns}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        ).execute()

    # =========================================================
    # Intervals API
    # =========================================================

    def _find_interval_row(
        self, account: int, queue: str
    ) -> Optional[Tuple[int, Dict]]:
        rows = self._get_rows(self.intervals_sheet, "A:C")

        for idx, row in enumerate(rows, start=1):
            if len(row) < 2:
                continue

            try:
                row_account = int(row[0])
            except ValueError:
                continue

            if row_account == account and row[1] == queue:
                raw = row[2] if len(row) > 2 else ""
                intervals = json.loads(raw) if raw.strip() else []

                return idx, {
                    "account": row_account,
                    "queue": row[1],
                    "intervals": intervals,
                }

        return None

    def get_intervals(self, account: int, queue: str) -> str:
        found = self._find_interval_row(account, queue)
        return found[1]["intervals"] if found else ""

    def save_intervals(
        self,
        account: int,
        queue: str,
        intervals: str,
    ) -> None:
        intervals_json = json.dumps(intervals, ensure_ascii=False)

        found = self._find_interval_row(account, queue)

        if found:
            row_index, _ = found
            self._update_row(
                self.intervals_sheet,
                row_index,
                "A:C",
                [str(account), queue, intervals_json],
            )
        else:
            self._append_row(
                self.intervals_sheet,
                "A:C",
                [str(account), queue, intervals_json],
            )

    def clear_intervals(self, account: int, queue: str) -> None:
        found = self._find_interval_row(account, queue)
        if not found:
            return

        row_index, _ = found
        self._update_row(
            self.intervals_sheet,
            row_index,
            "A:C",
            [str(account), queue, ""],
        )
        return

    def list_intervals(self) -> List[Dict[str, str]]:
        intervals: List[Dict[str, str]] = []

        for row in self._get_rows(self.intervals_sheet, "A:C"):
            if not row or not row[0]:
                continue

            intervals.append({
                "account": row[0],
                "queue": row[1] if len(row) > 1 else "",
                "intervals": row[2] if len(row) > 2 else ""
            })

        return intervals

    # =========================================================
    # Devices API
    # =========================================================

    def _find_device_row(
        self, device_uuid: str
    ) -> Optional[Tuple[int, Dict[str, str]]]:
        rows = self._get_rows(self.devices_sheet, "A:E")

        for idx, row in enumerate(rows, start=1):
            if not row or row[0] != device_uuid:
                continue

            return idx, {
                "device_uuid": row[0],
                "device_type": row[1] if len(row) > 1 else "",
                "push_address": row[2] if len(row) > 2 else "",
                "watched_queue": row[3] if len(row) > 3 else "",
                "device_details": row[4] if len(row) > 4 else "",
            }

        return None

    def get_device(self, device_uuid: str) -> Optional[Dict[str, str]]:
        found = self._find_device_row(device_uuid)
        return found[1] if found else None

    def save_device(
        self,
        device_uuid: str,
        device_type: str,
        push_address: str,
        watched_queue: str,
        device_details: str,
    ) -> None:
        values = [
            device_uuid,
            device_type,
            push_address,
            watched_queue,
            device_details,
        ]

        found = self._find_device_row(device_uuid)

        if found:
            row_index, _ = found
            self._update_row(
                self.devices_sheet,
                row_index,
                "A:E",
                values,
            )
        else:
            self._append_row(
                self.devices_sheet,
                "A:E",
                values,
            )

    def delete_device(self, device_uuid: str) -> None:
        found = self._find_device_row(device_uuid)
        if not found:
            return

        row_index, _ = found
        self._update_row(
            self.devices_sheet,
            row_index,
            "A:E",
            ["", "", "", "", ""],
        )

    def list_devices(self) -> List[Dict[str, str]]:
        devices: List[Dict[str, str]] = []

        for row in self._get_rows(self.devices_sheet, "A:D"):
            if not row or not row[0]:
                continue

            devices.append({
                "device_uuid": row[0],
                "device_type": row[1] if len(row) > 1 else "",
                "push_address": row[2] if len(row) > 2 else "",
                "watched_queue": row[3] if len(row) > 3 else "",
                "device_details": row[4] if len(row) > 4 else "",
            })

        return devices
