import streamlit as st
import pandas as pd
from io import BytesIO

# 🔧 Fonction de nettoyage des chaînes incompatibles avec latin-1
def clean_latin1(s):
    """Supprime les caractères non compatibles avec latin-1 (ISO-8859-1)."""
    if isinstance(s, str):
        return s.encode("latin-1", errors="ignore").decode("latin-1")
    return s

# Fonction de callback pour la connexion
def login_callback():
    if st.session_state.username == "paypal.aprolia" and st.session_state.password == "2025#Aprolia79!":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False
        st.error("Nom d'utilisateur ou mot de passe incorrect")

# Page de connexion
def login_page():
    st.title("Connexion")
    st.text_input("Nom d'utilisateur", key="username")
    st.text_input("Mot de passe", type="password", key="password")
    st.button("Se connecter", on_click=login_callback)

# Vérification de l'authentification
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
else:
    # Titre de l'application
    st.title("Générateur d'écritures PayPal")

    # Chargement des fichiers
    st.header("Chargement des fichiers")
    paypal_file = st.file_uploader("Importer le fichier PayPal (CSV)", type=["csv"])
    export_file = st.file_uploader("Importer le fichier Export (XLSX)", type=["xlsx"])

    generate_button = st.button("Générer les fichiers")

    if generate_button and paypal_file and export_file:
        # Lire les données
        paypal_data = pd.read_csv(paypal_file, sep=",", dtype=str)

        # Filtrer uniquement les lignes où 'Type' est égal à 'Paiement Express Checkout'
        paypal_data = paypal_data[paypal_data['Type'] == 'Paiement Express Checkout']

        if paypal_data.empty:
            st.error("Aucune transaction de type 'Paiement Express Checkout' trouvée dans le fichier PayPal.")
        else:
            export_data = pd.read_excel(export_file, dtype=str, skiprows=1)  # Ignorer la première ligne

            # Colonnes à nettoyer
            columns_to_clean = ['Avant commission', 'Commission', 'Net']

            for col in columns_to_clean:
                paypal_data[col] = paypal_data[col].astype(str).str.replace("\xa0", "", regex=False)
                paypal_data[col] = paypal_data[col].str.replace(",", ".", regex=False)
                paypal_data[col] = pd.to_numeric(paypal_data[col], errors='coerce').fillna(0)

            lines = []
            inconnues = []

            for index, row in paypal_data.iterrows():
                type_lig = ""
                journal = "53"
                date = row['Date']
                piece = ""
                ligne = str(index + 1)
                type_cpt = "C"

                reference_facture = ""
                if pd.notna(row['Numéro de client']) and row['Numéro de client'].strip() != "":
                    titre_objet = row.get('Titre de l\'objet', '')
                    if '--' in titre_objet:
                        reference_facture = titre_objet.split('--')[-1].strip()
                else:
                    reference_facture = row['Numéro de facture']

                compte_row = export_data[export_data['N° commande'] == reference_facture]
                if not compte_row.empty and compte_row['Code Mistral'].values[0] and compte_row['Code Mistral'].values[0] != "0":
                    compte = compte_row['Code Mistral'].values[0]
                else:
                    compte = "1"
                    inconnues.append(row)

                reference = reference_facture
                libelle = f"Règlement {row['Nom'].upper()}"
                montant = f"{row['Avant commission']:.2f}".replace(".", ",")
                sens = "C"
                d_eche = ""
                paiement = ""
                tva = ""
                devise = ""
                post_analytique = ""

                lines.append([
                    type_lig, journal, date, piece, ligne, type_cpt, compte, reference, libelle,
                    montant, sens, d_eche, paiement, tva, devise, post_analytique
                ])

            # Ligne "frais"
            commission_sum = paypal_data['Commission'].sum() * -1
            lines.append([
                "", "53", date, "", str(len(lines) + 1), "G", "627831", date, "Règlement PAYPAL",
                f"{commission_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
            ])

            # Ligne "total"
            net_sum = paypal_data['Net'].sum()
            lines.append([
                "", "53", date, "", str(len(lines) + 1), "G", "512102", date, "Règlement PAYPAL",
                f"{net_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
            ])

            columns = [
                "Type Lig", "Journal", "Date", "Pièce", "Ligne", "Type Cpt", "Compte", "Référence",
                "Libellé", "Montant", "Sens", "D.Eché", "Paiement", "TVA", "Devise", "Post analytique"
            ]
            output_df = pd.DataFrame(lines, columns=columns)

            # 🔁 Forcer le DataFrame en chaîne de caractères
            output_df = output_df.astype(str)

            # 🔧 Nettoyer tous les caractères non latin-1
            output_df = output_df.applymap(clean_latin1)

            # 📝 Export vers CSV (latin-1 sécurisé)
            output_csv = BytesIO()
            try:
                output_df.to_csv(output_csv, sep=";", index=False, encoding="latin-1")
            except UnicodeEncodeError as e:
                st.error("❌ Une erreur d'encodage a été détectée malgré le nettoyage.")
                st.text(f"Détail : {e}")
                st.stop()
            output_csv.seek(0)

            # Commandes inconnues
            inconnues_csv = BytesIO()
            if inconnues:
                inconnues_df = pd.DataFrame(inconnues)
                inconnues_df.to_csv(inconnues_csv, sep=";", index=False, encoding="utf-8-sig")
            else:
                inconnues_csv.write(b"Aucune commande inconnue")
            inconnues_csv.seek(0)

            # Stockage dans session
            st.session_state["output_csv"] = output_csv
            st.session_state["inconnues_csv"] = inconnues_csv

# Téléchargement
if "output_csv" in st.session_state and "inconnues_csv" in st.session_state:
    st.header("Téléchargement des fichiers")
    st.download_button(
        "Télécharger le fichier des écritures",
        data=st.session_state["output_csv"],
        file_name="ECRITURES.csv",
        mime="text/csv"
    )
    st.download_button(
        "Télécharger les commandes inconnues",
        data=st.session_state["inconnues_csv"],
        file_name="commandes_inconnues.csv",
        mime="text/csv"
    )
