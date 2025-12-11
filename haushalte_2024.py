import pandas as pd
from pathlib import Path


FILE = Path("t01-2-03.xlsx")
SHEET = "2024"

# Excel einlesen
df = pd.read_excel(FILE, sheet_name=SHEET)

COL_VIERTEL = "Präsidialdepartement des Kantons Basel-Stadt"

data = (
    df.loc[9:, [COL_VIERTEL, "Unnamed: 3", "Unnamed: 10"]]
      .dropna(subset=[COL_VIERTEL, "Unnamed: 3", "Unnamed: 10"])
      .assign(**{COL_VIERTEL: lambda d: d[COL_VIERTEL].str.strip()})
)

data = data.rename(columns={
    COL_VIERTEL: "wohnviertel",
    "Unnamed: 3": "hh_1_person",
    "Unnamed: 10": "hh_total",
})

# Prozentanteil 1-Personen-Haushalte berechnen
data["anteil_1p_prozent"] = data["hh_1_person"] / data["hh_total"] * 100

# Speziell: Matthäus
matth = data.loc[data["wohnviertel"] == "Matthäus"]
print("\nMatthäus 2024:")
print(matth[["wohnviertel", "hh_1_person", "hh_total", "anteil_1p_prozent"]])

brud = data.loc[data["wohnviertel"] == "Bruderholz"]
print("\nBruderholz 2024:")
print(brud[["wohnviertel", "hh_1_person", "hh_total", "anteil_1p_prozent"]])
