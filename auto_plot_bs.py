import argparse
from pathlib import Path
from datetime import datetime
import math

import pandas as pd
import matplotlib.pyplot as plt

# Standard-Konfiguration – bei Bedarf anpassen
DELIMITER = ";"

POSSIBLE_YEAR_COLS = ["Jahr", "jahr"]
POSSIBLE_QUARTER_COLS = [
    "Wohnviertel-Name",
    "wohnviertel_name",
    "Wohnviertel",
    "wohnviertel",
]
POSSIBLE_COUNT_COLS = ["Anzahl", "anzahl"]
POSSIBLE_NAT_COLS = [
    "Staatsangehörigkeit",   # falls mal ein anderes File mit Umlaut kommt
    "Staatsangehoerigkeit",  # 100126 / 100128
    "staatsangehoerigkeit",  # fallback klein
]
POSSIBLE_AGE_COLS = ["Alter", "alter"]

# Feste Altersgruppen für alle Quartiere
AGE_BINS = [0, 6, 12, 18, 25, 35, 45, 65, 80, 90, 100, math.inf]
AGE_LABELS = [
    "0–5",
    "6–11",
    "12–17",
    "18–24",
    "25–34",
    "35–44",
    "45–64",
    "65–79",
    "80–89",
    "90–99",
    "100+",
]

# Ab welcher Anteilshöhe bekommt eine Nationalität eine eigene Kategorie
# (z.B. 0.03 = 3 %). Alles darunter wird zu "Restliche" zusammengefasst.
MIN_SHARE_FOR_OWN_CATEGORY = 0.01
MAX_CATEGORIES = 15  # Sicherheitslimit, damit die Legende nicht explodiert


def guess_col(possible_names, columns, what: str, required: bool = True):
    """Sucht eine Spalte unabhängig von Gross-/Kleinschreibung."""
    lower_map = {c.lower(): c for c in columns}
    for name in possible_names:
        key = name.lower()
        if key in lower_map:
            return lower_map[key]
    if required:
        raise SystemExit(
            f"Keine passende Spalte für {what} gefunden. "
            f"Gesucht: {possible_names}, Vorhanden: {list(columns)}"
        )
    return None


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, delimiter=DELIMITER, encoding="utf-8-sig", low_memory=False)
    return df


