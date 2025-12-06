import csv
import sys
from pathlib import Path
from collections import Counter

# In CH/DE sind CSVs oft mit ';' getrennt.
DELIMITER = ";"

# Spaltenname genau wie in deiner Datei:
COLUMN_NAME = "Staatsangehoerigkeit"


def count_nationalities(input_file: str, output_file: str | None = None):
    input_path = Path(input_file)

    # Default: gleicher Name, aber _staatsangehoerigkeiten.txt
    if output_file is None:
        output_path = input_path.with_name(input_path.stem + "_staatsangehoerigkeiten.txt")
    else:
        output_path = Path(output_file)

    counter = Counter()

    # WICHTIG: utf-8-sig entfernt das BOM (\ufeff) am Anfang
    with input_path.open(mode="r", encoding="utf-8-sig", newline="") as f_in:
        reader = csv.DictReader(f_in, delimiter=DELIMITER)

        if COLUMN_NAME not in reader.fieldnames:
            raise KeyError(
                f"Spalte '{COLUMN_NAME}' nicht gefunden. "
                f"Gefundene Spalten: {reader.fieldnames}"
            )

        for row in reader:
            nat = (row.get(COLUMN_NAME) or "").strip()
            if nat:  # leere Einträge ignorieren
                counter[nat] += 1

    # Sortieren nach Staatsangehörigkeit (alphabetisch)
    sorted_items = sorted(counter.items(), key=lambda x: x[0])

    total = sum(counter.values())
    with output_path.open(mode="w", encoding="utf-8") as f_out:
        f_out.write(f"Auswertung Staatsangehörigkeit für Datei: {input_path.name}\n")
        f_out.write(f"Gesamtanzahl Einträge mit Staatsangehörigkeit: {total}\n\n")
        f_out.write("Staatsangehoerigkeit\tAnzahl\n")
        f_out.write("-" * 40 + "\n")
        for nat, count in sorted_items:
            f_out.write(f"{nat}\t{count}\n")

    print(f"Fertig. Ergebnis gespeichert in: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python staatCounter.py <input.csv> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None
    count_nationalities(input_file, output_file)
