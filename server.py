import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
from playwright.sync_api import sync_playwright
import requests

app = Flask(__name__)


def scrape_seite(url):
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="de-DE",
    )
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    soup = BeautifulSoup(page.content(), "html.parser")
    browser.close()
    return soup.get_text(separator="\n", strip=True)[:25000]


@app.route("/", methods=["GET", "POST"])
def index():
  ergebnis = None
  if request.method == "POST":
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
      return render_template(
          "index.html",
          ergebnis="Fehler: GEMINI_API_KEY ist auf dem Server nicht hinterlegt.",
      )

    url = request.form.get("url", "").strip()
    kriterien = request.form.get("kriterien", "").strip()

    try:
      seiten_text = scrape_seite(url)
      if len(seiten_text) < 100:
        return render_template(
            "index.html",
            ergebnis=(
                "Die Webseite hat fast keinen Text geliefert (evtl."
                f" Bot-Blockade). Inhalt: {seiten_text}"
            ),
        )

      prompt = f"""
            Du bist ein präziser Einkaufs-Assistent. Analysiere den folgenden Text einer Webseite mit Angeboten.
            Filtere ALLE Angebote heraus, die exakt diesen Kriterien entsprechen:
            "{kriterien}"
            
            Liste jeden Treffer übersichtlich mit Titel, Preis und kurzen Details auf. Wenn nichts passt, sage es ehrlich.
            
            Webseiten-Inhalt:
            {seiten_text}
            """
      res = requests.post(
          "https://googleapis.com",
          headers={
              "Content-Type": "application/json",
              "x-goog-api-key": api_key,
          },
          json={"contents": [{"parts": [{"text": prompt}]}]},
          timeout=60,
      )
      if res.status_code != 200:
        ergebnis = (
            f"Google-Antwort (Status {res.status_code}): {res.text[:500]}"
        )
      else:
        data = res.json()
        ergebnis = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
      ergebnis = f"Fehler beim Auslesen: {str(e)}"

  return render_template("index.html", ergebnis=ergebnis)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
