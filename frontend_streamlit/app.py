"""Tableau de bord commercial Streamlit."""

import pandas as pd
import streamlit as st

from data_manager import (
    filter_by_statuses,
    get_dashboard_metrics,
    load_clients_df,
    trigger_promo_campaign,
)

URGENT_STATUSES = {"À_Appeler", "Devis_À_Valider", "Devis_Refusé"}

st.set_page_config(
    page_title="Tableau de Bord Commercial",
    layout="wide",
)


@st.cache_data(ttl=300)
def _load_clients_df_cached() -> pd.DataFrame:
    return load_clients_df()


def _highlight_urgent_rows(row: pd.Series) -> list[str]:
    status = row.get("Statut")
    if isinstance(status, str) and status in URGENT_STATUSES:
        return ["background-color: #ffe2e2; color: #5c1111"] * len(row)
    return [""] * len(row)


title_column, refresh_column = st.columns([5, 1])
with title_column:
    st.title("Tableau de Bord Commercial")
    st.caption("Suivi des devis, des relances et des opportunités commerciales.")
with refresh_column:
    st.write("")
    if st.button("🔄 Actualiser les données", width="stretch"):
        st.cache_data.clear()
        st.rerun()

try:
    clients_df = _load_clients_df_cached()
except Exception as exc:
    st.error(f"Impossible de charger les clients depuis Google Sheets : {exc}")
    st.stop()

metrics = get_dashboard_metrics(clients_df)
kpi_columns = st.columns(4)
kpi_columns[0].metric("Total clients", metrics["total_clients"])
kpi_columns[1].metric("Devis à valider", metrics["devis_a_valider"])
kpi_columns[2].metric("Clients à appeler", metrics["clients_a_appeler"])
kpi_columns[3].metric(
    "Éligibles aux offres promo", metrics["clients_eligibles_promo"]
)

st.divider()
st.header("Alertes urgentes")

validation_clients = filter_by_statuses(clients_df, ["Devis_À_Valider"])
if not validation_clients.empty:
    st.error(f"⚠️ {len(validation_clients)} Devis à valider urgemment")
    st.dataframe(validation_clients, width="stretch", hide_index=True)

call_clients = filter_by_statuses(clients_df, ["À_Appeler"])
if not call_clients.empty:
    st.warning(f"📞 {len(call_clients)} Client(s) à appeler par téléphone")
    st.dataframe(call_clients, width="stretch", hide_index=True)

refused_clients = filter_by_statuses(clients_df, ["Devis_Refusé"])
if not refused_clients.empty:
    st.error(f"❌ {len(refused_clients)} Devis refusé(s) à traiter")
    st.dataframe(refused_clients, width="stretch", hide_index=True)

st.divider()
st.header("Campagne promotionnelle")
st.write(
    f"Clients ciblés : **{metrics['clients_eligibles_promo']}** "
    "(devis acceptés ou refusés)."
)

template_column, language_column = st.columns(2)
with template_column:
    template_name = st.text_input(
        "Nom du modèle Meta validé",
        value="nouvelles_offres",
    )
with language_column:
    language_code = st.text_input("Code langue", value="fr")

if st.button(
    "Envoyer les nouvelles offres",
    type="primary",
    disabled=metrics["clients_eligibles_promo"] == 0,
):
    try:
        campaign_result = trigger_promo_campaign(
            template_name.strip(),
            language_code.strip() or "fr",
        )
        st.success(
            f"Campagne terminée : {campaign_result.get('envoyés', 0)} message(s) "
            f"envoyé(s), {campaign_result.get('échecs', 0)} échec(s)."
        )
    except Exception as exc:
        st.error(f"Échec de la campagne promotionnelle : {exc}")

st.divider()
st.header("Base complète des clients")

filter_column, search_column = st.columns([2, 3])
with filter_column:
    available_statuses = sorted(
        clients_df["Statut"].dropna().astype(str).unique().tolist()
    )
    selected_statuses = st.multiselect(
        "Filtrer par statut",
        options=available_statuses,
        default=available_statuses,
    )
with search_column:
    search_text = st.text_input("Rechercher par entreprise ou nom du client")

filtered_clients = filter_by_statuses(clients_df, selected_statuses)
if search_text.strip():
    search_mask = pd.Series(False, index=filtered_clients.index)
    for column in ("Entreprise", "Nom_Client"):
        if column in filtered_clients.columns:
            search_mask |= filtered_clients[column].astype("string").str.contains(
                search_text.strip(),
                case=False,
                na=False,
                regex=False,
            )
    filtered_clients = filtered_clients.loc[search_mask]

st.caption(f"{len(filtered_clients)} client(s) affiché(s).")
st.dataframe(
    filtered_clients.style.apply(_highlight_urgent_rows, axis=1),
    width="stretch",
    hide_index=True,
)
