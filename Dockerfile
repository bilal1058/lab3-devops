# ── Base image ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Metadata
LABEL maintainer="FA23-BAI-029"
LABEL description="Selenium news scraper – The Washington Post – DevOps Quiz 3"

# ── System dependencies + Chrome + ChromeDriver ──────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        curl \
        gnupg \
        unzip \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libc6 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libexpat1 \
        libfontconfig1 \
        libgbm1 \
        libgcc1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libstdc++6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxtst6 \
        lsb-release \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome stable
RUN wget -q -O /tmp/google-chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/google-chrome.deb \
    && rm /tmp/google-chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver via Chrome for Testing
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+') \
    && CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Chrome version: $CHROME_VERSION  Major: $CHROME_MAJOR" \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
         -O /tmp/chromedriver.zip \
    || wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}" -O /tmp/cd_ver \
    && CD_VER=$(cat /tmp/cd_ver 2>/dev/null || echo "") \
    && if [ -n "$CD_VER" ]; then \
         wget -q "https://chromedriver.storage.googleapis.com/${CD_VER}/chromedriver_linux64.zip" \
              -O /tmp/chromedriver.zip; \
       fi \
    && unzip -o /tmp/chromedriver.zip -d /tmp/chromedriver_dir \
    && find /tmp/chromedriver_dir -name "chromedriver" -exec mv {} /usr/bin/chromedriver \; \
    && chmod +x /usr/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /tmp/chromedriver_dir /tmp/cd_ver

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY app.py .

# ── Expose port & run ─────────────────────────────────────────────────────────
EXPOSE 7000
CMD ["python", "app.py"]
