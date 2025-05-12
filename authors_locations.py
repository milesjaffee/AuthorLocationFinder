import pandas as pd
import requests
from geopy.geocoders import Nominatim
import folium
from collections import defaultdict
import time
import math
import re
import argparse
import os
import sys

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
geolocator = Nominatim(user_agent="author_mapper")

#gets a list of unique authors from the goodreads csv. filter out to-read list 
def get_unique_authors(csv_path, toread_enabled):
    df = pd.read_csv(csv_path)
    if (not toread_enabled):
        df = df[df['Exclusive Shelf'] != 'to-read']
    authors = df['Author'].dropna().unique()
    return list(set(authors))

#outdated. gets long paragraph from wikipedia. perhaps useful for tooltips
def get_birthplace_info(author): 
    search_url = f"https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'titles': author,
        'prop': 'extracts',
        'explaintext': True,
    }
    response = requests.get(search_url, params=params)
    data = response.json()
    pages = data['query']['pages']
    page = next(iter(pages.values()))
    extract = page.get('extract', '')
    
    # Try to find a line with 'born in' or 'birthplace'
    for line in extract.split('\n'):
        if 'born in' in line.lower():
            return line
            #return line.split('born in', 1)[1].strip().split('.')[0]
        if 'birthplace' in line.lower():
            return line
            #return line.split(':', 1)[1].strip()
    return None

#gets coords of author birthplace based on wikidata search
def get_birthplace_coords(author_name):
    # Clean up author name
    author_name = re.sub(r"\s+", " ", author_name).strip()


    # Step 1: Search Wikidata for the best matching QID
    search_url = "https://www.wikidata.org/w/api.php"
    search_params = {
        "action": "wbsearchentities",
        "search": author_name,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 3
    }

    try:
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_results = search_response.json().get("search", [])

        #print(search_results)

        # Step 2: Find a result with a literary description
        target_qid = None
        for result in search_results:
            description = result.get("description", "").lower()
            if any(x in description for x in ["writer", "author", "novelist", "poet", "playwright"]):
                target_qid = result["id"]
                break

        # Fallback: just take the first result
        if not target_qid and search_results:
            target_qid = search_results[0]["id"]

        if not target_qid:
            print(f"No Wikidata search result for: {author_name}")
            return None, None, None

        # Step 3: Use QID to fetch birthplace from SPARQL
        query = f"""
        SELECT DISTINCT ?birthplace ?birthplaceLabel WHERE {{
          wd:{target_qid} p:P19 ?birthplaceStatement.
          ?birthplaceStatement ps:P19 ?birthplace.
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """

        headers = {"Accept": "application/sparql-results+json",
                   "User-Agent": "goodreads author mapper tool, mej327@lehigh.edu"
                   }
        response = requests.get(
            "https://query.wikidata.org/sparql",
            params={'query': query},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        results = response.json().get("results", {}).get("bindings", [])

        print(results)
        for result in results:
            #birthplace_label = result["birthplaceLabel"]["value"]

            if "birthplace" not in result:
                continue

            birthplace_qid = result["birthplace"]["value"].split("/")[-1]

            coord_query = f"""
            SELECT ?coord WHERE {{
              wd:{birthplace_qid} wdt:P625 ?coord.
            }}
            """
            coord_response = requests.get(
                "https://query.wikidata.org/sparql",
                params={'query': coord_query},
                headers=headers,
                timeout=10
            )
            coord_response.raise_for_status()
            coord_results = coord_response.json().get("results", {}).get("bindings", [])

            if coord_results:
                coord = coord_results[0]["coord"]["value"]
                lon_lat = coord.replace('Point(', '').replace(')', '').split()
                lat, lon = float(lon_lat[1]), float(lon_lat[0])
                birthplace = result['birthplaceLabel']['value']
                return birthplace, lat, lon

            time.sleep(0.2)  # Be respectful

        # Step 3: If no coords anywhere, just return label of first birthplace
        if results:
            birthplace = results[0]['birthplaceLabel']['value']
            return birthplace, None, None

    except Exception as e:
        print(f"[ERROR] {author_name}: {e}")

    return None, None, None

# fallback geocode function
def geocode_place(place):
    try:
        location = geolocator.geocode(place)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

#creates the map of the authors
def create_author_map(authors):
    grouped_authors = defaultdict(list)

    for i, author in enumerate(authors):
        print(f"[{i+1}/{len(authors)}] Processing: {author}")
        birthplace, lat, lon = get_birthplace_coords(author)
        if lat is not None and lon is not None:
            key = (round(lat, 4), round(lon, 4))  # Rounding to reduce accidental float precision mismatch
            grouped_authors[key].append(author)
        elif birthplace:
            lat, lon = geocode_place(birthplace)
            time.sleep(1)
        else:
            print(f"No coordinates found for {author}")
        time.sleep(0.7)

    # Create map
    m = folium.Map(location=[20, 0], zoom_start=2)

    # Add one marker per location
    for (lat, lon), names in grouped_authors.items():
        popup_text = ", ".join(names)
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="book", prefix="fa")
        ).add_to(m)

    # Save map
    m.save("author_birthplaces_map.html")
    print("✅ Map saved as author_birthplaces_map.html")

# stock list of a few default authors for testing
authors = [
    "Jane Austen",
    "Henrik Ibsen",
    "Haruki Murakami"
]

def main():
    parser = argparse.ArgumentParser(description="Process a Goodreads export file to get a map (html file) with authors' birthplaces.")
    parser.add_argument(
        '-f', '--file',
        type=str,
        default='goodreads_library_export.csv',
        help='Path to the Goodreads CSV export file (default: goodreads_library_export.csv)'
    )
    parser.add_argument(
        '-t', '--toread',
        action='store_true',
        help='Count authors in the to-read list?'
    )

    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

    toread_enabled = args.toread  # True if -t is used

    authors = get_unique_authors(args.file, toread_enabled)
    create_author_map(authors)


# Only run if this script is executed directly
if __name__ == "__main__":
    main()
