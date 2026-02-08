from typing import List, Dict, Optional, Tuple

import logging
import requests
import certifi
import ssl
import time
import random

logger = logging.getLogger(__name__)


class OblEnergoDataRetriever:

    URL = "https://interruptions.energy.cn.ua/api/info_disable"

    HEADERS = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "uk",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Origin": "https://interruptions.energy.cn.ua",
        "Pragma": "no-cache",
        "Referer": "https://interruptions.energy.cn.ua/interruptions",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Storage-Access": "none",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/143.0.0.0 Safari/537.36"
        ),
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    def get_oblenergo_data(
            self,
            queue_list:  List[Dict[str, str]]
    ) -> List[Dict[str, str]]:

        logger.info("Start getting data")
        logger.info(f"OpenSSL: {ssl.OPENSSL_VERSION}")
        logger.info(f"Default verify paths: {ssl.get_default_verify_paths()}")
        logger.info(f"Certifi: {certifi.where()}")

        results: List[Dict[str, str]] = []

        for record in queue_list:
            account = record.get("account")

            if not account:
                logger.warning("Missing account field", extra={"record": record})
                continue

            payload = {"person_accnt": account}

            logger.info(f"Start request for account: {account}")

            try:
                response = requests.post(
                    self.URL,
                    json=payload,
                    headers=self.HEADERS,
                    timeout=10,
                    verify=certifi.where()
                )

                response.raise_for_status()

                data = response.json()

                results.append({
                    **record,
                    "oblenergo_response": data,
                })

                logger.info(f"End request for account: {account}. Response: {response} \n Data: {data}")

            except requests.RequestException as exc:
                logger.error(f"Request failed for account: {account}. Error: {str(exc)}")
            '''
                results.append({
                    **record,
                    "error": str(exc),
                })
            '''
            time.sleep(1 + round(random.random(), 3))

        return results
