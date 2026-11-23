import os
from flask import Flask, render_template, request
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from google import genai

app = Flask(__name__)

# Holt den Key sicher aus den Umgebungsvariablen des Servers
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def scrape_seite(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()
        return soup.get_text(separator="\n", strip=True)[:25000]

@app.route("/", methods=["GET", "POST"])
def index():
    ergebnis = None
    if request.method == "POST":
        if not client:
            return render_template("index.html", ergebnis="Fehler: GEMINI_API_KEY ist auf dem Server nicht hinterlegt.")
            
        url = request.form.get("url")
        kriterien = request.form.get("kriterien")
        
        try:
            seiten_text = scrape_seite(url)
            prompt = f"""
            Du bist ein präziser Einkaufs-Assistent. Analysiere den folgenden Text einer Webseite mit Angeboten.
            Filtere ALLE Angebote heraus, die exakt diesen Kriterien entsprechen:
            "{kriterien}"
            
            Liste jeden Treffer übersichtlich mit Titel, Preis und kurzen Details auf. Wenn nichts passt, sage es ehrlich.
            
            Webseiten-Inhalt:
            {seiten_text}
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            ergebnis = response.text
        except Exception as e:
            ergebnis = f"Fehler beim Auslesen: {str(e)}"
            
    return render_template("index.html", ergebnis=ergebnis)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
