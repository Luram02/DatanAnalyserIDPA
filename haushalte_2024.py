import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

FILE = Path("t01-2-03.xlsx")
SHEET = "2024"

# Ordner für die Diagramme
OUTPUT_DIR = Path("output_diagrams")
OUTPUT_DIR.mkdir(exist_ok=True)

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

def safe_name(name: str) -> str:
    # Für Dateinamen: Umlaute & Leerzeichen etwas entschärfen
    return (
        name.replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("Ä", "Ae")
            .replace("Ö", "Oe")
            .replace("Ü", "Ue")
            .replace("ß", "ss")
            .replace(" ", "_")
    )

def safe_name(name: str) -> str:
    # Für Dateinamen: Umlaute & Leerzeichen etwas entschärfen
    return (
        name.replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("Ä", "Ae")
            .replace("Ö", "Oe")
            .replace("Ü", "Ue")
            .replace("ß", "ss")
            .replace(" ", "_")
    )

def _label(size: int) -> str:
    if size == 1:
        return "1 Person"
    elif size < 6:
        return f"{size} Personen"
    else:
        return "6+ Personen"

def _autopct(pct: float) -> str:
    # Nur anzeigen, wenn mindestens 1 %
    return f"{pct:.1f}%" if pct >= 1 else ""

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
    hh_labels = []
    hh_counts = []
    for size in range(1, 7):
        hh_count = int(row[f"hh_{size}_person"])
        hh_pct = row[f"hh_{size}_hh_prozent"]
        label = _label(size)
        print(f"  {label}: {hh_count:5d} Haushalte ({hh_pct:5.1f} %)")
        hh_labels.append(label)
        hh_counts.append(hh_count)

    print(f"\nTotal Haushalte: {int(row['hh_total'])}")

    print("\nPersonen nach Haushaltsgrösse (skaliert auf echte Einwohnerzahl):")
    pers_labels = []
    pers_counts_scaled = []
    for size in range(1, 7):
        pers_raw = float(row[f"pers_{size}"])
        pers_scaled = pers_raw * scale_factor
        pers_pct = pers_scaled / real_total * 100 if real_total > 0 else 0
        label = _label(size)
        print(
            f"  Personen in {label}-Haushalten: "
            f"{int(round(pers_scaled)):6d} ({pers_pct:5.1f} %)"
        )
        pers_labels.append(label)
        pers_counts_scaled.append(pers_scaled)

    print(f"\nRoh geschätztes Total Personen: {int(round(est_total))}")
    print(f"Verwendetes Total Personen (für 100 %): {int(round(real_total))}")

    # ==== für die DIAGRAMME 5 & 6+ zusammenfassen zu "5+ Personen" ====

    # Haushalte: 1,2,3,4, 5+ (5 + 6+)
    hh_labels_plot = [
        "1 Person",
        "2 Personen",
        "3 Personen",
        "4 Personen",
        "5+ Personen",
    ]
    hh_counts_plot = [
        hh_counts[0],                # 1
        hh_counts[1],                # 2
        hh_counts[2],                # 3
        hh_counts[3],                # 4
        hh_counts[4] + hh_counts[5]  # 5 + 6+
    ]

    # Personen (skaliert): gleiche Aggregation
    pers_labels_plot = hh_labels_plot[:]  # gleiche Labels
    pers_counts_scaled_plot = [
        pers_counts_scaled[0],
        pers_counts_scaled[1],
        pers_counts_scaled[2],
        pers_counts_scaled[3],
        pers_counts_scaled[4] + pers_counts_scaled[5],
    ]

    base_name = safe_name(viertel_name)

    # 1) Haushalte nach Haushaltsgrösse
    plt.figure(figsize=(6, 6))
    plt.pie(
        hh_counts_plot,
        labels=hh_labels_plot,
        autopct=_autopct,
        startangle=90,
    )
    plt.title(f"{viertel_name} 2024 – Haushalte nach Haushaltsgrösse")
    plt.tight_layout()
    file_hh = OUTPUT_DIR / f"{base_name}_haushalte_2024.png"
    plt.savefig(file_hh, dpi=200)
    plt.close()
    print(f"Gespeichert: {file_hh}")

    # 2) Personen nach Haushaltsgrösse (skaliert)
    plt.figure(figsize=(6, 6))
    plt.pie(
        pers_counts_scaled_plot,
        labels=pers_labels_plot,
        autopct=_autopct,
        startangle=90,
    )
    plt.title(f"{viertel_name} 2024 – Personen nach Haushaltsgrösse")
    plt.tight_layout()
    file_pers = OUTPUT_DIR / f"{base_name}_personen_2024.png"
    plt.savefig(file_pers, dpi=200)
    plt.close()
    print(f"Gespeichert: {file_pers}")



# Nur diese zwei Quartiere ausgeben + Diagramme als Dateien speichern
print_quarter("Matthäus")
print_quarter("Bruderholz")
