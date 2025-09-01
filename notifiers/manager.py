from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from notifiers.discord import DiscordNotifier
from utils.config import DEFAULT_NOTIFY_ON, SEND_SUMMARY_DISCORD
from utils.logger import get_logger
from utils.types import NotificationsCfg, Notifier, Status, SummaryPayload, TaskLike

logger = get_logger("CronHub")


class NotifierManager:
    """
    Agrège tous les notifiers et applique la politique de diffusion.
    """

    def __init__(self, notifiers: Iterable[Notifier] | None = None) -> None:
        if notifiers is None:
            self.notifiers: list[Notifier] = [cast(Notifier, DiscordNotifier())]
        else:
            self.notifiers = list(notifiers)

    def notify(self, task: TaskLike, status: Status, **kwargs: object) -> None:
        """
        Envoie les notifications selon la config de la tâche (task.notifications) et la politique globale
        (DEFAULT_NOTIFY_ON).

        - "none" dans notify_on désactive toute notification.
        - Si status == "success_with_warnings" mais que "success" est autorisé
          et pas "success_with_warnings", on rabat sur "success".
        """
        cfg: NotificationsCfg = task.notifications or {}
        notify_on = cfg.get("notify_on", DEFAULT_NOTIFY_ON)

        # Cas "none" → aucune notification
        if "none" in notify_on:
            logger.info("⚡ Notifications désactivées pour %s", task.script)
            return

        status_to_check: Status = status
        if status == "success_with_warnings" and "success" in notify_on and "success_with_warnings" not in notify_on:
            status_to_check = "success"

        if status_to_check not in notify_on:
            return

        for notifier in self.notifiers:
            try:
                notifier.send(task, status, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Notifier %s a échoué: %s", type(notifier).__name__, exc)

    def notify_summary(self, summary: SummaryPayload) -> None:
        """
        Diffuse un résumé global (si activé via SEND_SUMMARY_DISCORD).
        """
        if not SEND_SUMMARY_DISCORD:
            return

        content = (
            "📊 **Résumé CronHub**\n"
            f"✅ {summary['success']} succès\n"
            f"⚠️ {summary['success_with_warnings']} avec warnings\n"
            f"❌ {summary['failure']} échecs\n"
            f"⏱️ Durée totale : {summary['total_duration']:.2f}s"
        )
        for notifier in self.notifiers:
            try:
                notifier.send_summary(content)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Notifier %s (summary) a échoué: %s", type(notifier).__name__, exc)
