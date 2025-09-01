# notifiers/email.py
from __future__ import annotations

from utils.types import Notifier, Status, TaskLike


class EmailNotifier(Notifier):
    def __init__(self, smtp_url: str, from_addr: str, to_addrs: list[str]) -> None:
        self.smtp_url = smtp_url
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, task: TaskLike, status: Status, **kwargs: object) -> None:
        # TODO: implémenter envoi via SMTP/SendGrid/etc.
        pass

    def send_summary(self, content: str) -> None:
        # TODO: idem
        pass
