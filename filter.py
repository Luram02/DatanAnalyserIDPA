import csv
import sys
from pathlib import Path
from datetime import datetime

DELIMITER = ";"


COUNT_COLUMN = "Anzahl"

#Filtert daten für die IDPA arbeit. Befehl zum adden filtern: 
#python filter.py [csv file Name] "Spalte" "Wert"
#z.B. python filter.py 100126_Wohnviertel-Name_Matthäus1919.csv "Datum" "31. Dezember 2023"
def filter_rows(input_file: str, filter_column: str, filter_value: str):
    input_path = Path(input_file)


    now = datetime.now()
    timestamp_for_filename = now.strftime("%H%M")
    timestamp_for_log = now.strftime("%Y-%m-%d %H:%M")


    safe_col = filter_column.replace(" ", "_")
    safe_val = filter_value.replace(" ", "_")


    output_name = f"{input_path.stem}_{safe_col}_{safe_val}{timestamp_for_filename}.csv"
    output_path = input_path.with_name(output_name)


    count_log_path = input_path.with_name("Anzahl.txt")

    total_personen = 0


    with input_path.open(mode="r", encoding="utf-8-sig", newline="") as f_in, \
         output_path.open(mode="w", encoding="utf-8", newline="") as f_out:

        reader = csv.DictReader(f_in, delimiter=DELIMITER)

        if filter_column not in reader.fieldnames:
            print(f"Fehler: Spalte '{filter_column}' nicht gefunden.")
            print(f"Verfügbare Spalten: {reader.fieldnames}")
            sys.exit(1)

        if COUNT_COLUMN not in reader.fieldnames:
            print(f"Fehler: Spalte '{COUNT_COLUMN}' (Personenzahl) nicht gefunden.")
            print(f"Verfügbare Spalten: {reader.fieldnames}")
            sys.exit(1)

        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames, delimiter=DELIMITER)
        writer.writeheader()

        for row in reader:
            if (row.get(filter_column) or "").strip() == filter_value:
                writer.writerow(row)

                raw_count = (row.get(COUNT_COLUMN) or "").strip()
                if raw_count:
                    try:
                        raw_count_clean = raw_count.replace("'", "").replace(" ", "")
                        anzahl = int(raw_count_clean)
                    except ValueError:
                        anzahl = 0
                    total_personen += anzahl

    with count_log_path.open(mode="a", encoding="utf-8") as log:
        log.write(
            f"{timestamp_for_log} | Datei={input_path.name} | "
            f"Filterspalte={filter_column} | Wert={filter_value} | "
            f"Personen={total_personen}\n"
        )

    print(f"Gefilterte Daten gespeichert in: {output_path}")
    print(f"Gesamtzahl Personen (Summe aus '{COUNT_COLUMN}'): {total_personen}")
    print(f"Eintrag in {count_log_path.name} hinzugefügt.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python matfilter.py <input.csv> <Spaltenname> <Filterwert>")
        print('Beispiel: python matfilter.py 100126.csv "Wohnviertel-Name" "Matthäus"')
        sys.exit(1)

    input_file = sys.argv[1]
    filter_column = sys.argv[2]
    filter_value = sys.argv[3]

    filter_rows(input_file, filter_column, filter_value)
