FROM python:3.11-slim

# Install system dependencies

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome with signed repository key (no apt-key)

RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/
keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://
dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory

WORKDIR /app

# Copy requirements and install Python dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code

COPY . .

# Create necessary directories

RUN mkdir -p src/database reports

# Set environment variables

ENV PYTHONPATH=/app
ENV FLASK_APP=src/main.py
ENV FLASK_ENV=production

# Create non-root user for security

RUN useradd -m -u 1000 hvacuser && chown -R hvacuser:hvacuser /app
USER hvacuser

# Expose port

EXPOSE 5000

# Health check

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/login || exit 1

# Start application

CMD ["python", "src/main.py"]
EOF

- Normalize:
sed -i 's/\r$//' Dockerfile

Step B — Make sure the host code has the fixed pagination

- Check import and paginate usage (use -E for regex alternation):
grep -n 'from sqlalchemy import select' src/routes/scraping.py
grep -nE 'query.paginate|db.paginate' src/routes/scraping.py
Expected:
- The first command prints a line with the select import.
- The second prints only db.paginate lines (no query.paginate). If it shows query.paginate, your
working tree isn’t updated—do:
git fetch origin && git reset --hard origin/main

Step C — Rebuild image without cache and restart

- Build fresh:
docker compose -f docker-compose.production.yml build --no-cache hvac-scraper
- Start:
docker compose -f docker-compose.production.yml up -d

Step D — Verify the code inside the running container

- Confirm the import and db.paginate are present:
docker exec -it hvac-scraper sh -lc "grep -n 'from sqlalchemy import select' /app/src/routes/
scraping.py; grep -nE 'query\.paginate|db\.paginate' /app/src/routes/scraping.py"
Expected: select import present; only db.paginate lines, no query.paginate.

Step E — Test API quickly

- Log in and store cookie:
curl -c cookies.txt -s -X POST http://127.0.0.1:5001/login -H 'Content-Type: application/json' -d
'{"username":"admin","password":"YOUR_PASSWORD"}' -i
- List jobs:
curl -b cookies.txt -i http://127.0.0.1:5001/api/scraping/jobs
Expected: HTTP/1.1 200 with success true; the UI should stop showing “API Fail”.

If you still see 500:

- Turn on DEBUG to see the exact error:
sed -i 's/^DEBUG=.*/DEBUG=True/' .env
docker compose -f docker-compose.production.yml up -d
curl -b cookies.txt -s -i http://127.0.0.1:5001/api/scraping/jobs
docker compose -f docker-compose.production.yml logs -f hvac-scraper  (Ctrl+C to stop)
Share the first error line; I’ll give the one-line fix. Then set DEBUG=False and restart.

Why this resolves it

- The conflict markers in Dockerfile prevented a fresh image from building, so the container kept
running the old code with Model.query.paginate → 500. Overwriting Dockerfile and building with
--no-cache guarantees the container has the fixed code. The grep checks confirm the right code is in
both host and container.

user
i want the repo to stay current. Give me a copy and paste version that I can put in the Dockerfile on
github and then import to the server

codex
Here’s a clean, copy‑paste Dockerfile you can commit to GitHub. It uses Python 3.11, installs Google
Chrome via a signed keyring (no apt‑key), and keeps everything else the same.

Copy this into Dockerfile at the repo root

FROM python:3.11-slim

# Install system dependencies

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome with signed repository key (no apt-key)

RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/
keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://
dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory

WORKDIR /app

# Install Python dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code

COPY . .

# Create necessary directories

RUN mkdir -p src/database reports

# Environment

ENV PYTHONPATH=/app
ENV FLASK_APP=src/main.py
ENV FLASK_ENV=production

# Security: non-root user

RUN useradd -m -u 1000 hvacuser && chown -R hvacuser:hvacuser /app
USER hvacuser

# Expose port

EXPOSE 5000

# Health check

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/login || exit 1

# Start application

CMD ["python", "src/main.py"]
