from notifiers.discord import DiscordNotifier
from utils.config import DEFAULT_NOTIFY_ON, SEND_SUMMARY_DISCORD
from utils.logger import get_logger
logger = get_logger("CronHub")

class NotifierManager:
    def __init__(self):
        self.notifiers = [DiscordNotifier()]

    def notify(self, task, status, **kwargs):
        """Envoie les notifications selon la config."""
        notify_on = task.notifications.get("notify_on", DEFAULT_NOTIFY_ON)
        # Cas "none" → aucune notification
        if "none" in notify_on:
            logger.info(f"ℹ️ Notifications désactivées pour {task.script}")
            return
        if status == "success_with_warnings" and "success" in notify_on and "success_with_warnings" not in notify_on:
            status_to_check = "success"
        else:
            status_to_check = status

        if status_to_check not in notify_on:
            return
        
        for notifier in self.notifiers:            
            notifier.send(task, status, **kwargs)
            
    def notify_summary(self, summary):
        if not SEND_SUMMARY_DISCORD:
            return
        content = (
            f"📊 **Résumé CronHub**\n"
            f"✅ {summary['success']} succès\n"
            f"⚠️ {summary['success_with_warnings']} avec warnings\n"
            f"❌ {summary['failure']} échecs\n"
            f"⏱️ Durée totale : {summary['total_duration']:.2f}s"
        )
        for notifier in self.notifiers:
            notifier.send_summary(content)
