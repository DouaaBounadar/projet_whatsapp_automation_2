"""Connexion et opérations de base sur Google Sheets."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread.worksheet import Worksheet

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _BACKEND_DIR.parent
_ENV_PATH = _PROJECT_DIR / "credentials" / ".env"
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

load_dotenv(_ENV_PATH)


def _get_configuration() -> tuple[str, Path]:
    """Retourne l'identifiant du document et le chemin des identifiants Google."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

    if not sheet_id or sheet_id.startswith("A_REMPLIR"):
        raise RuntimeError(
            f"GOOGLE_SHEET_ID est absent ou non configuré dans {_ENV_PATH}."
        )
    if not credentials_path:
        raise RuntimeError(
            f"GOOGLE_CREDENTIALS_PATH est absent de {_ENV_PATH}."
        )

    path = Path(credentials_path).expanduser()
    if not path.is_absolute():
        # Le chemin fourni est relatif au dossier du backend, pas au terminal.
        path = _BACKEND_DIR / path
    return sheet_id, path.resolve()


def get_worksheet(sheet_name: str | None = None) -> Worksheet:
    """Authentifie le compte de service et retourne la feuille demandée."""
    sheet_id, credentials_path = _get_configuration()

    try:
        credentials = Credentials.from_service_account_file(
            str(credentials_path), scopes=_SCOPES
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Fichier d'identifiants Google introuvable : {credentials_path}. "
            "Vérifiez GOOGLE_CREDENTIALS_PATH."
        ) from exc
    except (GoogleAuthError, ValueError) as exc:
        raise RuntimeError(
            f"Fichier d'identifiants Google invalide : {credentials_path}."
        ) from exc

    client = gspread.authorize(credentials)
    try:
        spreadsheet = client.open_by_key(sheet_id)
        if sheet_name is None:
            return spreadsheet.sheet1
        return spreadsheet.worksheet(sheet_name)
    except SpreadsheetNotFound as exc:
        raise RuntimeError(
            "Google Sheet introuvable ou inaccessible. Vérifiez "
            "GOOGLE_SHEET_ID et partagez le document avec le compte de service."
        ) from exc
    except WorksheetNotFound as exc:
        raise RuntimeError(
            f"La feuille Google Sheets {sheet_name!r} est introuvable."
        ) from exc
    except APIError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code == 403:
            message = (
                "Accès refusé par Google Sheets. Vérifiez que le document est "
                "partagé avec l'adresse e-mail du compte de service."
            )
        else:
            message = f"Erreur de l'API Google Sheets (HTTP {status_code})."
        raise RuntimeError(message) from exc


def get_all_clients() -> list[dict[str, Any]]:
    """Récupère les clients et ajoute leur numéro de ligne dans le classeur."""
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    return [
        {**record, "row_index": row_index}
        for row_index, record in enumerate(records, start=2)
    ]


def update_client(
    row_index: int,
    statut: str | None = None,
    niveau_relance: int | str | None = None,
    update_date: bool = True,
) -> None:
    """Met à jour les champs fournis sur une ligne client précise."""
    if row_index < 2:
        raise ValueError("row_index doit désigner une ligne de données (>= 2).")

    updates: dict[str, str | int] = {}
    if statut is not None:
        updates["Statut"] = statut
    if niveau_relance is not None:
        updates["Niveau_Relance"] = niveau_relance
    if update_date:
        updates["Date_Mise_A_Jour"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not updates:
        return

    worksheet = get_worksheet()
    headers = worksheet.row_values(1)
    column_by_name = {header: index for index, header in enumerate(headers, start=1)}
    missing_columns = updates.keys() - column_by_name.keys()
    if missing_columns:
        raise ValueError(
            "Colonnes obligatoires absentes des en-têtes : "
            + ", ".join(sorted(missing_columns))
        )

    for column_name, value in updates.items():
        worksheet.update_cell(row_index, column_by_name[column_name], value)


if __name__ == "__main__":
    expected_columns = {
        "Entreprise",
        "Telephone",
        "Nom_Client",
        "Statut",
        "Date_Mise_A_Jour",
        "Niveau_Relance",
    }

    worksheet = get_worksheet()
    headers = set(worksheet.row_values(1))
    missing_columns = expected_columns - headers
    if missing_columns:
        raise ValueError(
            "Colonnes manquantes dans Google Sheets : "
            + ", ".join(sorted(missing_columns))
        )

    clients = get_all_clients()
    print(f"Nombre de clients trouvés : {len(clients)}")
    print("Trois premiers clients :")
    for client in clients[:3]:
        print(client)

    # Exemple explicite, à décommenter uniquement pour effectuer une modification :
    # update_client(row_index=2, statut="Contacté", niveau_relance=1)
