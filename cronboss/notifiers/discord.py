import os
import requests
from utils.config import DISCORD_WEBHOOK_URL
from utils.logger import get_logger

logger = get_logger("CronBoss")

class DiscordNotifier:
    def send(self, task, status, **kwargs):
        if not DISCORD_WEBHOOK_URL:
            logger.warning("⚠️ Pas de DISCORD_WEBHOOK_URL → pas de notif Discord.")
            return

        duration = kwargs.get("duration", 0)
        returncode = kwargs.get("returncode")
        stdout = kwargs.get("stdout")
        stderr = kwargs.get("stderr")

        icon = "✅" if status == "success" else "❌"
        content = f"{icon} **{task.script.name}** → {status.upper()} en {duration:.2f}s"

        if status == "success":
            icon = "✅"
            content = f"{icon} **{task.script.name}** → SUCCESS en {duration:.2f}s"
        elif status == "success_with_warnings":
            icon = "⚠️"
            content = f"{icon} **{task.script.name}** → SUCCESS AVEC WARNINGS en {duration:.2f}s"
            if stderr:
                warn_msg = stderr.strip()
                warn_msg = warn_msg[:800] + ("..." if len(warn_msg) > 800 else "")
                content += f"\n```{warn_msg}```"
        else:  # failure
            icon = "❌"
            content = f"{icon} **{task.script.name}** → FAILURE en {duration:.2f}s"
            if stderr:
                err_msg = stderr.strip()
                err_msg = err_msg[:800] + ("..." if len(err_msg) > 800 else "")
                content += f"\n```{err_msg}```"

        try:
            resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=5)
            if resp.status_code != 204:
                logger.error(f"⚠️ Discord a répondu {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Erreur envoi Discord : {e}")
            
    def send_summary(self, content):
        if not DISCORD_WEBHOOK_URL:
            logger.info("ℹ️ Résumé Discord non envoyé (pas de DISCORD_WEBHOOK_URL)")
            return
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=5)
        except Exception as e:
            logger.error(f"❌ Impossible d’envoyer le résumé Discord : {e}")
