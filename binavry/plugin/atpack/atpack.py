from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from bs4 import BeautifulSoup
from remotezip2 import RemoteZip
from requests import Session

from .atdf import ATDeviceInfo


@dataclass(frozen=True)
class ATPackInfo:
    device: str
    link: str
    _session: Session

    @cached_property
    def device_info(self) -> ATDeviceInfo:
        with RemoteZip(url=self.link, session=self._session) as rz:
            return ATDeviceInfo(rz.read(f'atdf/{self.device}.atdf'))


class PackDownloader:
    URL = 'http://packs.download.atmel.com/'

    def __init__(self):
        self._packs: list[ATPackInfo] = []
        self._session = Session()

    def update(self) -> None:
        resp = self._session.get(PackDownloader.URL)

        soup = BeautifulSoup(resp.text, features='xml')
        packs = soup.find(id='atmel-dfp')
        if packs is None:
            return

        packs = packs.find_all(class_='pack-card')

        for pack in packs:
            link = pack.find(class_='pack-version')
            if link is None:
                continue
            link = PackDownloader.URL + str(link['href'])

            for device in pack.find_all(class_='device-name'):
                self._packs.append(
                    ATPackInfo(device=device.text, link=link, _session=self._session)
                )

    @property
    def packs(self) -> tuple[ATPackInfo, ...]:
        return tuple(self._packs)
