#!/bin/bash
# Import Kibana dashboards and index patterns
KIBANA_URL="${KIBANA_URL:-http://kibana:5601}"

echo "=== ELK SIEM Lab Setup ==="

# Wait for Kibana
echo "[1/4] Waiting for Kibana..."
until curl -s "$KIBANA_URL/api/status" | grep -q '"level":"available"'; do
    sleep 5
    echo "  Waiting..."
done
echo "  Kibana is ready!"

# Create index patterns
echo "[2/4] Creating index patterns..."
for pattern in "security-web-*" "security-sysmon-*" "security-suricata-*"; do
    curl -s -X POST "$KIBANA_URL/api/saved_objects/index-pattern" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -d "{\"attributes\":{\"title\":\"$pattern\",\"timeFieldName\":\"@timestamp\"}}" > /dev/null
    echo "  Created: $pattern"
done

# Create combined pattern
curl -s -X POST "$KIBANA_URL/api/saved_objects/index-pattern" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{"attributes":{"title":"security-*","timeFieldName":"@timestamp"}}' > /dev/null
echo "  Created: security-*"

# Import dashboards
echo "[3/4] Importing dashboards..."
if [ -f "kibana/dashboards.ndjson" ]; then
    curl -s -X POST "$KIBANA_URL/api/saved_objects/_import?overwrite=true" \
        -H "kbn-xsrf: true" \
        --form file=@kibana/dashboards.ndjson > /dev/null
    echo "  Dashboards imported!"
else
    echo "  No dashboards.ndjson found, skipping."
fi

echo "[4/4] Verifying..."
curl -s "$KIBANA_URL/api/saved_objects/_find?type=index-pattern" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for obj in data.get('saved_objects', []):
    print(f\"  Index Pattern: {obj['attributes']['title']}\")
" 2>/dev/null

echo ""
echo "=== Setup Complete ==="
echo "Kibana: $KIBANA_URL"
echo "Elasticsearch: http://elasticsearch:9200"
