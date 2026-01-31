import json
import logging
from typing import Any, Dict, List

from timeIntervalsEx import TimeIntervalsEX

logger = logging.getLogger(__name__)


def get_changes(raw: List[Dict[str, Any]]) -> List[str]:

    changed_queues = []

    for entry in raw:
        account = entry.get("account")
        queue = entry.get("queue")
        saved = json.loads(entry.get("intervals") or "{}")
        saved_data = saved.get("aData", []) or []
        response = entry.get("oblenergo_response", {}) or {}
        response_data = response.get("aData", []) or []

        logger.info(f"Account:{account}; Queue: {queue}; Saved data: {saved_data}")
        logger.info(f"Account:{account}; Queue: {queue}; Response data: {response_data}")

        if not account or not isinstance(response_data, list):
            continue

        record = [account, queue, TimeIntervalsEX(), TimeIntervalsEX()]

        for item in saved_data:
            start = item.get("acc_begin")
            end = item.get("accend_plan")

            if start and end:
                record[2].append((start, end))

        for item in response_data:
            start = item.get("acc_begin")
            end = item.get("accend_plan")

            if start and end:
                record[3].append((start, end))

        logger.info(f"Comparison record: Account:{record[0]} Queue:{record[1]} Saved data: {record[2].pretty_print(False)} Response data: {record[3].pretty_print(False)}")

        if record[2].compare(compare_to=record[3]):
            logger.info(f"Should notify: {record[1]}")
            changed_queues.append(record[1])

    logger.info(f"Changed queues: {changed_queues}")
    return changed_queues



