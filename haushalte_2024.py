import pandas as pd
from pathlib import Path

FILE = Path("t01-2-03.xlsx")
SHEET = "2024"

# Excel einlesen
df = pd.read_excel(FILE, sheet_name=SHEET)

COL_VIERTEL = "Präsidialdepartement des Kantons Basel-Stadt"

# Alle relevanten Spalten: 1–6(+) Personen-Haushalte + Total
HH_COLS = {
    "Unnamed: 3": 1,  # 1-Personen-Haushalt
    "Unnamed: 4": 2,  # 2-Personen-Haushalt
    "Unnamed: 5": 3,  # 3-Personen-Haushalt
    "Unnamed: 6": 4,  # 4-Personen-Haushalt
    "Unnamed: 7": 5,  # 5-Personen-Haushalt
    "Unnamed: 8": 6,  # 6+ Personen-Haushalt (konservativ mit 6 gerechnet)
}

TOTAL_COL = "Unnamed: 10"

data = (
    df.loc[9:, [COL_VIERTEL] + list(HH_COLS.keys()) + [TOTAL_COL]]
      .dropna(subset=[COL_VIERTEL, TOTAL_COL])
      .assign(**{COL_VIERTEL: lambda d: d[COL_VIERTEL].str.strip()})
)

rename_cols = {COL_VIERTEL: "wohnviertel", TOTAL_COL: "hh_total"}
for col, size in HH_COLS.items():
    rename_cols[col] = f"hh_{size}_person"

data = data.rename(columns=rename_cols)

# Prozentanteil der Haushalte je Haushaltsgrösse (bezogen auf Haushalte)
for size in range(1, 7):
    col_hh = f"hh_{size}_person"
    data[f"hh_{size}_hh_prozent"] = data[col_hh] / data["hh_total"] * 100

# Personen pro Haushaltsgrösse (gewichtete Personenanzahl)
for size in range(1, 7):
    col_hh = f"hh_{size}_person"
    data[f"pers_{size}"] = size * data[col_hh]

# Roh-Total Personen (geschätzt, da 6+ nur als 6 gezählt wird)
pers_cols = [f"pers_{size}" for size in range(1, 7)]
data["pers_total_est"] = data[pers_cols].sum(axis=1)

# Echte Einwohnerzahlen pro Quartier (für 100 %)
POP_OVERRIDES = {
    "Matthäus": 15164,
    "Bruderholz": 9616,
}

def print_quarter(viertel_name: str):
    row = data.loc[data["wohnviertel"] == viertel_name]
    if row.empty:
        print(f"\n{viertel_name} nicht gefunden.")
        return

    row = row.iloc[0]

    # Roh-Schätzung aus Haushalten
    est_total = float(row["pers_total_est"])

    # Echte Einwohnerzahl → darauf skalieren
    real_total = POP_OVERRIDES.get(viertel_name, est_total)
    scale_factor = real_total / est_total if est_total > 0 else 1.0

    print(f"\n=== {viertel_name} 2024 ===")

    print("\nHaushalte nach Haushaltsgrösse (Anzahl & % der Haushalte):")
    for size in range(1, 7):
        hh_count = int(row[f"hh_{size}_person"])
        hh_pct = row[f"hh_{size}_hh_prozent"]
        label = f"{size} Personen" if size < 6 else "6+ Personen"
        print(f"  {label}: {hh_count:5d} Haushalte ({hh_pct:5.1f} %)")

    print(f"\nTotal Haushalte: {int(row['hh_total'])}")

    print("\nPersonen nach Haushaltsgrösse (skaliert auf echte Einwohnerzahl):")
    for size in range(1, 7):
        pers_raw = float(row[f"pers_{size}"])
        pers_scaled = pers_raw * scale_factor
        pers_pct = pers_scaled / real_total * 100 if real_total > 0 else 0
        label = f"{size} Personen" if size < 6 else "6+ Personen"
        print(
            f"  Personen in {label}-Haushalten: "
            f"{int(round(pers_scaled)):6d} ({pers_pct:5.1f} %)"
        )

    print(f"\nRoh geschätztes Total Personen: {int(round(est_total))}")
    print(f"Verwendetes Total Personen (für 100 %): {int(round(real_total))}")


# Nur diese zwei Quartiere ausgeben
print_quarter("Matthäus")
print_quarter("Bruderholz")
