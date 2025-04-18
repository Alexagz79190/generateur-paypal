import pandas as pd
from io import BytesIO

# Exemple contenant un caractère interdit en latin-1
data = {'col1': ['Normal', 'Avec Ė'], 'col2': ['OK', 'Test €']}

df = pd.DataFrame(data)

# 🔧 Nettoyage solide ligne par ligne
def deep_clean_df(df):
    cleaned_data = []
    for row in df.itertuples(index=False):
        cleaned_row = []
        for val in row:
            val = "" if pd.isna(val) else str(val)
            try:
                val = val.encode("latin-1", errors="ignore").decode("latin-1")
            except Exception:
                val = ""
            cleaned_row.append(val)
        cleaned_data.append(cleaned_row)
    return pd.DataFrame(cleaned_data, columns=df.columns)

# 🔁 Nettoyage
cleaned_df = deep_clean_df(df)

# ✅ Export latin-1
output_csv = BytesIO()
cleaned_df.to_csv(output_csv, sep=";", index=False, encoding="latin-1")
output_csv.seek(0)

# ✅ Afficher le contenu exporté
print(output_csv.getvalue().decode("latin-1"))
