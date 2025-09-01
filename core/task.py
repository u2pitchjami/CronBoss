from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import threading
import time
from typing import IO, Literal

from core.scheduler import should_run
from handlers.get_interpreter import get_interpreter_from_project, load_interpreters_map
from utils.config import DEFAULT_VENV, INTERPRETERS_PATH, WARNINGS_AS_FAILURE
from utils.lock import release_task_lock, try_acquire_task_lock
from utils.logger import get_logger
from utils.types import (
    CleanupCfg,
    InterpretersMap,
    NotificationsCfg,
    StartHandle,
    Status,
    TaskConfig,
)

logger: logging.Logger = get_logger("CronBoss")


class Task:
    """
    Représente une tâche CronHub (config YAML + état d'exécution).
    """

    def __init__(
        self,
        config: TaskConfig,
        source_file: str,
        interpreters: InterpretersMap | None = None,
    ) -> None:
        """
        Initialise une tâche à partir d'une configuration YAML et de son fichier source.

        :param config: Dictionnaire typé décrivant la tâche (voir utils.types.TaskConfig).
        :param source_file: Fichier YAML d'origine (chemin).
        :param interpreters: Mapping optionnel pour la résolution des interpréteurs Python.
        """
        # Config issue du YAML
        self.config: TaskConfig = config
        self.source_file: str = source_file
        self.type: str = config.get("type", "python")
        self.script: Path = Path(config.get("script", ""))
        self.args: str = config.get("args", "")
        self.enabled: bool = bool(config.get("enabled", True))
        self.exclusive: bool = bool(config.get("exclusive", True))
        self.cleanup: CleanupCfg | None = config.get("cleanup")  # TypedDict si présent
        self.attempts: int = 0

        notif_cfg: NotificationsCfg = config.get("notifications", {})  # parfaitement typé
        self.notifications: NotificationsCfg = {
            "notify_on": notif_cfg.get("notify_on", ["failure"]),
            "channels": notif_cfg.get("channels", ["discord"]),
        }

        # 📌 Résolution de l'interpréteur Python
        if self.type == "python":
            if interpreters is None:  # fallback autonome
                interpreters = load_interpreters_map(INTERPRETERS_PATH)
            self.interpreter: str | None = (
                config.get("interpreter")
                or get_interpreter_from_project(str(self.script), source_file, interpreters)
                or DEFAULT_VENV
            )
        else:
            self.interpreter = None

        # cwd calculé
        self.cwd: str = self._resolve_cwd()

        # Retry & timeout
        self.retries: int = int(config.get("retries", 0))
        self.retry_delay: int = int(config.get("retry_delay", 30))
        self.timeout: int = int(config.get("timeout", 0))  # 0 = pas de limite
        self.timeout_mode: str = config.get("timeout_mode", "strict")

        # Runtime state
        self.proc: subprocess.Popen[str] | None = None
        self.start_time: float | None = None
        self.duration: float | None = None
        self.returncode: int | None = None
        self.stdout: str | None = None
        self.stderr: str | None = None
        self.stdout_lines: list[str] = []
        self.stderr_lines: list[str] = []
        self._task_lock_fh: IO[str] | None = None

    def _resolve_cwd(self) -> str:
        """
        Détermine le répertoire de travail correct.

        - Si Bash : dossier du script
        - Si Python : cherche un .env en remontant jusqu'à 3 niveaux
        """
        script_dir = self.script.parent.resolve()

        if self.type == "bash":
            return str(script_dir)

        if self.type == "python":
            current = script_dir
            for _ in range(3):  # on check max 3 niveaux
                env_file = current / ".env"
                if env_file.exists():
                    return str(current)
                current = current.parent
            # fallback : dossier du script
            return str(script_dir)

        # fallback pour types inconnus
        return str(Path.cwd())

    def should_run(self, hour: int, minute: int, weekday: int, day: int) -> bool:
        """
        Vérifie si la tâche doit être lancée (via scheduler).

        :param hour: Heure courante (0..23)
        :param minute: Minute courante (0..59)
        :param weekday: Jour de la semaine (0=Mon .. 6=Sun)
        :param day: Jour du mois (1..31)
        """
        result = should_run(self.config, hour, minute, weekday, day)
        return bool(result)

    def can_start(self) -> bool:
        """
        Vérifie si la tâche peut être lancée.

        - Retourne False si exclusive=True et qu'une instance est déjà en cours.
        - Sinon True.
        """
        if not self.enabled:
            return False
        if not self.exclusive:
            return True

        # 1) Exclusivité intra-run
        if self.proc and self.proc.poll() is None:
            return False

        # 2) Exclusivité inter-run (autre cronboss déjà en train d'exécuter ce script)
        if self._task_lock_fh is None:
            self._task_lock_fh = try_acquire_task_lock(str(self.script))
            if self._task_lock_fh is None:
                logger.info("⛔ Lock déjà pris pour %s — on skip.", self.script)
                return False
        return True

    @staticmethod
    def _stream_reader(pipe: IO[str], buffer: list[str], name: str, logger: logging.Logger) -> None:
        """
        Lit un flux en temps réel et stocke les lignes.

        :param pipe: Flux à lire (stdout/stderr).
        :param buffer: Buffer cible où stocker les lignes.
        :param name: Nom du flux pour le log ("stdout" / "stderr").
        :param logger: Logger à utiliser.
        """
        for line in iter(pipe.readline, ""):  # '' car déjà str
            decoded = line.strip()
            buffer.append(decoded)
            logger.debug("[%s] %s", name, decoded)
        pipe.close()

    def start(self, handle: StartHandle) -> None:
        """
        Démarre la tâche sans bloquer.

        :param handle: Dictionnaire typé contenant au moins "proc" (Popen[str]).
        """
        # Sécurité si start() est appelé sans passer par can_start()
        if self.exclusive and self._task_lock_fh is None:
            self._task_lock_fh = try_acquire_task_lock(str(self.script))
            if self._task_lock_fh is None:
                logger.info("⛔ Lock indisponible pour %s — démarrage annulé.", self.script)
                return
        self.proc = handle["proc"]
        self.start_time = time.time()
        self.attempts += 1  # 🔑 incrément à chaque lancement
        self.returncode = None
        self.stdout_lines = []
        self.stderr_lines = []

        # Sécurise les pipes pour mypy : stdout/stderr ne sont pas Optional ici si créés avec PIPE+text
        assert self.proc is not None
        if self.proc.stdout is None or self.proc.stderr is None:
            # Si le créateur de Popen n'a pas passé stdout/stderr=PIPE, on évite un crash.
            logger.warning("[CronHub] Process sans stdout/stderr pipe — pas de stream en temps réel")
        else:
            # Threads pour vider stdout et stderr en continu
            threading.Thread(
                target=self._stream_reader,
                args=(self.proc.stdout, self.stdout_lines, "stdout", logger),
                daemon=True,
            ).start()
            threading.Thread(
                target=self._stream_reader,
                args=(self.proc.stderr, self.stderr_lines, "stderr", logger),
                daemon=True,
            ).start()

        if self.attempts > 1:
            logger.info("[CronHub] 🔄 Retry %s/%s pour %s", self.attempts, self.retries, self.script)
        else:
            logger.info("[CronHub] ▶️ Lancement %s", self.script)

    def finish(self, timeout: int | None = None) -> None:
        """
        Récupère les infos quand la tâche est terminée.

        :param timeout: Délai max (secondes) avant arrêt (None = sans limite).
        """
        if self.proc is None:
            logger.warning("[CronHub] finish() appelé sans process")
            return
        try:
            if timeout:
                self.stdout, self.stderr = self.proc.communicate(timeout=timeout)
            else:
                self.stdout, self.stderr = self.proc.communicate()
        except subprocess.TimeoutExpired:
            import os
            import signal

            # On tue le groupe puis le proc
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except Exception:  # pragma: no cover - garde de sécurité
                logger.debug("[CronHub] killpg non disponible/nécessaire")

            self.proc.kill()
            self.stderr = f"⏱️ Timeout dépassé ({timeout}s)"
            self.returncode = -1
            self.duration = time.time() - (self.start_time or time.time())
            # 🔑 Ajout du log explicite
            logger.info("[CronHub] 🚨 Timeout : %s interrompu après %ss", self.script, timeout)
            return

        self.duration = time.time() - (self.start_time or time.time())
        self.returncode = self.proc.returncode
        # 🔑 Concatène les lignes récupérées
        self.stdout = "\n".join(self.stdout_lines[-20:])
        self.stderr = "\n".join(self.stderr_lines[-20:])

        if self.returncode != 0:
            logger.error("[CronHub] ❌ Erreur sur %s: %s", self.script, self.stderr)
        else:
            logger.info("[CronHub] ✅ Succès %s", self.script)
        # Relâche le lock après fin complète (hors retry)
        release_task_lock(self._task_lock_fh)
        self._task_lock_fh = None

    def check_status(self) -> Literal["success", "failure", "retry"] | None:
        """
        Vérifie l'état sans bloquer, gère timeout & retry sans appeler communicate().

        Retour:
        - "success": terminé avec code 0
        - "failure": terminé avec code != 0 ou timeout
        - "retry": terminé avec code != 0 ET retry encore possible
        - None: toujours en cours
        """
        if self.proc is None:
            return None

        now = time.time()

        # Timeout strict (sans communicate)
        if self.timeout > 0 and (now - (self.start_time or now)) > self.timeout:
            try:
                self.proc.kill()
            except Exception:  # pragma: no cover - garde
                pass
            self.returncode = -1
            self.stderr = f"⏱️ Timeout dépassé ({self.timeout}s)"
            self.duration = now - (self.start_time or now)
            return "failure"

        rc = self.proc.poll()
        if rc is None:
            return None

        # Terminé (ne pas lire stdout/stderr ici)
        self.returncode = rc
        self.duration = now - (self.start_time or now)

        if rc == 0:
            return "success"

        # Échec → retry possible ?
        if self.attempts <= self.retries:
            time.sleep(self.retry_delay)
            return "retry"

        return "failure"

    def get_status(self) -> Status:
        """
        Retourne le statut de la tâche : "success", "failure", "success_with_warnings" ou "Non".
        """
        if self.returncode is None:
            return "Non"
        if self.returncode != 0:
            return "failure"

        if self.stderr and ("warning" in self.stderr.lower() or "error" in self.stderr.lower()):
            if WARNINGS_AS_FAILURE.lower() == "true":
                return "failure"
            return "success_with_warnings"

        return "success"

    def is_success(self) -> bool:
        """
        Retourne True si le job est OK.
        """
        return self.returncode == 0

    def __repr__(self) -> str:
        """
        Représentation courte pour logs/debug.
        """
        return f"<Task {self.script.name} status={'?'}>"
