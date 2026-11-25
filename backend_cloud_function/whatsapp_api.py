"""Fonctions d'envoi de messages via l'API WhatsApp Cloud de Meta."""

import logging
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BACKEND_DIR.parent / "credentials" / ".env"
_DEFAULT_API_VERSION = "v19.0"
_REQUEST_TIMEOUT_SECONDS = 30

load_dotenv(_ENV_PATH)

logger = logging.getLogger(__name__)


def _get_api_configuration() -> tuple[str, str]:
    """Construit l'URL de l'API et retourne celle-ci avec le jeton."""
    token = os.getenv("WHATSAPP_API_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", _DEFAULT_API_VERSION).strip()

    if not token or "A_REMPLIR" in token:
        raise ValueError("WHATSAPP_API_TOKEN doit être renseigné dans credentials/.env.")
    if not phone_number_id or "A_REMPLIR" in phone_number_id:
        raise ValueError(
            "WHATSAPP_PHONE_NUMBER_ID doit être renseigné dans credentials/.env."
        )
    if not api_version:
        api_version = _DEFAULT_API_VERSION

    endpoint = (
        f"https://graph.facebook.com/{api_version}/"
        f"{phone_number_id}/messages"
    )
    return token, endpoint


def format_phone_number(telephone: str) -> str:
    """Supprime les séparateurs et retourne un numéro international composé de chiffres."""
    numero = re.sub(r"[\s()+-]", "", telephone)
    if not numero.isdigit():
        raise ValueError(
            "Le numéro doit contenir uniquement des chiffres, "
            "avec l'indicatif international."
        )
    return numero


def _send_payload(telephone: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Envoie un payload WhatsApp et transforme les erreurs en résultat explicite."""
    try:
        token, endpoint = _get_api_configuration()
        numero = format_phone_number(telephone)
    except ValueError as exc:
        logger.error("%s", exc)
        return {"success": False, "response": {"error": str(exc)}}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload["to"] = numero

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        error = f"Erreur réseau lors de l'appel à l'API WhatsApp : {exc}"
        logger.error("%s", error)
        return {"success": False, "response": {"error": error}}

    try:
        response_data: Any = response.json()
    except ValueError:
        response_data = response.text

    if not response.ok:
        meta_error = (
            response_data.get("error")
            if isinstance(response_data, dict)
            else None
        )
        if isinstance(meta_error, dict) and meta_error.get("message"):
            error_message = str(meta_error["message"])
        elif isinstance(response_data, str) and response_data:
            error_message = response_data
        else:
            error_message = (
                f"Échec de l'API WhatsApp (HTTP {response.status_code})."
            )
        logger.error("%s", error_message)
        return {"success": False, "response": response_data}

    return {"success": True, "response": response_data}


def send_text_message(telephone: str, message_text: str) -> dict[str, Any]:
    """Envoie un message texte à un numéro WhatsApp."""
    if not message_text:
        return {
            "success": False,
            "response": {"error": "Le texte du message ne peut pas être vide."},
        }

    payload = {
        "messaging_product": "whatsapp",
        "type": "text",
        "text": {"body": message_text},
    }
    return _send_payload(telephone, payload)


def send_template_message(
    telephone: str,
    template_name: str,
    language_code: str = "fr",
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Envoie un modèle WhatsApp approuvé par Meta."""
    if not template_name:
        return {
            "success": False,
            "response": {"error": "Le nom du modèle ne peut pas être vide."},
        }

    template: dict[str, Any] = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components is not None:
        template["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "type": "template",
        "template": template,
    }
    return _send_payload(telephone, payload)


if __name__ == "__main__":
    TEST_PHONE = "A_REMPLIR_NUMERO_TEST"
    configured_token = os.getenv("WHATSAPP_API_TOKEN", "").strip()

    if not configured_token or "A_REMPLIR" in configured_token:
        print(
            "Renseignez WHATSAPP_API_TOKEN dans credentials/.env "
            "avant de lancer le test."
        )
    elif not TEST_PHONE or "A_REMPLIR" in TEST_PHONE:
        print("Renseignez TEST_PHONE avec un numéro WhatsApp de test.")
    else:
        result = send_template_message(
            TEST_PHONE,
            template_name="hello_world",
            language_code="en_US",
        )
        print(result)
