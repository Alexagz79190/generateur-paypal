import streamlit as st
import pandas as pd
from io import BytesIO

# Page de connexion
def login_page():
    st.title("Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if username == "paypal.aprolia" and password == "2025#Aprolia79!":  # Remplacez par vos identifiants réels
            st.session_state["authenticated"] = True
            st.query_params(authenticated="true")  # Définir un paramètre pour éviter double clic
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect")

# Vérification de l'authentification
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = st.query_params().get("authenticated") == ["true"]

if not st.session_state["authenticated"]:
    login_page()
else:
    # Titre de l'application
    st.title("Générateur d'écritures PayPal")

    # Fonction pour réinitialiser l'application
    def reset_app():
        st.session_state.clear()
        st.experimental_set_query_params()  # Supprimer les paramètres d'URL


    # Initialiser les fichiers générés dans session_state
    if "output_csv" not in st.session_state:
        st.session_state["output_csv"] = None
    if "inconnues_csv" not in st.session_state:
        st.session_state["inconnues_csv"] = None

    # Chargement des fichiers
    st.header("Chargement des fichiers")
    paypal_file = st.file_uploader("Importer le fichier PayPal (CSV)", type=["csv"])
    export_file = st.file_uploader("Importer le fichier Export (XLSX)", type=["xlsx"])

    generate_button = st.button("Générer les fichiers")

    if generate_button and paypal_file and export_file:
        # Lire les données
        paypal_data = pd.read_csv(paypal_file, sep=",", dtype=str)
        export_data = pd.read_excel(export_file, dtype=str, skiprows=1)  # Ignorer la première ligne

        # Convertir les montants avec des virgules en points
        paypal_data['Avant commission'] = paypal_data['Avant commission'].str.replace(",", ".").astype(float)
        paypal_data['Commission'] = paypal_data['Commission'].str.replace(",", ".").astype(float)
        paypal_data['Net'] = paypal_data['Net'].str.replace(",", ".").astype(float)

        # Initialiser les listes pour construire les lignes
        lines = []
        inconnues = []

        # Mapper les colonnes nécessaires entre les deux fichiers
        for index, row in paypal_data.iterrows():
            type_lig = ""
            journal = "53"
            date = row['Date']  # Colonne Date fichier Paypal
            piece = ""
            ligne = str(index + 1)  # N° ligne (indentation)
            type_cpt = "C"
            # Trouver le compte dans le fichier export
            reference_facture = row['Numéro de facture']
            compte_row = export_data[export_data['N° commande'] == reference_facture]
            if not compte_row.empty and compte_row['N° client'].values[0] and compte_row['N° client'].values[0] != "0":
                compte = compte_row['N° client'].values[0]
            else:
                compte = "1"
                inconnues.append(row)
            reference = reference_facture  # Numéro de facture fichier Paypal
            libelle = f"Règlement {row['Nom'].upper()}"  # Concaténation avec Nom en majuscules
            montant = f"{row['Avant commission']:.2f}".replace(".", ",")  # Format en virgule
            sens = "C"
            d_eche = ""
            paiement = ""
            tva = ""
            devise = ""
            post_analytique = ""

            # Ajouter la ligne principale
            lines.append([
                type_lig, journal, date, piece, ligne, type_cpt, compte, reference, libelle,
                montant, sens, d_eche, paiement, tva, devise, post_analytique
            ])

        # Ajouter la ligne "frais"
        commission_sum = paypal_data['Commission'].sum() * -1  # Passer en positif et formater
        lines.append([
            "", "53", date, "", str(len(lines) + 1), "G", "627831", date, "Règlement PAYPAL",
            f"{commission_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
        ])

        # Ajouter la ligne "total"
        net_sum = paypal_data['Net'].sum()  # Formater
        lines.append([
            "", "53", date, "", str(len(lines) + 1), "G", "512102", date, "Règlement PAYPAL",
            f"{net_sum:.2f}".replace(".", ","), "D", "", "", "", "", ""
        ])

        # Créer un DataFrame final
        columns = [
            "Type Lig", "Journal", "Date", "Pièce", "Ligne", "Type Cpt", "Compte", "Référence",
            "Libellé", "Montant", "Sens", "D.Eché", "Paiement", "TVA", "Devise", "Post analytique"
        ]
        output_df = pd.DataFrame(lines, columns=columns)
        output_csv = BytesIO()
        output_df.to_csv(output_csv, sep=";", index=False, encoding="utf-8-sig")
        output_csv.seek(0)

        # Gérer les commandes inconnues
        inconnues_csv = BytesIO()
        if inconnues:
            inconnues_df = pd.DataFrame(inconnues)
            inconnues_df.to_csv(inconnues_csv, sep=";", index=False, encoding="utf-8-sig")
        else:
            inconnues_csv.write(b"Aucune commande inconnue")
        inconnues_csv.seek(0)

        # Stocker les fichiers dans session_state
        st.session_state["output_csv"] = output_csv
        st.session_state["inconnues_csv"] = inconnues_csv

    # Afficher les boutons de téléchargement uniquement si les fichiers sont disponibles
    if st.session_state["output_csv"] and st.session_state["inconnues_csv"]:
        st.header("Téléchargement des fichiers")
        st.download_button(
            label="Télécharger le fichier des écritures",
            data=st.session_state["output_csv"],
            file_name="ECRITURES.csv",
            mime="text/csv"
        )
        st.download_button(
            label="Télécharger les commandes inconnues",
            data=st.session_state["inconnues_csv"],
            file_name="commandes_inconnues.csv",
            mime="text/csv"
        )
