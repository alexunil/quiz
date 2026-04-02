# Basis-Image: offizielles Python 3.12, "slim" = kleines Image ohne unnötige Tools
FROM python:3.12-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# Erst nur requirements.txt kopieren (nicht den ganzen Code!)
# Warum? Docker cached diesen Layer. Wenn sich nur der Code ändert,
# aber nicht die requirements.txt, muss pip install nicht nochmal laufen.
COPY requirements.txt .

# Abhängigkeiten installieren
# --no-cache-dir: pip soll keinen Cache anlegen → kleineres Image
RUN pip install --no-cache-dir -r requirements.txt

# Jetzt erst den restlichen Code kopieren
COPY . .

# Datenverzeichnisse anlegen (Kataloge, Datenbank)
RUN mkdir -p data/catalogs instance

# Port 5009 im Container freigeben (nur Dokumentation, kein echtes Binding)
EXPOSE 5009

# Umgebungsvariablen für den Container
ENV FLASK_ENV=production

# Startbefehl: gunicorn als Production-Server statt flask run
# -w 2: 2 Worker-Prozesse
# -b 0.0.0.0:5009: auf allen Interfaces lauschen
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5009", "run:app"]
