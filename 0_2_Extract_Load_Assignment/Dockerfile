FROM python:3.13.10-slim

# Copy uv binary from official uv image (multi-stage build pattern)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Set working directory
WORKDIR /app

# Add virtual environment to PATH so we can use installed packages
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first (better layer caching)
COPY "pyproject.toml" "uv.lock" ./
# Install dependencies from lock file (ensures reproducible builds)
RUN apt-get update && apt-get install -y build-essential
RUN uv sync --locked


COPY swap.py swap.py

ENTRYPOINT ["uv", "run", "python", "swap.py"]