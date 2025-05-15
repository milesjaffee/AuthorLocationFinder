# AuthorLocationFinder
 Finds locations of authors based on a given csv. Outputs openstreetmap-based HTML - just click on it or drag into a browser to view your nice, zoomable, draggable map.

## How to use

1. Put your Goodreads CSV (which you get from the "Export library" button on this page: [https://www.goodreads.com/review/import]) into the AuthorLocationFinder folder. *If it's named goodreads_library_export.csv, replace the default file with that name. If it's named something else, you have to use the -f command-line tag to access it!*

2. In main directory, run **python authors_locations.py** on command line with tags after it (ex. "python authors_locations.py -f bar.csv -t")

3. After the command-line output finishes, your map will be generated at **author_birthplaces_map.html**. Check out **author_birthplaces_map_default.html** for an example of what this could look like!

## Optional command-line tags

* **-t** (no argument necessary) to add locations of authors on your to-read list. If this tag is not used, only authors of "currently reading" and "previously read" books will be added.

* **-f (filename)** to read from a particular file. If this tag is not used, it will read from my default file, which is named goodreads_library_export.csv.
