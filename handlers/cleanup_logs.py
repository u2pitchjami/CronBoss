from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import time

from utils.logger import get_logger
from utils.types import CleanupRule

logger = get_logger("Cron_Hub")


def cleanup_multiple(paths: Sequence[str | Path], rule: CleanupRule) -> None:
    """
    Supprime des fichiers dans un ou plusieurs dossiers selon des règles simples.

    Stratégies supportées (priorisées) :
      1) keep_last: garder les N fichiers les plus récents, supprimer le reste
      2) keep_days: supprimer les fichiers plus vieux que N jours

    Filtrage :
      - extensions: "all" (tous fichiers) ou liste d'extensions [".log", ".gz", ...]
      - recursive: True/False (utilise rglob ou glob)
      - dry_run: True/False (logge sans supprimer)

    :param paths: Dossiers à nettoyer.
    :param rule: Règles de nettoyage (voir utils.types.CleanupRule).
    """
    # --- Lecture/normalisation des options ---
    keep_last: int | None = rule.get("keep_last")
    keep_days: int | None = rule.get("keep_days")
    extensions = rule.get("extensions", [".log"])
    recursive: bool = bool(rule.get("recursive", False))
    dry_run: bool = bool(rule.get("dry_run", False))

    if keep_last is None and keep_days is None:
        logger.info("🧹 Aucune règle (keep_last/keep_days) fournie → aucune suppression effectuée.")
        return

    # Priorité : keep_last > keep_days
    strategy = "keep_last" if keep_last is not None else "keep_days"
    now = time.time()
    cutoff: float | None = None
    if strategy == "keep_days" and isinstance(keep_days, int) and keep_days >= 0:
        cutoff = now - (keep_days * 86400)

    for base in list(paths):
        base_path = Path(base)
        if not base_path.exists() or not base_path.is_dir():
            logger.warning("⚠️ Chemin ignoré (inexistant/non-dossier) : %s", base_path)
            continue

        # --- Collecte des fichiers cibles ---
        it = base_path.rglob("*") if recursive else base_path.glob("*")

        files: list[Path] = []
        if extensions == "all":
            files = [p for p in it if p.is_file()]
        else:
            # Normalise extensions (ajoute le "." si oublié)
            normalized_exts = []
            for ext in extensions:
                if not ext:
                    continue
                normalized_exts.append(ext if ext.startswith(".") else f".{ext}")
            files = [p for p in it if p.is_file() and any(p.name.endswith(ext) for ext in normalized_exts)]

        if not files:
            logger.info("📂 %s : aucun fichier à traiter (filtre=%s, recursive=%s)", base_path, extensions, recursive)
            continue

        # --- Application de la stratégie ---
        to_delete: list[Path] = []
        if strategy == "keep_last" and keep_last is not None:
            # Trie par date de modification (plus récents d'abord)
            files_sorted = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
            to_delete = files_sorted[keep_last:] if keep_last >= 0 else []
            logger.info(
                "📂 %s : stratégie keep_last=%s → suppression de %s fichiers", base_path, keep_last, len(to_delete)
            )

        elif strategy == "keep_days" and cutoff is not None:
            to_delete = [f for f in files if f.stat().st_mtime < cutoff]
            logger.info(
                "📂 %s : stratégie keep_days=%s → suppression de %s fichiers", base_path, keep_days, len(to_delete)
            )

        # --- Exécution / Dry-run ---
        for f in to_delete:
            try:
                if dry_run:
                    logger.info("🧪 [Dry run] Suppression prévue : %s", f)
                else:
                    logger.info("🧹 Suppression : %s", f)
                    f.unlink()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("❌ Erreur suppression %s : %s", f, exc)
