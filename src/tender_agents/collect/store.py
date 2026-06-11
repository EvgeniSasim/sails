import json
import os
from pathlib import Path
from typing import Set, Tuple, Union
from tender_agents.models import TenderRecord

class JsonlStore:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self._seen_keys: Set[Union[Tuple[str, str], str]] = set()
        self._load_existing_keys()

    def _get_key(self, record: TenderRecord) -> Union[Tuple[str, str], str]:
        if record.external_id:
            return (record.platform, record.external_id)
        # Normalize URL: strip trailing slash and ensure it's a string
        url_str = str(record.url).rstrip("/")
        return url_str

    def _load_existing_keys(self):
        if not self.path.exists():
            return

        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # We need to reconstruct a TenderRecord-like object or just use the dict
                    # to extract the key.
                    platform = data.get("platform")
                    external_id = data.get("external_id")
                    url = data.get("url")

                    if external_id and platform:
                        self._seen_keys.add((platform, external_id))
                    elif url:
                        self._seen_keys.add(url.rstrip("/"))
                except (json.JSONDecodeError, KeyError):
                    continue

    def write(self, record: TenderRecord) -> bool:
        key = self._get_key(record)
        if key in self._seen_keys:
            return False

        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        self._seen_keys.add(key)
        return True