def auto_plot(df: pd.DataFrame,
              output_path: Path,
              title_prefix: str = "",
              use_pie: bool = False,
              nationality_filter: str | None = None):
    # Jahr- und Anzahl-Spalte ermitteln
    year_col = guess_col(POSSIBLE_YEAR_COLS, df.columns, "Jahr")
    count_col = guess_col(POSSIBLE_COUNT_COLS, df.columns, "Anzahl")

    # Jahr numerisch
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[year_col])

    years = sorted(df[year_col].unique())
    n_years = len(years)
    if n_years == 0:
        raise SystemExit("Keine gültigen Jahreswerte gefunden.")

    # Prüfen, ob Altersspalte vorhanden ist
    age_col = guess_col(POSSIBLE_AGE_COLS, df.columns, "Alter", required=False)
    if age_col is not None:
        print("Altersspalte erkannt -> Altersdiagramm")
        return auto_plot_age(df, year_col, age_col, count_col, output_path, title_prefix)

    # Sonst: Nationalitäten-Mode
    nat_col = guess_col(POSSIBLE_NAT_COLS, df.columns, "Staatsangehörigkeit")

    # Wenn eine spezifische Staatsangehörigkeit verlangt ist:
    if nationality_filter:
        return plot_nationality_trend(
            df, year_col, nat_col, count_col,
            nationality_filter, output_path, title_prefix
        )

    nats = df[nat_col].dropna().unique()
    n_nat = len(nats)

    print(f"Gefundene Jahre: {years}")
    print(f"Anzahl Nationalitäten: {n_nat}")

    # ------------------------------------------------------------------
    # Fall A: Ein Jahr → Verteilung nach Nationalität (Balken- ODER Kreisdiagramm)
    # ------------------------------------------------------------------
    if n_years == 1:
        year = years[0]
        grouped = (
            df.groupby(nat_col)[count_col]
            .sum()
            .sort_values(ascending=False)
        )

        total = grouped.sum()
        shares = grouped / total

        print(
            f"Schwelle für eigene Kategorie: "
            f"{MIN_SHARE_FOR_OWN_CATEGORY * 100:.1f}% des Gesamtbestands."
        )

        # Nach Anteil filtern: alles unterhalb der Schwelle in "Restliche"
        mask_keep = shares >= MIN_SHARE_FOR_OWN_CATEGORY
        keep = grouped[mask_keep]

        # Falls immer noch zu viele Kategorien: Top-N nehmen
        if len(keep) > MAX_CATEGORIES:
            keep = keep.head(MAX_CATEGORIES)

        rest_sum = total - keep.sum()

        if rest_sum > 0:
            keep["Restliche"] = rest_sum
            print(
                f"'Restliche' umfassen zusammen "
                f"{rest_sum/total*100:.1f}% ({int(rest_sum)} Personen)."
            )
        else:
            print("'Restliche' wäre leer – alle Nationalitäten sind einzeln dargestellt.")

        grouped = keep

        if use_pie:
            # Kreisdiagramm
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(
                grouped.values,
                labels=grouped.index,
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.axis("equal")  # Kreis
            title = f"{title_prefix} – Nationalitätenverteilung {int(year)}"
            ax.set_title(title)

            plt.tight_layout()
            fig.savefig(str(output_path), dpi=300)
            plt.close(fig)

            print("Diagramm-Typ: Kreisdiagramm (Nationalitäten)")
            print(f"Gespeichert als: {output_path}")
        else:
            # Horizontales Balkendiagramm
            fig_height = max(5, len(grouped) * 0.4)
            fig, ax = plt.subplots(figsize=(10, fig_height))

            grouped.sort_values().plot(kind="barh", ax=ax)
            ax.set_xlabel("Anzahl Personen")
            ax.set_ylabel("Staatsangehörigkeit")
            title = f"{title_prefix} – Nationalitätenverteilung {int(year)}"
            ax.set_title(title)
            ax.grid(axis="x", linestyle=":", alpha=0.5)

            plt.tight_layout()
            fig.savefig(str(output_path), dpi=300)
            plt.close(fig)

            print("Diagramm-Typ: Horizontales Balkendiagramm")
            print(f"Gespeichert als: {output_path}")
        return

    if use_pie:
        print("Hinweis: --cycle wirkt nur, wenn genau ein Jahr ausgewählt ist.")

    # ------------------------------------------------------------------
    # Fall B: Mehrere Jahre → gestapeltes Flächendiagramm (Nationalität)
    # ------------------------------------------------------------------

    grouped = (
        df.groupby([year_col, nat_col])[count_col]
        .sum()
        .reset_index()
    )

    # Pivot: Zeilen = Jahr, Spalten = Nationalität
    pivot = grouped.pivot(index=year_col, columns=nat_col, values=count_col)
    pivot = pivot.sort_index()

    # Wie viele Nationalitäten explizit zeigen? (Schweiz + X grösste + Restliche)
    max_bands_without_rest = 10

    totals = (
        grouped.groupby(nat_col)[count_col]
        .sum()
        .sort_values(ascending=False)
    )

    selected_nats = []

    # Schweiz immer explizit
    if "Schweiz" in totals.index:
        selected_nats.append("Schweiz")

    # Danach die grössten anderen Nationalitäten
    for nat in totals.index:
        if nat == "Schweiz":
            continue
        if len(selected_nats) >= max_bands_without_rest:
            break
        selected_nats.append(nat)

    print("Explizit dargestellte Nationalitäten:", selected_nats)

    stack_df = pivot[selected_nats].fillna(0)

    # Gesamtbevölkerung pro Jahr
    total_per_year = pivot.sum(axis=1).fillna(0)

    # Restliche = Gesamt – Summe der ausgewählten Nationalitäten
    rest = total_per_year - stack_df.sum(axis=1)
    rest_name = "Restliche"
    stack_df[rest_name] = rest

    plot_columns = selected_nats + [rest_name]

    # Gestapeltes Flächendiagramm
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(
        stack_df.index.values,
        [stack_df[col].values for col in plot_columns],
        labels=plot_columns
    )

    ax.set_xlabel("Jahr")
    ax.set_ylabel("Anzahl Personen")
    title = f"{title_prefix} – Nationalitätenzusammensetzung"
    ax.set_title(title)
    ax.legend(title="Staatsangehörigkeit", loc="upper left", ncol=2)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=300)
    plt.close(fig)

    print("Diagramm-Typ: Gestapeltes Flächendiagramm (inkl. 'Restliche')")
    print(f"Gespeichert als: {output_path}")


