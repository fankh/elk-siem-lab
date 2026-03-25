FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Sigma CLI + ES backend
RUN pip install --no-cache-dir \
    sigma-cli \
    pySigma-backend-elasticsearch \
    requests

WORKDIR /lab

# Copy sigma rules and scripts
COPY sigma-rules/ /lab/sigma-rules/
COPY scripts/ /lab/scripts/

# Verify installation
RUN sigma version && echo "Sigma CLI installed successfully"

CMD ["tail", "-f", "/dev/null"]
