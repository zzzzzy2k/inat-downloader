import json
import csv

def json_to_csv(json_file: str = "observations.json", csv_file: str = "observations.csv"):
    """将 observations.json 转换为 CSV"""

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])

    fieldnames = [
        "id", "species_guess", "scientific_name", "common_name_cn",
        "observed_on", "location", "place_guess", "user_login",
        "quality_grade", "identifications_count", "photos_count", "photo_urls"
    ]

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for obs in results:
            taxon = obs.get("taxon", {})
            photos = obs.get("photos", [])

            row = {
                "id": obs.get("id"),
                "species_guess": obs.get("species_guess"),
                "scientific_name": taxon.get("name"),
                "common_name_cn": taxon.get("preferred_common_name"),
                "observed_on": obs.get("observed_on"),
                "location": obs.get("location"),
                "place_guess": obs.get("place_guess"),
                "user_login": obs.get("user", {}).get("login"),
                "quality_grade": obs.get("quality_grade"),
                "identifications_count": obs.get("identifications_count"),
                "photos_count": len(photos),
                "photo_urls": ";".join(p.get("url", "") for p in photos)
            }
            writer.writerow(row)

    print(f"Saved {len(results)} observations to {csv_file}")

if __name__ == "__main__":
    json_to_csv()
