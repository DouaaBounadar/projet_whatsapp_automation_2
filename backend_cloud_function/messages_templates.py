"""Messages WhatsApp personnalisés utilisés par le moteur de règles."""

MESSAGES: dict[str, str] = {
    "contact_initial_1": (
        "{nom_client}, je me permets de revenir vers vous au sujet de votre "
        "demande auprès de {entreprise}. Souhaitez-vous en discuter ?"
    ),
    "contact_initial_2": (
        "{nom_client}, je reviens vers vous concernant votre demande auprès de "
        "{entreprise}. N'hésitez pas à me dire si vous souhaitez poursuivre."
    ),
    "contact_initial_3": (
        "{nom_client}, voici mon dernier message au sujet de votre demande "
        "auprès de {entreprise}. Je reste à votre disposition si besoin. "
        "Belle journée."
    ),
    "devis_envoye": (
        "{nom_client}, avez-vous pu consulter le devis transmis par "
        "{entreprise} ? Je reste à votre disposition pour répondre à vos "
        "questions."
    ),
    "devis_accepte": (
        "{nom_client}, merci pour votre confiance envers {entreprise}. "
        "Nous sommes ravis de vous accompagner."
    ),
    "devis_refuse": (
        "{nom_client}, nous avons bien pris note de votre décision concernant "
        "la proposition de {entreprise}. Si vous le souhaitez, pourriez-vous "
        "nous indiquer ce qui a motivé votre choix ? Merci."
    ),
}


def get_message(
    key: str, nom_client: str = "", entreprise: str = ""
) -> str:
    """Formate un message et remplace les informations absentes par des valeurs neutres."""
    try:
        template = MESSAGES[key]
    except KeyError as exc:
        raise KeyError(f"Clé de message inconnue : {key!r}.") from exc

    nom = nom_client.strip() or "Bonjour"
    nom_entreprise = entreprise.strip() or "votre entreprise"
    return template.format(nom_client=nom, entreprise=nom_entreprise)
