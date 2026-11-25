# Automatisation WhatsApp, Google Sheets et Streamlit

Ce projet constitue la base d'une application d'automatisation reliant WhatsApp, Google Sheets et une interface Streamlit. Les intégrations Google Sheets et WhatsApp sont amorcées ; l'orchestration et l'interface restent à implémenter.

## Architecture

- **`backend_cloud_function/`** : backend destiné à Google Cloud Functions. `main.py` expose le point d'entrée HTTP ; `rules_engine.py` applique les règles de relance ; `messages_templates.py` centralise les textes ; `whatsapp_api.py` et `sheets_api.py` gèrent les intégrations avec Meta et Google Sheets.
- **`frontend_streamlit/`** : tableau de bord commercial Streamlit dans `app.py` ; `data_manager.py` centralise l'accès aux données et les métriques.
- **Google Sheets** : stockage et consultation des données partagées entre les composants.
- **`credentials/`** : modèles locaux pour les paramètres d'environnement et le compte de service Google. Ce dossier est ignoré par Git ; ne publiez jamais de vrais identifiants.

```text
projet_whatsapp_automation/
├── backend_cloud_function/
│   ├── main.py
│   ├── messages_templates.py
│   ├── rules_engine.py
│   ├── sheets_api.py
│   ├── whatsapp_api.py
│   └── requirements.txt
├── frontend_streamlit/
│   ├── app.py
│   ├── data_manager.py
│   └── requirements.txt
├── credentials/
│   ├── .env
│   └── google_service_account.json
├── .gitignore
└── README.md
```

## Prérequis

- Python 3.10 ou plus récent
- Un compte Google Cloud avec l'API Google Sheets activée et un compte de service
- Un projet WhatsApp Business Platform configuré dans Meta
- Un Google Sheet auquel le compte de service a accès

## Configuration des identifiants

1. Copiez les valeurs fournies par Meta dans `credentials/.env` : jeton d'API et identifiant du numéro de téléphone. Adaptez également `WHATSAPP_API_VERSION` si nécessaire.
2. Remplacez les champs `A_REMPLIR` de `credentials/google_service_account.json` par les valeurs du fichier JSON du compte de service Google. Conservez un JSON valide et gardez ce fichier privé.
3. Renseignez `GOOGLE_SHEET_ID` avec l'identifiant du document Google Sheets et vérifiez `GOOGLE_CREDENTIALS_PATH` depuis le répertoire du composant qui l'utilisera.
4. Partagez le Google Sheet avec l'adresse e-mail du compte de service, avec les permissions nécessaires.

Les fichiers et le dossier `credentials/` sont exclus du contrôle de version. Les valeurs d'exemple ne sont pas des identifiants valides et doivent être remplacées avant toute exécution.

## Installation locale

Depuis la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend_cloud_function\requirements.txt -r frontend_streamlit\requirements.txt
```

Cette installation prépare les dépendances des deux composants. Le backend et le tableau de bord peuvent être lancés avec les commandes ci-dessous.

## Tester la connexion Google Sheets

Après avoir remplacé les valeurs factices dans `credentials/.env` et renseigné le JSON du compte de service, partagez le document Sheets avec l'adresse e-mail de ce compte. Depuis la racine du projet, lancez :

```powershell
.\.venv\Scripts\python.exe .\backend_cloud_function\sheets_api.py
```

Le test vérifie les en-têtes attendus et affiche le nombre de clients ainsi que les trois premières lignes, sans modifier le document. Le chemin des identifiants est résolu relativement au dossier du backend, quel que soit le répertoire courant du terminal.

## Tester l'API WhatsApp

Renseignez `WHATSAPP_API_TOKEN` et `WHATSAPP_PHONE_NUMBER_ID` dans `credentials/.env`, puis remplacez `TEST_PHONE` dans `backend_cloud_function/whatsapp_api.py` par un numéro de test au format international. Depuis la racine du projet, lancez :

```powershell
.\.venv\Scripts\python.exe .\backend_cloud_function\whatsapp_api.py
```

Cette commande envoie le modèle de test `hello_world` en anglais au numéro configuré. Elle n'envoie rien tant que le jeton ou le numéro de test conserve sa valeur factice. Les fonctions d'envoi peuvent également être appelées directement depuis le backend.

## Lancer le tableau de bord Streamlit

Depuis la racine du projet, lancez :

```powershell
streamlit run frontend_streamlit/app.py
```

Le tableau de bord affiche les indicateurs, les alertes urgentes et la base filtrable. Une campagne promotionnelle n'est envoyée qu'après le clic sur le bouton correspondant et nécessite un modèle Meta validé ainsi qu'une configuration WhatsApp fonctionnelle.
