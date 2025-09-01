# utils/normalizer.py
from __future__ import annotations

from typing import Any, Literal, cast

from utils.logger import get_logger
from utils.types import (
    CleanupCfg,
    DaysField,
    HoursField,
    MinutesField,
    NotificationsCfg,
    TaskWithSource,
    WeekdaySpec,
)

LOGGER = get_logger(__name__)


def _as_bool(value: Any, default: bool) -> bool:
    """
    Convertit des valeurs YAML/booléennes/humaines en bool.

    Accepte: bool, "yes"/"no"/"true"/"false" (insensible à la casse), sinon default.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"yes", "true", "1"}:
            return True
        if v in {"no", "false", "0"}:
            return False
    return default


_warned_day_spec_once = False


def _coerce_int_list(value: Any) -> list[int] | None:
    """
    Convertit une valeur YAML en liste d'entiers, ou None si non applicable.

    Accepte:
      - [1, 2, 3]
      - ["01", "20"]  -> [1, 20]
      - 12            -> [12]
      - None          -> None
    Refuse:
      - autre chose -> log + None
    """
    if value is None:
        return None
    # Ne pas warn pour les sentinelles attendues par le schéma
    if isinstance(value, str) and value.strip().lower() == "any":
        return None
    # Back-compat: si on nous passe un dict {"day": [...]}, convertir silencieusement ici
    if isinstance(value, dict) and "day" in value:
        lst = _coerce_int_list(value.get("day"))
        return lst
    if isinstance(value, list):
        out: list[int] = []
        for item in value:
            if isinstance(item, int):
                out.append(item)
            elif isinstance(item, str) and item.isdigit():
                out.append(int(item))
            else:
                LOGGER.warning("Valeur non entière dans liste: %r (ignorée)", item)
        return out
    if isinstance(value, int):
        return [value]
    if isinstance(value, str) and value.isdigit():
        return [int(value)]
    LOGGER.warning("Impossible de convertir en liste d'entiers: %r", value)
    return None


def _normalize_hours(value: Any) -> HoursField:
    """
    hours: "any" | [int]
    Valeurs non conformes -> "any"
    """
    if isinstance(value, str) and value.strip().lower() == "any":
        return "any"
    lst = _coerce_int_list(value)
    return lst if lst is not None and len(lst) > 0 else "any"


def _normalize_minutes(value: Any) -> MinutesField:
    """
    minutes: [int]
    Valeurs non conformes -> []
    """
    lst = _coerce_int_list(value)
    return lst or []


def _normalize_days(value: Any) -> DaysField:
    """
    days: "any" | [int] | {"weekday": [int]}
    """
    if isinstance(value, dict):
        if "weekday" in value:
            wd = _coerce_int_list(value.get("weekday"))
            if wd:
                spec: WeekdaySpec = {"weekday": wd}
                return spec
            LOGGER.warning("days.weekday invalide: %r -> 'any'", value)
            return "any"
        if "day" in value:
            # Back-compat: {'day': [...]} → liste de jours du mois
            global _warned_day_spec_once
            if not _warned_day_spec_once:
                LOGGER.info(
                    "Schéma legacy détecté: days: {day: [...]} → supporté mais déprécié. "
                    "Préférez days: [..] (jours du mois) ou {weekday: [...]}."
                )
                _warned_day_spec_once = True
            dm = _coerce_int_list(value.get("day"))
            return dm if dm else "any"
    lst = _coerce_int_list(value)
    return lst if lst else "any"


def _normalize_cleanup(value: Any) -> CleanupCfg | None:
    """
    cleanup:
      paths: [str]
      rule:
        keep_days: int
        extensions: [str]
        recursive: bool
    Valeurs invalides -> None ou champs ignorés.
    """
    if not isinstance(value, dict):
        return None

    paths_val = value.get("paths")
    paths: list[str] = []
    if isinstance(paths_val, list):
        for p in paths_val:
            if isinstance(p, str) and p.strip():
                paths.append(p.strip())
    rule_val = value.get("rule")
    rule: dict[str, Any] = {}
    if isinstance(rule_val, dict):
        if isinstance(rule_val.get("keep_days"), int):
            rule["keep_days"] = rule_val["keep_days"]
        ext_val = rule_val.get("extensions")
        if isinstance(ext_val, list):
            rule["extensions"] = [e for e in ext_val if isinstance(e, str)]
        rule["recursive"] = _as_bool(rule_val.get("recursive"), False)

    cleanup: CleanupCfg = {}
    if paths:
        cleanup["paths"] = paths
    if rule:
        cleanup["rule"] = cast(Any, rule)  # champs validés ci-dessus
    return cleanup or None


def _normalize_notifications(value: Any) -> NotificationsCfg:
    """
    notifications:
      notify_on: ["failure", "success", "success_with_warnings", "retry"]
      channels: [str]
    Valeurs invalides -> valeurs par défaut raisonnables.
    """
    allowed = {"failure", "success", "success_with_warnings", "retry"}
    out: NotificationsCfg = {}
    if isinstance(value, dict):
        raw_no = value.get("notify_on")
        if isinstance(raw_no, list):
            filtered = [v for v in raw_no if isinstance(v, str) and v in allowed]
            out["notify_on"] = cast(list[Literal["failure", "success", "success_with_warnings", "retry"]], filtered)
        raw_ch = value.get("channels")
        if isinstance(raw_ch, list):
            out["channels"] = [v for v in raw_ch if isinstance(v, str) and v.strip()]
    if "notify_on" not in out:
        out["notify_on"] = ["failure"]
    if "channels" not in out:
        out["channels"] = ["discord"]
    return out


def normalize_task_dict(raw: dict[str, Any], source_file: str) -> TaskWithSource | None:
    """
    Valide et normalise un dict YAML en TaskWithSource typé.

    - Vérifie les champs obligatoires: type, script
    - Normalise: hours, minutes, days, enabled, exclusive, cleanup, notifications
    - Injecte: source_file
    - Retourne None si la tâche est invalide (avec logs explicites)

    :param raw: Dictionnaire brut issu de yaml.safe_load (une entrée de liste).
    :param source_file: Nom de base du fichier YAML (sans extension).
    :return: TaskWithSource prêt à l'emploi, ou None si invalide.
    """
    if not isinstance(raw, dict):
        LOGGER.warning("Entrée YAML ignorée (non-dict): %r", type(raw).__name__)
        return None

    ttype = raw.get("type", "python")
    if ttype not in ("python", "bash"):
        LOGGER.warning("type invalide %r -> 'python'", ttype)
        ttype = "python"

    script = raw.get("script")
    if not isinstance(script, str) or not script.strip():
        LOGGER.error("Tâche ignorée: script manquant/invalide: %r", script)
        return None

    task: TaskWithSource = {
        "type": ttype,  # Literal validé
        "script": script.strip(),
        "source_file": source_file,
    }

    # Champs simples
    if isinstance(raw.get("args"), str):
        task["args"] = raw["args"]
    task["enabled"] = _as_bool(raw.get("enabled"), True)
    task["exclusive"] = _as_bool(raw.get("exclusive"), True)

    if isinstance(raw.get("interpreter"), str) and raw["interpreter"].strip():
        task["interpreter"] = raw["interpreter"].strip()

    # Retry/timeout
    if isinstance(raw.get("retries"), int):
        task["retries"] = raw["retries"]
    if isinstance(raw.get("retry_delay"), int):
        task["retry_delay"] = raw["retry_delay"]
    if isinstance(raw.get("timeout"), int):
        task["timeout"] = raw["timeout"]
    if isinstance(raw.get("timeout_mode"), str) and raw["timeout_mode"] in {"strict", "soft"}:
        task["timeout_mode"] = raw["timeout_mode"]

    # Schedule
    task["hours"] = _normalize_hours(raw.get("hours"))
    task["minutes"] = _normalize_minutes(raw.get("minutes"))
    task["days"] = _normalize_days(raw.get("days"))

    # Cleanup / notifications
    cleanup = _normalize_cleanup(raw.get("cleanup"))
    if cleanup is not None:
        task["cleanup"] = cleanup
    task["notifications"] = _normalize_notifications(raw.get("notifications"))

    return task
