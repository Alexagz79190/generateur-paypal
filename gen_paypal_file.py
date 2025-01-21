import streamlit as st
import pandas as pd

# Titre de l'application
st.title("Générateur d'écritures PayPal")

# Chargement des fichiers au centre
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

    # Téléchargement du fichier d'écritures
    st.header("Téléchargement")
    st.download_button(
        label="Télécharger le fichier des écritures",
        data=output_df.to_csv(sep=";", index=False, encoding="utf-8-sig"),
        file_name="ECRITURES.csv",
        mime="text/csv"
    )

    # Gérer les commandes inconnues
    if inconnues:
        inconnues_df = pd.DataFrame(inconnues)
        st.download_button(
            label="Télécharger les commandes inconnues",
            data=inconnues_df.to_csv(sep=";", index=False, encoding="utf-8-sig"),
            file_name="commandes_inconnues.csv",
            mime="text/csv"
        )