def plot_nationality_trend(df: pd.DataFrame,
                           year_col: str,
                           nat_col: str,
                           count_col: str,
                           nationality: str,
                           output_path: Path,
                           title_prefix: str):
    """Zeitverlauf einer Staatsangehörigkeit + jährliche Veränderung."""
    df_nat = df[df[nat_col] == nationality].copy()

    if df_nat.empty:
        raise SystemExit(f"Keine Daten für Staatsangehörigkeit '{nationality}' gefunden.")

    series = (
        df_nat.groupby(year_col)[count_col]
        .sum()
        .sort_index()
    )

    # Jährliche Veränderung (Differenz zum Vorjahr)
    delta = series.diff().fillna(0)

    print(f"Zeitverlauf für {nationality}:")
    print("Jahr | Anzahl | Veränderung ggü. Vorjahr")
    for year, total, d in zip(series.index, series.values, delta.values):
        print(f"{int(year)} | {int(total)} | {int(d):+d}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Oben: absolute Anzahl
    ax1.plot(series.index, series.values, marker="o")
    ax1.set_ylabel("Anzahl Personen")
    title1 = f"{title_prefix} – {nationality}: Anzahl pro Jahr"
    ax1.set_title(title1)
    ax1.grid(True, linestyle=":", alpha=0.5)

    # Unten: jährliche Veränderung
    colors = ["tab:green" if d >= 0 else "tab:red" for d in delta.values]
    ax2.bar(series.index, delta.values, color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xlabel("Jahr")
    ax2.set_ylabel("Veränderung zum Vorjahr")
    title2 = f"Jährliche Veränderung ({nationality})"
    ax2.set_title(title2)
    ax2.grid(True, axis="y", linestyle=":", alpha=0.5)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=300)
    plt.close(fig)

    print("Diagramm-Typ: Linien- + Balkendiagramm (Zeitverlauf & Veränderung)")
    print(f"Gespeichert als: {output_path}")


def auto_plot_age(df: pd.DataFrame,
                  year_col: str,
                  age_col: str,
                  count_col: str,
                  output_path: Path,
                  title_prefix: str):
    """Altersstruktur je Jahr als Diagramm zeichnen (mit feinen Gruppen & Farbverlauf)."""

    # Alter numerisch
    df[age_col] = pd.to_numeric(df[age_col], errors="coerce")
    df = df.dropna(subset=[age_col])

    # Altersgruppen bilden (0–5, 6–11, ..., 100+)
    df["Altersgruppe"] = pd.cut(
        df[age_col],
        bins=AGE_BINS,
        labels=AGE_LABELS,
        right=True,
        include_lowest=True,
    )
    df = df.dropna(subset=["Altersgruppe"])

    years = sorted(df[year_col].unique())
    n_years = len(years)
    print(f"Gefundene Jahre (Alter-Mode): {years}")

    # Gruppen in fixer Reihenfolge (nur die, die wirklich vorkommen)
    groups_present = [
        g for g in AGE_LABELS
        if g in df["Altersgruppe"].unique()
    ]

    # 1 Jahr -> Säulendiagramm der Altersgruppen
    if n_years == 1:
        year = years[0]
        grouped = (
            df.groupby("Altersgruppe")[count_col]
            .sum()
            .reindex(groups_present)
            .fillna(0)
        )

        fig, ax = plt.subplots(figsize=(10, 6))

        # Farben entlang eines Farbverlaufs (ähnliche Alter -> ähnliche Farbe)
        cmap = plt.get_cmap("viridis", len(groups_present))
        colors = [cmap(i) for i in range(len(groups_present))]

        grouped.plot(kind="bar", ax=ax, color=colors)
        ax.set_xlabel("Altersgruppe")
        ax.set_ylabel("Anzahl Personen")
        title = f"{title_prefix} – Altersstruktur {int(year)}"
        ax.set_title(title)
        ax.grid(axis="y", linestyle=":", alpha=0.5)

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=300)
        plt.close(fig)

        print("Diagramm-Typ: Säulendiagramm (Altersstruktur)")
        print(f"Gespeichert als: {output_path}")
        return

    # Mehrere Jahre -> gestapeltes Flächendiagramm nach Altersgruppen
    grouped = (
        df.groupby([year_col, "Altersgruppe"])[count_col]
        .sum()
        .reset_index()
    )

    pivot = grouped.pivot(index=year_col, columns="Altersgruppe", values=count_col)
    pivot = pivot.sort_index()
    pivot = pivot[groups_present].fillna(0)

    fig, ax = plt.subplots(figsize=(12, 6))

    cmap = plt.get_cmap("viridis", len(groups_present))
    colors = [cmap(i) for i in range(len(groups_present))]

    ax.stackplot(
        pivot.index.values,
        [pivot[g].values for g in groups_present],
        labels=groups_present,
        colors=colors,
    )

    ax.set_xlabel("Jahr")
    ax.set_ylabel("Anzahl Personen")
    title = f"{title_prefix} – Altersstruktur nach Jahr"
    ax.set_title(title)
    ax.legend(title="Altersgruppe", loc="upper left", ncol=2)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=300)
    plt.close(fig)

    print("Diagramm-Typ: Gestapeltes Flächendiagramm (Altersgruppen)")
    print(f"Gespeichert als: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Automatisches Diagramm für BS-Demografie-Daten erzeugen."
    )
    parser.add_argument("input_csv", help="Pfad zur CSV-Datei (Export von data.bs.ch)")
    parser.add_argument(
        "--quartier",
        help="Wohnviertel-Name filtern (z.B. 'Matthäus')",
        default=None,
    )
    parser.add_argument(
        "--jahr",
        type=int,
        help="Optional: auf ein bestimmtes Jahr filtern (z.B. 2023)",
        default=None,
    )
    parser.add_argument(
        "--output",
        help="Ausgabedatei (PNG). Standard: automatisch im selben Ordner.",
        default=None,
    )
    parser.add_argument(
        "--cycle",
        help="Bei Einzeljahr (Nationalitäten) Kreisdiagramm statt Balkendiagramm",
        action="store_true",
    )
    parser.add_argument(
        "--nationality",
        help="Optional: Verlauf einer bestimmten Staatsangehörigkeit (z.B. 'Ukraine')",
        default=None,
    )

    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise SystemExit(f"Datei nicht gefunden: {input_path}")

    df = load_data(input_path)

    # Spaltennamen raten
    quarter_col = guess_col(POSSIBLE_QUARTER_COLS, df.columns, "Wohnviertel-Name")
    year_col = guess_col(POSSIBLE_YEAR_COLS, df.columns, "Jahr")

    # Filtern nach Wohnviertel
    title_parts = []
    if args.quartier:
        df = df[df[quarter_col] == args.quartier]
        title_parts.append(f"Wohnviertel {args.quartier}")

    # Filtern nach Jahr (falls gewünscht)
    if args.jahr is not None:
        df = df[df[year_col] == args.jahr]
        title_parts.append(f"Jahr {args.jahr}")

    if df.empty:
        raise SystemExit("Nach dem Filtern sind keine Daten mehr vorhanden.")

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        base_name = input_path.stem
        extra = "_".join(part.replace(" ", "_") for part in title_parts) or "gesamt"
        output_path = input_path.with_name(f"{base_name}_{extra}_{timestamp}.png")

    title_prefix = " – ".join(title_parts) if title_parts else "Gesamt"

    auto_plot(
        df,
        output_path,
        title_prefix=title_prefix,
        use_pie=args.cycle,
        nationality_filter=args.nationality,
    )


if __name__ == "__main__":
    main()
