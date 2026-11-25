"""Accès aux données Google Sheets pour le tableau de bord Streamlit."""

import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

_PROJECT_DIR = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _PROJECT_DIR / "backend_cloud_function"
for _module_path in (_PROJECT_DIR, _BACKEND_DIR):
    if str(_module_path) not in sys.path:
        sys.path.insert(0, str(_module_path))

from backend_cloud_function.rules_engine import send_promo_campaign
from backend_cloud_function.sheets_api import get_all_clients

SHEET_COLUMNS = [
    "Entreprise",
    "Telephone",
    "Nom_Client",
    "Statut",
    "Date_Mise_A_Jour",
    "Niveau_Relance",
]

DASHBOARD_STATUSES = [
    "Devis_À_Valider",
    "À_Appeler",
    "Devis_Refusé",
    "Devis_Accepté",
    "Devis_Envoyé",
    "Contact_Initial",
]


def load_clients_df() -> pd.DataFrame:
    """Charge les clients dans un DataFrame avec un schéma stable, même vide."""
    clients = get_all_clients()
    df = pd.DataFrame.from_records(clients)
    if "row_index" not in df.columns:
        df["row_index"] = pd.Series(dtype="Int64")

    for column in SHEET_COLUMNS:
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")

    return df.reindex(columns=[*SHEET_COLUMNS, "row_index"])


def get_dashboard_metrics(df: pd.DataFrame) -> dict[str, int]:
    """Calcule les volumes par statut et le nombre de clients éligibles aux offres."""
    status_counts = {
        status: int(df["Statut"].eq(status).sum()) if "Statut" in df.columns else 0
        for status in DASHBOARD_STATUSES
    }
    return {
        "total_clients": len(df),
        "devis_a_valider": status_counts["Devis_À_Valider"],
        "clients_a_appeler": status_counts["À_Appeler"],
        "devis_refuses": status_counts["Devis_Refusé"],
        "devis_acceptes": status_counts["Devis_Accepté"],
        "devis_envoyes": status_counts["Devis_Envoyé"],
        "contacts_initiaux": status_counts["Contact_Initial"],
        "clients_eligibles_promo": (
            status_counts["Devis_Accepté"] + status_counts["Devis_Refusé"]
        ),
    }


def filter_by_statuses(
    df: pd.DataFrame, statuses: Sequence[str]
) -> pd.DataFrame:
    """Retourne une copie du DataFrame limitée aux statuts sélectionnés."""
    if "Statut" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df["Statut"].isin(statuses)].copy()


def trigger_promo_campaign(
    template_name: str, language_code: str = "fr"
) -> dict[str, int]:
    """Déclenche la campagne Meta ciblant les clients éligibles."""
    return send_promo_campaign(template_name, language_code)
