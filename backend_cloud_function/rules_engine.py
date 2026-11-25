"""Application des règles de relance et de suivi des devis."""

import logging
from datetime import datetime, timedelta
from typing import Any

from messages_templates import get_message
from sheets_api import get_all_clients, update_client
from whatsapp_api import send_template_message, send_text_message

logger = logging.getLogger(__name__)
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
)
_STATUTS_SANS_ACTION = {
    "Devis_En_Préparation",
    "Devis_À_Valider",
    "À_Appeler",
}


def _parse_level(value: Any) -> int:
    """Convertit le niveau de relance en entier et traite une cellule vide comme zéro."""
    if value is None or not str(value).strip():
        return 0

    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Niveau_Relance invalide : {value!r}.") from exc
    if not numeric_value.is_integer():
        raise ValueError(f"Niveau_Relance doit être un entier : {value!r}.")
    return int(numeric_value)


def _parse_updated_at(value: Any) -> datetime:
    """Lit une date de mise à jour parmi les formats acceptés du Google Sheet."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Date_Mise_A_Jour est vide.")

    date_text = value.strip()
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(date_text, date_format)
        except ValueError:
            continue

    raise ValueError(
        f"Date_Mise_A_Jour invalide : {value!r}; "
        f"formats attendus : {', '.join(_DATE_FORMATS)}."
    )


def _record_error(stats: dict[str, Any], row_index: Any, message: str) -> None:
    detail = f"Ligne {row_index}: {message}"
    stats["erreurs"] += 1
    stats["details_erreurs"].append(detail)
    logger.error("%s", detail)


def _send_and_update(
    client: dict[str, Any],
    message_key: str,
    next_level: int,
    stats: dict[str, Any],
) -> None:
    row_index = client["row_index"]
    message = get_message(
        message_key,
        nom_client=str(client.get("Nom_Client") or ""),
        entreprise=str(client.get("Entreprise") or ""),
    )

    try:
        result = send_text_message(str(client.get("Telephone") or ""), message)
    except Exception as exc:
        _record_error(stats, row_index, f"Erreur lors de l'envoi WhatsApp : {exc}")
        return

    if result.get("success") is not True:
        _record_error(
            stats,
            row_index,
            f"Échec de l'envoi WhatsApp : {result.get('response')!r}.",
        )
        return

    stats["envoyes"] += 1
    try:
        update_client(row_index, niveau_relance=next_level)
    except Exception as exc:
        _record_error(
            stats,
            row_index,
            f"Message envoyé, mais mise à jour du Google Sheet impossible : {exc}",
        )


def process_all_clients() -> dict[str, Any]:
    """Traite les clients selon leur statut, leur niveau et leur date de mise à jour."""
    stats: dict[str, Any] = {
        "analyses": 0,
        "envoyes": 0,
        "passages_a_appeler": 0,
        "erreurs": 0,
        "details_erreurs": [],
    }
    clients = get_all_clients()
    now = datetime.now()

    for client in clients:
        stats["analyses"] += 1
        row_index = client.get("row_index", "?")
        status = str(client.get("Statut") or "").strip()

        if status in _STATUTS_SANS_ACTION or not status:
            continue
        if status not in {
            "Contact_Initial",
            "Devis_Envoyé",
            "Devis_Accepté",
            "Devis_Refusé",
        }:
            continue

        try:
            level = _parse_level(client.get("Niveau_Relance"))
        except ValueError as exc:
            _record_error(stats, row_index, str(exc))
            continue

        if status in {"Devis_Accepté", "Devis_Refusé"}:
            if level == 0:
                message_key = (
                    "devis_accepte" if status == "Devis_Accepté" else "devis_refuse"
                )
                _send_and_update(client, message_key, 1, stats)
            continue

        if status == "Devis_Envoyé":
            if level != 0:
                continue
            message_key = "devis_envoye"
            next_level = 1
            threshold = timedelta(hours=24)
        else:
            contact_steps = {
                0: ("contact_initial_1", 1, timedelta(hours=2)),
                1: ("contact_initial_2", 2, timedelta(hours=24)),
                2: ("contact_initial_3", 3, timedelta(hours=48)),
                3: (None, None, timedelta(hours=48)),
            }
            if level not in contact_steps:
                _record_error(
                    stats, row_index, f"Niveau_Relance non pris en charge : {level}."
                )
                continue
            message_key, next_level, threshold = contact_steps[level]

        try:
            updated_at = _parse_updated_at(client.get("Date_Mise_A_Jour"))
        except ValueError as exc:
            _record_error(stats, row_index, str(exc))
            continue
        if now - updated_at < threshold:
            continue

        if status == "Contact_Initial" and level == 3:
            try:
                update_client(row_index, statut="À_Appeler")
                stats["passages_a_appeler"] += 1
            except Exception as exc:
                _record_error(
                    stats,
                    row_index,
                    f"Impossible de passer le client en À_Appeler : {exc}",
                )
            continue

        if message_key is not None and next_level is not None:
            _send_and_update(client, message_key, next_level, stats)

    return stats


def send_promo_campaign(
    template_name: str, language_code: str = "fr"
) -> dict[str, int]:
    """Envoie un modèle promotionnel aux clients ayant accepté ou refusé un devis."""
    summary = {"envoyés": 0, "échecs": 0}
    clients = get_all_clients()

    for client in clients:
        if str(client.get("Statut") or "").strip() not in {
            "Devis_Accepté",
            "Devis_Refusé",
        }:
            continue
        try:
            result = send_template_message(
                str(client.get("Telephone") or ""),
                template_name,
                language_code=language_code,
            )
        except Exception as exc:
            summary["échecs"] += 1
            logger.error(
                "Échec de la campagne pour la ligne %s : %s",
                client.get("row_index", "?"),
                exc,
            )
            continue

        if result.get("success") is True:
            summary["envoyés"] += 1
        else:
            summary["échecs"] += 1
            logger.error(
                "Échec de la campagne pour la ligne %s : %r",
                client.get("row_index", "?"),
                result.get("response"),
            )

    return summary
