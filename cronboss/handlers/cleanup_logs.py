import time
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def cleanup_multiple(paths, rule):
    keep_days = rule.get("keep_days")
    keep_last = rule.get("keep_last")
    extensions = rule.get("extensions", [".log"])
    recursive = rule.get("recursive", False)
    dry_run = rule.get("dry_run", False)

    now = time.time()
    cutoff = now - (keep_days * 86400) if keep_days else None

    for log_path in paths:
        path = Path(log_path)
        files = path.rglob("*") if recursive else path.glob("*")
        if extensions == ['all']:
            files = [f for f in files if f.is_file()]
        else:
            files = [f for f in files if f.is_file() and any(f.name.endswith(ext) for ext in extensions)]

        if keep_last:
            files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
            to_delete = files[keep_last:]
        elif cutoff:
            to_delete = [f for f in files if f.stat().st_mtime < cutoff]
        else:
            to_delete = []

        for file in to_delete:
            try:
                if dry_run:
                    logger.info(f"🧪 [Dry run] Suppression prévue : {file}")
                else:
                    logger.info(f"🧹 Suppression : {file}")
                    file.unlink()
            except Exception as e:
                logger.warning(f"❌ Erreur suppression {file} : {e}")
