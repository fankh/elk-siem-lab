#!/bin/bash
# Full verification test suite for ELK SIEM Lab
# Run inside the 'tester' container: docker exec tester bash /lab/tools/test-all.sh

ES_URL="http://elasticsearch:9200"
PASS=0
FAIL=0

check() {
    local name="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ] || [ "$expected" = "ANY" -a -n "$actual" ]; then
        echo "  [PASS] $name: $actual"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $name: expected=$expected actual=$actual"
        FAIL=$((FAIL + 1))
    fi
}

check_range() {
    local name="$1" min="$2" max="$3" actual="$4"
    if [ "$actual" -ge "$min" ] 2>/dev/null && [ "$actual" -le "$max" ] 2>/dev/null; then
        echo "  [PASS] $name: $actual (range: $min~$max)"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $name: $actual (expected: $min~$max)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=========================================="
echo "  ELK SIEM Lab - Full Test Suite"
echo "=========================================="
echo ""

# --- 1교시: 로그 수집 ---
echo "=== 1교시: 로그 수집 파이프라인 ==="

status=$(curl -s "$ES_URL/_cluster/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
check "ES Cluster Health" "ANY" "$status"

for idx in web sysmon suricata; do
    count=$(curl -s "$ES_URL/security-${idx}-*/_count" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
    case $idx in
        web)      check_range "security-web docs" 600 650 "$count" ;;
        sysmon)   check_range "security-sysmon docs" 220 240 "$count" ;;
        suricata) check_range "security-suricata docs" 140 160 "$count" ;;
    esac
done

echo ""

# --- 2교시: 인제스트 및 정규화 ---
echo "=== 2교시: 인제스트 및 정규화 ==="

for field in source.ip url.path http.response.status_code http.request.method user_agent.original; do
    val=$(curl -s "$ES_URL/security-web-*/_search?size=1" | python3 -c "
import sys, json
hit = json.load(sys.stdin)['hits']['hits'][0]['_source']
print(hit.get('$field', ''))" 2>/dev/null)
    check "Grok field: $field" "ANY" "$val"
done

for field in process.executable process.command_line user.name; do
    val=$(curl -s "$ES_URL/security-sysmon-*/_search?size=1" | python3 -c "
import sys, json
hit = json.load(sys.stdin)['hits']['hits'][0]['_source']
print(hit.get('$field', ''))" 2>/dev/null)
    check "Sysmon ECS: $field" "ANY" "$val"
done

for field in source.ip destination.ip network.transport; do
    val=$(curl -s "$ES_URL/security-suricata-*/_search?size=1" | python3 -c "
import sys, json
hit = json.load(sys.stdin)['hits']['hits'][0]['_source']
print(hit.get('$field', ''))" 2>/dev/null)
    check "Suricata ECS: $field" "ANY" "$val"
done

echo ""

# --- 3교시: 이상 징후 분석 ---
echo "=== 3교시: 이상 징후 분석 ==="

for tag in sqli xss path_traversal; do
    count=$(curl -s "$ES_URL/security-web-*/_count" -H 'Content-Type: application/json' \
      -d "{\"query\":{\"bool\":{\"filter\":[{\"term\":{\"tags\":\"$tag\"}}]}}}" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
    case $tag in
        sqli)           check_range "SQLi tagged" 5 15 "$count" ;;
        xss)            check_range "XSS tagged" 3 10 "$count" ;;
        path_traversal) check_range "PathTraversal tagged" 2 5 "$count" ;;
    esac
done

bf=$(curl -s "$ES_URL/security-web-*/_count" -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"must":[{"term":{"http.response.status_code":401}},{"wildcard":{"url.path":"*login*"}}]}}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
check_range "Brute-force (401+login)" 80 100 "$bf"

susp=$(curl -s "$ES_URL/security-sysmon-*/_count" -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"suspicious"}}]}}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
check_range "Sysmon suspicious" 20 35 "$susp"

alerts=$(curl -s "$ES_URL/security-suricata-*/_count" -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"event_type":"alert"}}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
check_range "Suricata IDS alerts" 40 55 "$alerts"

echo ""

# --- 4교시: Kibana ---
echo "=== 4교시: Kibana 대시보드 ==="

kb_status=$(curl -s http://kibana:5601/api/status | python3 -c "
import sys, json; print(json.load(sys.stdin)['status']['overall']['level'])" 2>/dev/null)
check "Kibana status" "available" "$kb_status"

echo ""

# --- 5교시: Sigma Rule ---
echo "=== 5교시: Sigma Rule ==="

sigma_ver=$(sigma version 2>/dev/null | head -1)
check "sigma-cli installed" "ANY" "$sigma_ver"

for rule in /lab/sigma-rules/*.yml; do
    name=$(basename "$rule")
    result=$(sigma convert -t lucene --without-pipeline "$rule" 2>&1 | tail -1)
    if echo "$result" | grep -q "contains\|OR\|AND\|\*\|uri\|query"; then
        echo "  [PASS] Sigma convert: $name"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] Sigma convert: $name → $result"
        FAIL=$((FAIL + 1))
    fi
done

echo ""

# --- 6교시: 종합 관제 ---
echo "=== 6교시: 종합 관제 ==="

total_attack=$(curl -s "$ES_URL/security-web-*/_count" -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"attack"}}]}}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null)
check_range "Total attack-tagged events" 10 25 "$total_attack"

top_ip=$(curl -s "$ES_URL/security-web-*/_search" -H 'Content-Type: application/json' \
  -d '{"size":0,"query":{"bool":{"filter":[{"terms":{"tags":["sqli","xss","path_traversal"]}}]}},"aggs":{"top":{"terms":{"field":"source.ip.keyword","size":1}}}}' | python3 -c "
import sys, json
b = json.load(sys.stdin)['aggregations']['top']['buckets']
print(b[0]['key'] if b else '')" 2>/dev/null)
check "Top attack IP identified" "ANY" "$top_ip"

top_sig=$(curl -s "$ES_URL/security-suricata-*/_search" -H 'Content-Type: application/json' \
  -d '{"size":0,"query":{"term":{"event_type":"alert"}},"aggs":{"top":{"terms":{"field":"rule.name.keyword","size":1}}}}' | python3 -c "
import sys, json
b = json.load(sys.stdin)['aggregations']['top']['buckets']
print(b[0]['key'] if b else '')" 2>/dev/null)
check "Top IDS signature" "ANY" "$top_sig"

echo ""
echo "=========================================="
echo "  Results: PASS=$PASS  FAIL=$FAIL"
echo "=========================================="

if [ "$FAIL" -eq 0 ]; then
    echo "  ALL TESTS PASSED!"
else
    echo "  $FAIL test(s) failed. Check above for details."
fi
