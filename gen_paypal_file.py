import streamlit as st
import pandas as pd
from io import BytesIO

# ⛑ PATCH contre l'erreur StreamlitAPIException sur file_uploader
for key in list(st.session_state.keys()):
    if "file_uploader" in key:
        del st.session_state[key]


# ------------------------------
# Connexion
# ------------------------------
def login_callback():
    if st.session_state.username == "paypal.aprolia" and st.session_state.password == "2025#Aprolia79!":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False
        st.error("Nom d'utilisateur ou mot de passe incorrect")

def login_page():
    st.title("Connexion")
    st.text_input("Nom d'utilisateur", key="username")
    st.text_input("Mot de passe", type="password", key="password")
    st.button("Se connecter", on_click=login_callback)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
else:
    # ------------------------------
    # Interface principale
    # ------------------------------
    st.title("Générateur d'écritures PayPal")
    st.header("Chargement des fichiers")

    # Nettoyer les objets file_uploader invalides dans la session
    for key in list(st.session_state.keys()):
        if key.startswith("file_uploader") and not isinstance(st.session_state.get(key), BytesIO):
            del st.session_state[key]


    paypal_file = st.file_uploader("Importer le fichier PayPal (CSV)")
    export_file = st.file_uploader("Importer le fichier Export (XLSX)")
    generate_button = st.button("Générer les fichiers")

    if paypal_file and not paypal_file.name.lower().endswith(".csv"):
        st.error("Le fichier PayPal doit avoir l'extension .csv.")
        paypal_file = None

    if export_file and not export_file.name.lower().endswith(".xlsx"):
        st.error("Le fichier Export doit être un fichier Excel (.xlsx).")
        export_file = None


    if generate_button and paypal_file and export_file:
        # Vérification de l’extension CSV
        if not paypal_file.name.lower().endswith(".csv"):
            st.error("Le fichier PayPal doit être au format CSV.")
        else:
            paypal_data = pd.read_csv(paypal_file, sep=",", dtype=str)
            paypal_data = paypal_data[paypal_data['Type'] == 'Paiement Express Checkout']

            if paypal_data.empty:
                st.error("Aucune transaction de type 'Paiement Express Checkout' trouvée.")
            else:
                export_data = pd.read_excel(export_file, dtype=str, skiprows=1)
                columns_to_clean = ['Avant commission', 'Commission', 'Net']

                for col in columns_to_clean:
                    paypal_data[col] = paypal_data[col].astype(str)\
                        .str.replace("\xa0", "", regex=False)\
                        .str.replace(",", ".", regex=False)
                    paypal_data[col] = pd.to_numeric(paypal_data[col], errors='coerce').fillna(0)

                lines = []
                inconnues = []

                for index, row in paypal_data.iterrows():
                    type_lig, journal = "", "53"
                    date = row['Date']
                    piece, ligne, type_cpt = "", str(index + 1), "C"

                    # Référence facture
                    reference_facture = ""
                    if pd.notna(row['Numéro de client']) and row['Numéro de client'].strip():
                        titre_objet = row.get("Titre de l'objet", "")
                        if '--' in titre_objet:
                            reference_facture = titre_objet.split('--')[-1].strip()
                    else:
                        reference_facture = row['Numéro de facture']

                    # Recherche du compte Mistral
                    compte_row = export_data[
                        export_data['N° commande'].astype(str).str.strip() == reference_facture
                    ]
                    compte = (
                        compte_row['Code Mistral'].values[0]
                        if not compte_row.empty and compte_row['Code Mistral'].values[0] and compte_row['Code Mistral'].values[0] != "0"
                        else "1"
                    )
                    if compte == "1":
                        inconnues.append(row)

                    reference = reference_facture
                    libelle = f"Règlement {row['Nom'].upper()}"
                    montant = f"{row['Avant commission']:.2f}".replace(".", ",")
                    sens = "C"

                    # Ligne principale
                    lines.append([
                        type_lig, journal, date, piece, ligne, type_cpt, compte, reference,
                        libelle, montant, sens, "", "", "", "", ""
                    ])

                # Ligne commission
                commission_sum = paypal_data['Commission'].sum() * -1
                lines.append([
                    "", "53", date, "", str(len(lines) + 1), "G", "627831", date,
                    "Règlement PAYPAL", f"{commission_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
                ])

                # Ligne Net
                net_sum = paypal_data['Net'].sum()
                lines.append([
                    "", "53", date, "", str(len(lines) + 1), "G", "512102", date,
                    "Règlement PAYPAL", f"{net_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
                ])

                # Génération du fichier d'écriture
                columns = [
                    "Type Lig", "Journal", "Date", "Pièce", "Ligne", "Type Cpt", "Compte", "Référence",
                    "Libellé", "Montant", "Sens", "D.Eché", "Paiement", "TVA", "Devise", "Post analytique"
                ]
                output_df = pd.DataFrame(lines, columns=columns)
                output_csv = BytesIO()
                output_df.to_csv(output_csv, sep=";", index=False, encoding="latin-1")
                output_csv.seek(0)

                # Fichier des commandes inconnues
                inconnues_csv = BytesIO()
                if inconnues:
                    pd.DataFrame(inconnues).to_csv(inconnues_csv, sep=";", index=False, encoding="utf-8-sig")
                else:
                    inconnues_csv.write(b"Aucune commande inconnue")
                inconnues_csv.seek(0)

                st.session_state["output_csv"] = output_csv
                st.session_state["inconnues_csv"] = inconnues_csv

    # ------------------------------
    # Téléchargements
    # ------------------------------
    if "output_csv" in st.session_state and "inconnues_csv" in st.session_state:
        st.header("Téléchargement des fichiers")
        st.download_button("Télécharger le fichier des écritures", data=st.session_state["output_csv"],
                           file_name="ECRITURES.csv", mime="text/csv")
        st.download_button("Télécharger les commandes inconnues", data=st.session_state["inconnues_csv"],
                           file_name="commandes_inconnues.csv", mime="text/csv")
