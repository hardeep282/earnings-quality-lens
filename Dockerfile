

# Earnings Quality Lens: walking-skeleton image (step S1.4).
# Builds Bronze -> Silver -> Gold and the baseline from the CSV inside the image, runs every test as a
# build gate, then serves the Streamlit app on port 8501. Hardening (multi-stage, slimmer deps, scan): Phase 19.
ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Dependencies first: this slow layer is reused from cache until requirements.txt changes.
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# 2. A non-root user owns the project folder and runs everything after this point.
RUN useradd --create-home --uid 10001 appuser && chown appuser:appuser /app

# 3. Project files (the .dockerignore keeps .venv, .git, .env and the local database out).
COPY --chown=appuser:appuser data/raw/ data/raw/
COPY --chown=appuser:appuser sql/ sql/
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser tests/ tests/
COPY --chown=appuser:appuser .streamlit/ .streamlit/
USER appuser

# 4. Build Gold from the fingerprinted CSV, write the baseline, and stop the build if any test fails.
RUN python -m src.pipeline && python -m src.baseline && python -m pytest -q -p no:cacheprovider

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)"]
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]