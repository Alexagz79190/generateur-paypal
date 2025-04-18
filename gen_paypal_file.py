import streamlit as st
import pandas as pd
from io import BytesIO

# 🔧 Remplacement intelligent des caractères problématiques
UNICODE_REPLACEMENTS = {
    '\u0116': 'E',   # Ė
    '\u20AC': 'EUR', # €
    '\u2019': "'",   # apostrophe courbe
    '\u201C': '"',   # guillemets ouvrants
    '\u201D': '"',   # guillemets fermants
}

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    for char, replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Nettoyage final (sécurité) : enlever tout caractère non latin-1 restant
    return text.encode("latin-1", errors="ignore").decode("latin-1")

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
    st.title("Générateur d'écritures PayPal")

    st.header("Chargement des fichiers")
    paypal_file = st.file_uploader("Importer le fichier PayPal (CSV)", type=["csv"])
    export_file = st.file_uploader("Importer le fichier Export (XLSX)", type=["xlsx"])

    generate_button = st.button("Générer les fichiers")

    if generate_button and paypal_file and export_file:
        # 🔁 Lecture + nettoyage des caractères spéciaux à l'import
        paypal_data = pd.read_csv(paypal_file, sep=",", dtype=str)
        paypal_data = paypal_data.applymap(normalize_text)
        paypal_data = paypal_data[paypal_data['Type'] == 'Paiement Express Checkout']

        if paypal_data.empty:
            st.error("Aucune transaction de type 'Paiement Express Checkout' trouvée dans le fichier PayPal.")
        else:
            export_data = pd.read_excel(export_file, dtype=str, skiprows=1)
            export_data = export_data.applymap(normalize_text)

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

            commission_sum = paypal_data['Commission'].sum() * -1
            lines.append([
                "", "53", date, "", str(len(lines) + 1), "G", "627831", date, "Règlement PAYPAL",
                f"{commission_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
            ])

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

            # 🔁 Nettoyage final (sécurité)
            output_df = output_df.applymap(normalize_text)

            output_csv = BytesIO()
            output_df.to_csv(output_csv, sep=";", index=False, encoding="latin-1")
            output_csv.seek(0)

            inconnues_csv = BytesIO()
            if inconnues:
                inconnues_df = pd.DataFrame(inconnues)
                inconnues_df = inconnues_df.applymap(normalize_text)
                inconnues_df.to_csv(inconnues_csv, sep=";", index=False, encoding="utf-8-sig")
            else:
                inconnues_csv.write(b"Aucune commande inconnue")
            inconnues_csv.seek(0)

            st.session_state["output_csv"] = output_csv
            st.session_state["inconnues_csv"] = inconnues_csv

# Téléchargement des fichiers
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
