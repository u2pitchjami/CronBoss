
import time
import subprocess
import threading
from pathlib import Path
from utils.logger import get_logger
from utils.config import WARNINGS_AS_FAILURE, DEFAULT_VENV, INTERPRETERS_PATH
from core.scheduler import should_run
from handlers.get_interpreter import load_interpreters_map, get_interpreter_from_project

logger = get_logger("CronHub")

class Task:
    """Représente une tâche CronHub (config YAML + état d'exécution)."""

    def __init__(self, config: dict, source_file: str, interpreters: dict = None):
        # Config issue du YAML
        self.config = config
        self.source_file = source_file
        self.type = config.get("type", "python")
        self.script = Path(config.get("script"))
        self.args = config.get("args", "")
        self.enabled = config.get("enabled", True)
        self.exclusive = config.get("exclusive", True)
        self.cleanup = config.get("cleanup", None)
        self.attempts = 0
        notif_cfg = config.get("notifications") or {}
        self.notifications = {
            "notify_on": notif_cfg.get("notify_on", ["failure"]),
            "channels": notif_cfg.get("channels", ["discord"])
        }
        # 📌 Résolution de l'interpréteur Python
        if self.type == "python":
            if interpreters is None:  # fallback autonome
                interpreters = load_interpreters_map(INTERPRETERS_PATH)
            self.interpreter = (
                config.get("interpreter")
                or get_interpreter_from_project(str(self.script), source_file, interpreters)
                or DEFAULT_VENV
            )
        else:
            self.interpreter = None
        
        #cwd
        self.cwd = self._resolve_cwd()

        # Retry & timeout
        self.retries = int(config.get("retries", 0))
        self.retry_delay = int(config.get("retry_delay", 30))
        self.timeout = int(config.get("timeout", 0))  # 0 = pas de limite
        self.timeout_mode = config.get("timeout_mode", "strict")

        # Runtime state
        self.proc = None
        self.start_time = None
        self.duration = None
        self.returncode = None
        self.stdout = None
        self.stderr = None

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

    def should_run(self, hour, minute, weekday, day):
        """Vérifie si la tâche doit être lancée (via scheduler)."""
        return should_run(self.config, hour, minute, weekday, day)

    def can_start(self) -> bool:
        """
        Vérifie si la tâche peut être lancée.
        - Retourne False si exclusive=True et qu'une instance est déjà en cours.
        - Sinon True.
        """
        if self.exclusive and self.proc and self.proc.poll() is None:
            return False
        return True

    @staticmethod
    def _stream_reader(pipe, buffer, name, logger):
        """Lit un flux en temps réel et stocke les lignes."""
        for line in iter(pipe.readline, ''):  # '' car déjà str
            decoded = line.strip()
            buffer.append(decoded)
            logger.debug(f"[{name}] {decoded}")
        pipe.close()

    def start(self, handle):        
        """Démarre la tâche sans bloquer."""
        self.proc = handle["proc"]
        self.start_time = time.time()
        self.attempts += 1  # 🔑 incrément à chaque lancement
        self.returncode = None
        self.stdout_lines = []
        self.stderr_lines = []

        # Threads pour vider stdout et stderr en continu
        threading.Thread(
            target=self._stream_reader,
            args=(self.proc.stdout, self.stdout_lines, "stdout", logger),
            daemon=True
        ).start()
        threading.Thread(
            target=self._stream_reader,
            args=(self.proc.stderr, self.stderr_lines, "stderr", logger),
            daemon=True
        ).start()
        
        if self.attempts > 1:
            logger.info(f"[CronHub] 🔄 Retry {self.attempts}/{self.retries} pour {self.script}")
        else:
            logger.info(f"[CronHub] ▶️ Lancement {self.script}")
            
    
    
    def finish(self, timeout=None):
        """Récupère les infos quand la tâche est terminée."""
        try:
            if timeout:
                self.stdout, self.stderr = self.proc.communicate(timeout=timeout)
            else:
                self.stdout, self.stderr = self.proc.communicate()
        except subprocess.TimeoutExpired:
            import os, signal
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            self.proc.kill()
            self.stderr = f"⏱️ Timeout dépassé ({timeout}s)"
            self.returncode = -1
            self.duration = time.time() - self.start_time
            # 🔑 Ajout du log explicite
            logger.info(f"[CronHub] 🚨 Timeout : {self.script} interrompu après {timeout}s")
            return
        self.duration = time.time() - self.start_time
        self.returncode = self.proc.returncode
        # 🔑 Concatène les lignes récupérées
        self.stdout = "\n".join(self.stdout_lines[-20:])
        self.stderr = "\n".join(self.stderr_lines[-20:])

        if self.returncode != 0:
            logger.error(f"[CronHub] ❌ Erreur sur {self.script}: {self.stderr}")
        else:
            logger.info(f"[CronHub] ✅ Succès {self.script}")

    def check_status(self):
        """Vérifie l'état sans bloquer, gère timeout et retry."""
        if not self.proc:
            return None

        # Timeout strict
        if self.timeout > 0 and (time.time() - self.start_time) > self.timeout:
            self.proc.kill()
            self.returncode = -1
            self.stderr = f"⏱️ Timeout dépassé ({self.timeout}s)"
            self.duration = time.time() - self.start_time
            return "failure"

        rc = self.proc.poll()
        if rc is not None:  # terminé
            self.returncode = rc
            self.stdout, self.stderr = self.proc.communicate()
            self.duration = time.time() - self.start_time

            if rc == 0:
                return "success"
            else:
                if self.attempts <= self.retries:
                    time.sleep(self.retry_delay)
                    return "retry"
                return "failure"

        return None  # toujours en cours

    def get_status(self):
        """Retourne le statut de la tâche : success, failure, ou success_with_warnings."""
        if self.returncode == None:
            return "Non"        
        elif self.returncode != 0:
            return "failure"

        if self.stderr and ("warning" in self.stderr.lower() or "error" in self.stderr.lower()):
            if WARNINGS_AS_FAILURE.lower() == "true":
                return "failure"
            return "success_with_warnings"

        return "success"

    def is_success(self):
        """Retourne True si le job est OK."""
        return self.returncode == 0

    def __repr__(self):
        return f"<Task {self.script.name} status={'?'}>"
