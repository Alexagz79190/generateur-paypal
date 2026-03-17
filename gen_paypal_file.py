import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta

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

    for key in list(st.session_state.keys()):
        if key.startswith("file_uploader") and not isinstance(st.session_state.get(key), BytesIO):
            del st.session_state[key]

    paypal_file = st.file_uploader("Importer le fichier PayPal (CSV)")
    export_file = st.file_uploader("Importer le fichier Export (CSV)")

    if paypal_file and not paypal_file.name.lower().endswith(".csv"):
        st.error("Le fichier PayPal doit avoir l'extension .csv.")
        paypal_file = None

    if export_file and not export_file.name.lower().endswith(".csv"):
        st.error("Le fichier Export doit être au format CSV (.csv).")
        export_file = None

    # --------------------------------------------------
    # Filtres modifiables — affichés dès que l'Export est chargé
    # --------------------------------------------------
    date_filtre = (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    paiement_filtre = "Paypal adyen"

    if export_file:
        st.divider()
        st.subheader("🔧 Filtres de sélection")

        # Lecture rapide pour extraire les valeurs disponibles
        try:
            export_preview = pd.read_csv(export_file, sep=",", dtype=str)
            export_preview.columns = export_preview.columns.str.strip()
            export_file.seek(0)  # rembobiner pour la lecture définitive plus tard

            dates_dispo = sorted(
                export_preview["Date de validation"].dropna().unique().tolist(),
                reverse=True
            )
            paiements_dispos = sorted(
                export_preview["Paiement"].dropna().unique().tolist()
            )
        except Exception:
            dates_dispo = []
            paiements_dispos = []

        hier_str = (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📅 Date de validation**")
            if dates_dispo:
                default_date_idx = dates_dispo.index(hier_str) if hier_str in dates_dispo else 0
                date_selectionnee = st.selectbox(
                    "Choisir parmi les dates du fichier",
                    options=dates_dispo,
                    index=default_date_idx,
                    key="date_select"
                )
            else:
                date_selectionnee = hier_str
                st.info(f"Date par défaut : {hier_str}")

            date_manuelle = st.text_input(
                "✏️ Ou saisir manuellement (JJ/MM/AAAA)",
                value="",
                placeholder="ex : 15/03/2026 — laissez vide pour utiliser la sélection",
                key="date_manuelle"
            )
            date_filtre = date_manuelle.strip() if date_manuelle.strip() else date_selectionnee
            st.caption(f"✅ Date retenue : **{date_filtre}**")

        with col2:
            st.markdown("**💳 Mode de paiement**")
            if paiements_dispos:
                default_pay_idx = next(
                    (i for i, p in enumerate(paiements_dispos) if "paypal adyen" in p.lower()),
                    0
                )
                paiement_selectionne = st.selectbox(
                    "Choisir parmi les modes du fichier",
                    options=paiements_dispos,
                    index=default_pay_idx,
                    key="paiement_select"
                )
            else:
                paiement_selectionne = "Paypal adyen"
                st.info("Mode par défaut : Paypal adyen")

            paiement_manuel = st.text_input(
                "✏️ Ou saisir manuellement",
                value="",
                placeholder="ex : Paypal adyen — laissez vide pour utiliser la sélection",
                key="paiement_manuel"
            )
            paiement_filtre = paiement_manuel.strip() if paiement_manuel.strip() else paiement_selectionne
            st.caption(f"✅ Paiement retenu : **{paiement_filtre}**")

        st.divider()

    generate_button = st.button("Générer les fichiers", type="primary")

    # --------------------------------------------------
    # Génération
    # --------------------------------------------------
    if generate_button and paypal_file and export_file:

        paypal_data = pd.read_csv(paypal_file, sep=",", dtype=str)
        paypal_data = paypal_data[paypal_data['Type'] == 'Paiement Express Checkout']

        if paypal_data.empty:
            st.error("Aucune transaction de type 'Paiement Express Checkout' trouvée.")
        else:
            export_data = pd.read_csv(export_file, sep=",", dtype=str)
            export_data.columns = export_data.columns.str.strip()

            # Filtre Date
            export_data["Date de validation"] = export_data["Date de validation"].astype(str).str.strip()
            export_filtered = export_data[export_data["Date de validation"] == date_filtre].copy()

            nb_total = len(export_data)
            nb_apres_date = len(export_filtered)

            if export_filtered.empty:
                st.warning(
                    f"⚠️ Aucune commande avec la date **{date_filtre}** "
                    f"trouvée ({nb_total} lignes au total)."
                )
            else:
                # Filtre Paiement
                export_filtered = export_filtered[
                    export_filtered["Paiement"].astype(str).str.contains(
                        paiement_filtre, case=False, na=False
                    )
                ].copy()

                nb_apres_paypal = len(export_filtered)

                st.info(
                    f"📋 Export : {nb_total} lignes totales → "
                    f"{nb_apres_date} à la date du {date_filtre} → "
                    f"**{nb_apres_paypal} lignes « {paiement_filtre} »** retenues."
                )

                if export_filtered.empty:
                    st.warning(
                        f"⚠️ Aucune commande « {paiement_filtre} » trouvée pour le {date_filtre}."
                    )
                else:
                    # Nettoyage colonnes montants PayPal
                    columns_to_clean = ['Avant commission', 'Commission', 'Net']
                    for col in columns_to_clean:
                        paypal_data[col] = (
                            paypal_data[col].astype(str)
                            .str.replace("\xa0", "", regex=False)
                            .str.replace("\u202f", "", regex=False)
                            .str.replace(" ", "", regex=False)
                            .str.replace(",", ".", regex=False)
                        )
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
                        compte_row = export_filtered[
                            export_filtered['N° commande'].astype(str).str.strip() == reference_facture
                        ]
                        compte = (
                            compte_row['Code mistral'].values[0]
                            if not compte_row.empty
                            and compte_row['Code mistral'].values[0]
                            and compte_row['Code mistral'].values[0] not in ("0", "nan", "")
                            else "1"
                        )
                        if compte == "1":
                            inconnues.append(row)

                        reference = reference_facture
                        libelle = f"Règlement {row['Nom'].upper()}"
                        montant = f"{row['Avant commission']:.2f}".replace(".", ",")
                        sens = "C"

                        lines.append([
                            type_lig, journal, date, piece, ligne, type_cpt, compte, reference,
                            libelle, montant, sens, "", "", "", "", ""
                        ])

                    # Ligne commission
                    commission_sum = paypal_data['Commission'].sum() * -1
                    lines.append([
                        "", "53", date, "", str(len(lines) + 1), "G", "627831", date,
                        "Règlement PAYPAL", f"{commission_sum:.2f}".replace(".", ","), "D",
                        "", "", "", "", ""
                    ])

                    # Ligne Net
                    net_sum = paypal_data['Net'].sum()
                    lines.append([
                        "", "53", date, "", str(len(lines) + 1), "G", "512102", date,
                        "Règlement PAYPAL", f"{net_sum:.2f}".replace(".", ","), "D",
                        "", "", "", "", ""
                    ])

                    columns = [
                        "Type Lig", "Journal", "Date", "Pièce", "Ligne", "Type Cpt",
                        "Compte", "Référence", "Libellé", "Montant", "Sens",
                        "D.Eché", "Paiement", "TVA", "Devise", "Post analytique"
                    ]
                    output_df = pd.DataFrame(lines, columns=columns)
                    output_csv = BytesIO()
                    output_df.to_csv(
                        output_csv, sep=";", index=False, encoding="latin-1", errors="replace"
                    )
                    output_csv.seek(0)

                    inconnues_csv = BytesIO()
                    if inconnues:
                        pd.DataFrame(inconnues).to_csv(
                            inconnues_csv, sep=";", index=False, encoding="utf-8-sig"
                        )
                    else:
                        inconnues_csv.write(b"Aucune commande inconnue")
                    inconnues_csv.seek(0)

                    st.session_state["output_csv"] = output_csv
                    st.session_state["inconnues_csv"] = inconnues_csv

    elif generate_button and not (paypal_file and export_file):
        st.warning("⚠️ Veuillez charger les deux fichiers avant de générer.")

    # ------------------------------
    # Téléchargements
    # ------------------------------
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
