from flask import Flask, request, Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import re
import json

app = Flask(__name__)

REGISTRATION = "FA23-BAI-029"
NEWS_SOURCE = "The Nation Pakistan"
NEWS_BASE = "https://www.nation.com.pk"


def get_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def summarize_text(text, max_sentences=4):
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    summary = ' '.join(sentences[:max_sentences])
    if len(summary) > 1200:
        summary = summary[:1200].rsplit(' ', 1)[0] + '...'
    return summary if summary else text[:500]


def scrape_nation(keyword):
    driver = get_chrome_driver()
    article_url = ""
    summary = ""

    try:
        wait = WebDriverWait(driver, 15)

        # ── Step 1: Open homepage ────────────────────────────────────────────
        driver.get(NEWS_BASE)
        time.sleep(2)

        # ── Step 2: Find and click the search icon/button ────────────────────
        search_icon_selectors = [
            "//span[contains(@class,'search')]",
            "//i[contains(@class,'search')]",
            "//a[contains(@class,'search')]",
            "//button[contains(@class,'search')]",
            "//*[@id='search-icon']",
            "//*[contains(@class,'search-icon')]",
            "//*[contains(@class,'search-toggle')]",
            "//*[contains(@class,'searchIcon')]",
        ]

        clicked = False
        for sel in search_icon_selectors:
            try:
                el = driver.find_element(By.XPATH, sel)
                driver.execute_script("arguments[0].click();", el)
                time.sleep(1)
                clicked = True
                break
            except Exception:
                continue

        # ── Step 3: Find the search input and type keyword ───────────────────
        search_input_selectors = [
            "//input[@type='search']",
            "//input[@name='s']",
            "//input[contains(@class,'search')]",
            "//input[@placeholder]",
            "//input[@type='text']",
        ]

        search_box = None
        for sel in search_input_selectors:
            try:
                els = driver.find_elements(By.XPATH, sel)
                for el in els:
                    if el.is_displayed():
                        search_box = el
                        break
                if search_box:
                    break
            except Exception:
                continue

        if search_box:
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            time.sleep(4)
        else:
            # Direct URL fallback
            driver.get(f"{NEWS_BASE}/?s={keyword.replace(' ', '+')}")
            time.sleep(4)

        # ── Step 4: Collect article links from results page ──────────────────
        # The page URL should now be like nation.com.pk/?s=keyword
        # Grab all links with date patterns (actual articles)
        all_links = driver.find_elements(By.TAG_NAME, "a")
        candidates = []
        for link in all_links:
            try:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if (
                    "nation.com.pk" in href
                    and re.search(r'/\d{2}-\w+-\d{4}/', href)   # date slug like /09-May-2026/
                    and len(text) > 10
                ):
                    candidates.append((href, text))
            except Exception:
                continue

        # ── Step 5: Pick best match — prefer title containing keyword ─────────
        article_url = ""
        kw_lower = keyword.lower()
        for href, text in candidates:
            if kw_lower in text.lower() or kw_lower in href.lower():
                article_url = href
                break

        # Otherwise take first result
        if not article_url and candidates:
            article_url = candidates[0][0]

        if not article_url:
            article_url = NEWS_BASE

        # ── Step 6: Visit article and extract text ───────────────────────────
        driver.get(article_url)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
        except Exception:
            time.sleep(3)

        content_selectors = [
            "//div[contains(@class,'post-content')]//p",
            "//div[contains(@class,'entry-content')]//p",
            "//div[contains(@class,'article-content')]//p",
            "//div[contains(@class,'td-post-content')]//p",
            "//article//p",
            "//main//p",
        ]

        paragraphs = []
        for sel in content_selectors:
            try:
                els = driver.find_elements(By.XPATH, sel)
                if els:
                    paragraphs = [e.text.strip() for e in els if len(e.text.strip()) > 40]
                    if paragraphs:
                        break
            except Exception:
                continue

        if paragraphs:
            summary = summarize_text(' '.join(paragraphs))
        else:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            summary = summarize_text(body_text)

    except Exception as e:
        summary = f"Error: {str(e)}"
        if not article_url:
            article_url = NEWS_BASE
    finally:
        driver.quit()

    return article_url, summary


@app.route("/get", methods=["GET"])
def get_news():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return Response(
            json.dumps({"error": "Missing 'keyword' query parameter"}),
            status=400, mimetype="application/json"
        )
    try:
        url, summary = scrape_nation(keyword)
        result = {
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": url,
            "summary": summary
        }
        return Response(json.dumps(result, indent=2), status=200, mimetype="application/json")
    except Exception as e:
        result = {
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": NEWS_BASE,
            "summary": f"Scraping failed: {str(e)}"
        }
        return Response(json.dumps(result, indent=2), status=500, mimetype="application/json")


@app.route("/", methods=["GET"])
def index():
    return f"""
    <html><body style='font-family:sans-serif;padding:40px;max-width:600px'>
      <h1>DevOps Quiz 3 – Selenium News Scraper</h1>
      <p><b>Registration:</b> {REGISTRATION}</p>
      <p><b>News Source:</b> {NEWS_SOURCE}</p>
      <p><b>Try it:</b> <a href='/get?keyword=pakistan'>/get?keyword=pakistan</a></p>
    </body></html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000, debug=False)
