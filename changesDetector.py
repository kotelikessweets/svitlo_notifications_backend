from typing import List, Dict, Tuple
import json
from datetime import datetime
import logging

from oblEnergoDataRetriver import OblEnergoDataRetriever
from oblEnergoResponseUnwrapper import get_changes
from sheetsRepository import SheetsRepository

logger = logging.getLogger(__name__)

class ChangesDetector:
    #LocalStorage
    last_update_devices: datetime
    last_update_queues: datetime
    devices_list: List[Dict[str, str]]
    queue_list: List[Dict[str, str]]

    def __init__(
            self,
            repo_handler: SheetsRepository):
        self.repo_handler = repo_handler

# Initial data read task
    def populate(self) -> None:
        logger.info("Start populating changes detector")
        self.queue_list = self.repo_handler.list_intervals()
        self.devices_list = self.repo_handler.list_devices()
        self.last_update_queues = datetime.now()
        self.last_update_devices = datetime.now()
        logger.info(f"End populating changes detector. Queues count: {len(self.queue_list)}. Devices count: {len(self.devices_list)}")

# Update devices list only when new device is registered
    def repopulate_devices(self) -> None:
        logger.info(f"Start repopulating devices list. Devices count: {len(self.devices_list)}")
        self.devices_list = self.repo_handler.list_devices()
        self.last_update_devices = datetime.now()
        logger.info(f"End repopulating devices list. Devices count: {len(self.devices_list)}")


# Main worker
    def seek_changes(self) -> Tuple[str, int]:


        # Get updated data from OblEnergo API
        logger.info(f"Start seek_changes. Queues count: {len(self.queue_list)}")
        data_retriever = OblEnergoDataRetriever()
        oblenergo_data = data_retriever.get_oblenergo_data(self.queue_list)
        logger.info(f"End oblenergo requests. Results: \n{json.dumps(oblenergo_data, indent=2)}")

        # Find queues that have significant changes
        logger.info(f"Start analyzing changes. Queues count: {len(self.queue_list)}")
        changed_queues = get_changes(oblenergo_data)

        # Save the updated responses anyway
        record: dict[str, str]
        for record in oblenergo_data:
            try:
                self.repo_handler.save_intervals(int(record.get("account")),record.get("queue"),record.get("oblenergo_response"))
            except Exception as e:
                logger.error("Exception while saving intervals for queue" + record.get("queue") + f" : {e}")
        self.queue_list = self.repo_handler.list_intervals()


        # Return changed queues and number of changed queues
        self.last_update_queues = datetime.now()
        results = (changed_queues, len(changed_queues))
        logger.info(f"End seek_changes. Results: {results}")
        return results
