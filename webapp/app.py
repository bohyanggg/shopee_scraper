import os
import json
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash

# Load environment variables from .env
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-key")

# Paths
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(WORKSPACE_ROOT, "downloaded_files")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Ensure workspace root is on the import path
import sys  # noqa: E402
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# Import scraper after setting up paths
from app.scraping.shopee_scraper import ShopeeScraper  # noqa: E402


def _sanitize_filename(text: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text.strip())


@app.get("/")
def index():
    return render_template(
        "index.html",
        default_keyword="",
        default_numpage=0,
        default_itemperpage=0,
    )


@app.post("/scrape")
def scrape():
    # Read form inputs
    keyword = (request.form.get("keyword") or "").strip()
    try:
        numpage = int(request.form.get("numpage") or 0)
        itemperpage = int(request.form.get("itemperpage") or 0)
    except ValueError:
        flash("Invalid numeric inputs. Please provide valid integers.")
        return redirect(url_for("index"))

    if not keyword:
        flash("Keyword is required.")
        return redirect(url_for("index"))

    if numpage < 0 or itemperpage < 0:
        flash("Numbers must be 0 or greater.")
        return redirect(url_for("index"))

    # Credentials from environment
    username = os.environ.get("SHOPEE_USERNAME")
    password = os.environ.get("SHOPEE_PASSWORD")
    if not username or not password:
        flash("Missing credentials in .env (SHOPEE_USERNAME/SHOPEE_PASSWORD)")
        return redirect(url_for("index"))

    # Run scraper (pass None for optional parameters if they are 0)
    scraper = ShopeeScraper(
        username=username,
        password=password,
        keyword=keyword,
        numpage=numpage if numpage > 0 else None,
        itemperpage=itemperpage if itemperpage > 0 else None,
    )

    try:
        scraper.scrape()
    except Exception as e:
        flash(f"Scrape failed: {e}")
        return redirect(url_for("index"))

    results = scraper.results_data

    # Persist results to JSON
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_keyword = _sanitize_filename(keyword or "results")
    filename = f"shopee_{safe_keyword}_{ts}.json"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return render_template(
        "results.html",
        results=results,
        download_filename=filename,
    )


@app.get("/downloads/<path:filename>")
def downloads(filename: str):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


@app.get("/history")
def history():
    """List all past scrape results."""
    files = []
    if os.path.exists(DOWNLOAD_DIR):
        for fname in sorted(os.listdir(DOWNLOAD_DIR), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(DOWNLOAD_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    files.append({
                        "filename": fname,
                        "keyword": data.get("keyword", "Unknown"),
                        "itemCount": len(data.get("data", [])),
                        "createdAt": data.get("createdAt", "N/A"),
                    })
                except Exception:
                    pass
    return render_template("history.html", files=files)


@app.get("/results/<path:filename>")
def view_result(filename: str):
    """View a specific result file."""
    fpath = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(fpath) or not filename.endswith(".json"):
        flash("Result file not found.")
        return redirect(url_for("history"))
    
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception as e:
        flash(f"Error reading file: {e}")
        return redirect(url_for("history"))
    
    return render_template("results.html", results=results, download_filename=filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
