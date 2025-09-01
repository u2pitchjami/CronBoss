# notifiers/discord.py (extrait)
from __future__ import annotations

import requests

from utils.config import DISCORD_WEBHOOK_URL
from utils.logger import get_logger
from utils.types import Status, TaskLike

logger = get_logger("CronBoss")


class DiscordNotifier:
    """
    Notifier Discord via Webhook (content simple).
    """

    def send(self, task: TaskLike, status: Status, **kwargs: object) -> None:
        if not DISCORD_WEBHOOK_URL:
            logger.warning("⚠️ Pas de DISCORD_WEBHOOK_URL → pas de notif Discord.")
            return

        # duration: rendu robuste pour mypy (kwargs: object)
        raw_dur = kwargs.get("duration", 0)
        if isinstance(raw_dur, (int | float)):
            duration = float(raw_dur)
        else:
            duration = 0.0

        # stderr peut être absent ou non-str
        stderr_val = kwargs.get("stderr")
        stderr: str | None = stderr_val if isinstance(stderr_val, str) else None

        # (facultatif si tu veux t'en servir plus tard)
        # returncode_val = kwargs.get("returncode")
        # returncode: Optional[int] = returncode_val if isinstance(returncode_val, int) else None

        # Message
        if status == "success":
            content = f"✅ **{task.script.name}** → SUCCESS en {duration:.2f}s"
        elif status == "success_with_warnings":
            content = f"⚠️ **{task.script.name}** → SUCCESS AVEC WARNINGS en {duration:.2f}s"
            if stderr:
                warn_msg = stderr.strip()
                warn_msg = (warn_msg[:800] + "...") if len(warn_msg) > 800 else warn_msg
                content += f"\n```{warn_msg}```"
        elif status in ("failure", "retry"):
            # On affiche l'erreur sur failure ; sur retry, à toi de décider si tu veux notifier
            if stderr:
                err_msg = stderr.strip()
                err_msg = (err_msg[:800] + "...") if len(err_msg) > 800 else err_msg
                content = f"❌ **{task.script.name}** → FAILURE en {duration:.2f}s\n```{err_msg}```"
            else:
                content = f"❌ **{task.script.name}** → FAILURE en {duration:.2f}s"
        else:
            # Cas "Non" (pas encore exécuté) ou autres → on reste factuel
            content = f"⚡ **{task.script.name}** → {status.upper()}"

        try:
            resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=5)
            if resp.status_code != 204:
                logger.error("⚠️ Discord a répondu %s: %s", resp.status_code, resp.text)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("❌ Erreur envoi Discord : %s", exc)
