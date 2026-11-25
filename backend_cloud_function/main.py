"""Point d'entrée HTTP de l'automatisation Google Cloud Function."""

import json
import logging

import functions_framework
from flask import Request, Response, jsonify

from rules_engine import process_all_clients

logger = logging.getLogger(__name__)


@functions_framework.http
def run_automation(request: Request) -> Response | tuple[Response, int]:
    """Exécute le traitement des clients et retourne ses statistiques en JSON."""
    try:
        stats = process_all_clients()
    except Exception as exc:
        logger.exception("Échec du traitement des clients.")
        return jsonify(
            {
                "analyses": 0,
                "envoyes": 0,
                "passages_a_appeler": 0,
                "erreurs": 1,
                "details_erreurs": [str(exc)],
            }
        ), 500

    return jsonify(stats), 200


if __name__ == "__main__":
    print(json.dumps(process_all_clients(), ensure_ascii=False, indent=2))
