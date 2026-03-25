# ELK SIEM Lab

ELK Stack 기반 보안 관제(SIEM) 실습 환경입니다. Docker Compose로 Elasticsearch, Kibana, Logstash, Filebeat를 구성하고, 샘플 공격 로그와 Sigma Rule을 활용하여 실시간 위협 탐지를 학습합니다.

## 교육과정 연계

| 항목 | 내용 |
|------|------|
| 과정명 | AI-SIEM 관제 실습 |
| 형태 | Docker 기반 실습 중심 (6교시, 각 50분) |
| 기술 스택 | Elasticsearch 8.12, Kibana 8.12, Logstash 8.12, Filebeat 8.12, Sigma |

---

## 아키텍처

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  sample-logs │     │   Filebeat   │     │   Logstash   │
│              │────▶│  (수집기)     │────▶│  (파싱/변환)  │
│ web-access   │     │  port: -     │     │  port: 5044  │
│ sysmon       │     └──────────────┘     └──────┬───────┘
│ suricata     │                                  │
└──────────────┘                                  ▼
                                          ┌──────────────┐
                                          │Elasticsearch │
┌──────────────┐                          │  (저장/검색)  │
│   Kibana     │◀─────────────────────────│  port: 9200  │
│  (시각화)     │                          └──────────────┘
│  port: 5601  │
└──────────────┘

인덱스:
  security-web-YYYY.MM.dd       ← 웹 로그 (617건)
  security-sysmon-YYYY.MM.dd    ← Sysmon 이벤트 (229건)
  security-suricata-YYYY.MM.dd  ← IDS 알림 (149건)
```

---

## Quick Start

```bash
# 1. 클론
git clone https://github.com/fankh/elk-siem-lab.git
cd elk-siem-lab

# 2. ELK Stack 시작 (첫 실행 시 이미지 다운로드 ~5분)
docker-compose up -d

# 3. 상태 확인 (ES가 healthy 될 때까지 ~60초)
docker exec -it tools curl http://elasticsearch:9200/_cluster/health?pretty
# Windows 호스트에서: curl.exe http://localhost:9200/_cluster/health?pretty

# 4. 인덱스 확인 (Logstash 처리 후 ~90초)
docker exec -it tools curl http://elasticsearch:9200/_cat/indices/security-*?v
# Windows 호스트에서: curl.exe http://localhost:9200/_cat/indices/security-*?v

# 5. Kibana 접속
# http://localhost:5601
```

### CLI 실행 환경 안내

본 문서의 명령어는 **3가지 방법**으로 실행할 수 있습니다:

#### 방법 1: tools 컨테이너 (권장 — 모든 OS)

```bash
# tools 컨테이너 접속 (curl, python3, sigma, jq 사전 설치됨)
docker exec -it tools bash

# 컨테이너 내부에서는 ES를 elasticsearch:9200 으로 접근
curl http://elasticsearch:9200/_cluster/health?pretty
curl http://elasticsearch:9200/_cat/indices/security-*?v

# sigma 변환
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml

# 나가기
exit
```

> **참고**: tools 컨테이너 내부에서는 `localhost` 대신 `elasticsearch`, `kibana` 사용

#### 방법 2: 호스트 터미널 (macOS / Linux)

```bash
# 호스트에서 localhost로 접근
curl http://localhost:9200/_cluster/health?pretty
curl http://localhost:9200/_cat/indices/security-*?v
```

#### 방법 3: 호스트 터미널 (Windows PowerShell)

```powershell
# PowerShell에서 curl 대신 Invoke-WebRequest 사용
Invoke-WebRequest -Uri "http://localhost:9200/_cluster/health?pretty" | Select-Object -ExpandProperty Content

# 또는 curl.exe (Windows 10+ 내장)
curl.exe http://localhost:9200/_cluster/health?pretty
curl.exe http://localhost:9200/_cat/indices/security-*?v

# python3 대신 python 사용 (Windows)
curl.exe -s http://localhost:9200/security-web-*/_count | python -c "import sys,json; print(json.load(sys.stdin)['count'])"
```

#### 방법 4: 브라우저 직접 확인 (가장 간편)

| 확인 항목 | 브라우저 URL |
|---------|-----------|
| ES 상태 | http://localhost:9200/_cluster/health?pretty |
| ES 버전 | http://localhost:9200?pretty |
| 인덱스 목록 | http://localhost:9200/_cat/indices?v |
| 웹 로그 수 | http://localhost:9200/security-web-*/_count?pretty |
| Kibana | http://localhost:5601 |

### 명령어 환경별 대응표

| 작업 | tools 컨테이너 | macOS/Linux | Windows PowerShell | 브라우저 |
|------|:-----------:|:----------:|:-----------------:|:------:|
| ES 상태 확인 | `curl elasticsearch:9200/_cluster/health` | `curl localhost:9200/_cluster/health` | `curl.exe localhost:9200/_cluster/health` | localhost:9200/_cluster/health |
| 인덱스 목록 | `curl elasticsearch:9200/_cat/indices?v` | `curl localhost:9200/_cat/indices?v` | `curl.exe localhost:9200/_cat/indices?v` | localhost:9200/_cat/indices?v |
| 문서 수 확인 | `curl elasticsearch:9200/security-web-*/_count` | `curl localhost:9200/security-web-*/_count` | `curl.exe localhost:9200/security-web-*/_count` | localhost:9200/security-web-*/_count |
| Sigma 변환 | `sigma convert -t lucene ...` | `sigma convert ...` (pip 설치 필요) | `docker exec tools sigma convert ...` | - |
| Kibana 접속 | - | - | - | localhost:5601 |

### 포트 정보

| 서비스 | 포트 | URL | 용도 |
|--------|------|-----|------|
| Elasticsearch | 9200 | http://localhost:9200 | 로그 저장/검색 API |
| Kibana | 5601 | http://localhost:5601 | 대시보드/시각화 UI |
| Logstash | 5044 | - | Beats 입력 (내부) |

### 컨테이너 접속 방법

각 컨테이너에 접속하여 내부 파일 확인, 로그 조회, 디버깅을 수행할 수 있습니다.

#### elasticsearch 컨테이너

```bash
# 접속
docker exec -it elasticsearch bash

# 내부 주요 경로
/usr/share/elasticsearch/config/elasticsearch.yml   # 메인 설정
/usr/share/elasticsearch/config/jvm.options          # JVM 메모리
/usr/share/elasticsearch/data/                       # 인덱스 데이터
/usr/share/elasticsearch/logs/                       # ES 로그

# 내부에서 클러스터 상태 확인
curl -s http://localhost:9200/_cluster/health?pretty
curl -s http://localhost:9200/_cat/indices/security-*?v

# 파일 읽기
cat /usr/share/elasticsearch/config/elasticsearch.yml
```

#### kibana 컨테이너

```bash
# 접속
docker exec -it kibana bash

# 내부 주요 경로
/usr/share/kibana/config/kibana.yml   # 메인 설정
/usr/share/kibana/data/               # Kibana 데이터
/usr/share/kibana/logs/               # Kibana 로그

# 내부에서 상태 확인
curl -s http://localhost:5601/api/status | head -20

# 파일 읽기
cat /usr/share/kibana/config/kibana.yml
```

#### logstash 컨테이너

```bash
# 접속
docker exec -it logstash bash

# 내부 주요 경로
/usr/share/logstash/pipeline/          # 파이프라인 설정 (호스트에서 마운트)
/usr/share/logstash/pipeline/web-access.conf
/usr/share/logstash/pipeline/sysmon.conf
/usr/share/logstash/pipeline/suricata.conf
/usr/share/logstash/config/logstash.yml  # 메인 설정
/var/log/sample/                         # 샘플 로그 (호스트에서 마운트)

# 파이프라인 설정 읽기
cat /usr/share/logstash/pipeline/web-access.conf
cat /usr/share/logstash/pipeline/sysmon.conf
cat /usr/share/logstash/pipeline/suricata.conf

# 샘플 로그 확인
head -5 /var/log/sample/web-access.log
head -5 /var/log/sample/sysmon.json
head -5 /var/log/sample/suricata-eve.json

# 파이프라인 상태 확인
curl -s http://localhost:9600/_node/stats?pretty | head -40
```

#### filebeat 컨테이너

```bash
# 접속
docker exec -it filebeat bash

# 내부 주요 경로
/usr/share/filebeat/filebeat.yml       # 메인 설정 (호스트에서 마운트)
/usr/share/filebeat/data/              # Filebeat 레지스트리 (수집 상태)
/usr/share/filebeat/logs/              # Filebeat 로그
/var/log/sample/                       # 샘플 로그 (호스트에서 마운트)
/var/log/sample/web-access.log
/var/log/sample/sysmon.json
/var/log/sample/suricata-eve.json

# 설정 파일 읽기
cat /usr/share/filebeat/filebeat.yml

# 샘플 로그 파일 확인 (줄 수, 파일 크기)
wc -l /var/log/sample/web-access.log
wc -l /var/log/sample/sysmon.json
wc -l /var/log/sample/suricata-eve.json

# 로그 원본 읽기
head -10 /var/log/sample/web-access.log
head -3 /var/log/sample/sysmon.json
head -3 /var/log/sample/suricata-eve.json

# 수집 레지스트리 확인 (어디까지 읽었는지)
cat /usr/share/filebeat/data/registry/filebeat/log.json | head -20

# 설정 파일 권한 수정 (Filebeat는 소유자만 쓰기 가능해야 함)
chmod go-w /usr/share/filebeat/filebeat.yml

# 설정 검증
filebeat test config
filebeat test output
```

#### tools 컨테이너 (권장 CLI 환경)

```bash
# 접속
docker exec -it tools bash

# 내부 주요 경로
/lab/sigma-rules/                      # Sigma 탐지 룰 (호스트에서 마운트)
/lab/scripts/                          # 스크립트 (호스트에서 마운트)
/lab/sample-logs/                      # 샘플 로그 (호스트에서 마운트)

# 사전 설치 도구: curl, python3, sigma, jq

# ES 접근 (Docker 내부 네트워크 — localhost 대신 elasticsearch 사용)
curl http://elasticsearch:9200/_cluster/health?pretty
curl http://elasticsearch:9200/_cat/indices/security-*?v

# Sigma 룰 읽기/변환
cat /lab/sigma-rules/sqli-detection.yml
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml

# 샘플 로그 읽기
head -10 /lab/sample-logs/web-access.log
head -3 /lab/sample-logs/sysmon.json
head -3 /lab/sample-logs/suricata-eve.json
```

#### tester 컨테이너 (자동 검증용)

```bash
# 접속 (test 프로파일이므로 별도 실행 필요)
docker-compose --profile test run --rm tester bash

# 또는 자동 테스트 실행
docker-compose --profile test run --rm tester
```

#### 컨테이너 접속 요약표

| 컨테이너 | 접속 명령 | 설치된 도구 | ES 접근 주소 |
|----------|----------|-----------|-------------|
| **elasticsearch** | `docker exec -it elasticsearch bash` | curl | `localhost:9200` |
| **kibana** | `docker exec -it kibana bash` | curl, node | `elasticsearch:9200` |
| **logstash** | `docker exec -it logstash bash` | curl | `elasticsearch:9200` |
| **filebeat** | `docker exec -it filebeat bash` | filebeat | `logstash:5044` |
| **tools** (권장) | `docker exec -it tools bash` | curl, python3, sigma, jq | `elasticsearch:9200` |
| **tester** | `docker-compose --profile test run --rm tester bash` | curl, sigma | `elasticsearch:9200` |

> **참고**: Docker 내부 네트워크에서는 `localhost` 대신 컨테이너 이름(`elasticsearch`, `kibana`, `logstash`)을 호스트명으로 사용합니다.

### 환경 설정 (.env)

```bash
ELASTIC_VERSION=8.12.0    # ELK 버전
ES_JAVA_OPTS=-Xms2g -Xmx2g  # ES 메모리 (최소 2GB)
```

---

## 단계별 학습 가이드

처음 접하는 수강생을 위한 단계별 학습 경로입니다. 각 단계를 순서대로 진행하세요.

### Step 1: 환경 구성 및 데이터 확인 (1교시)

**목표**: ELK Stack이 정상 동작하고 로그가 수집되었는지 확인

```bash
# 1-1. 저장소 클론 + ELK 시작
git clone https://github.com/fankh/elk-siem-lab.git
cd elk-siem-lab
docker-compose up -d

# 1-2. ~90초 대기 후 상태 확인
# tools 컨테이너에서 실행 (권장):
docker exec -it tools curl -s http://elasticsearch:9200/_cluster/health?pretty | grep status
# Windows 호스트에서: curl.exe -s http://localhost:9200/_cluster/health?pretty | findstr status
# 기대: "status" : "yellow"

# 1-3. 인덱스 3개 생성 확인
docker exec -it tools curl -s http://elasticsearch:9200/_cat/indices/security-*?v
# Windows 호스트에서: curl.exe -s http://localhost:9200/_cat/indices/security-*?v
# 기대: security-web-*, security-sysmon-*, security-suricata-*

# 1-4. 문서 수 확인
docker exec -it tools curl -s http://elasticsearch:9200/security-web-*/_count?pretty
# Windows 호스트에서: curl.exe -s http://localhost:9200/security-web-*/_count?pretty
# 기대: 617건
```

**확인 포인트:**
- [ ] ES status: yellow 또는 green
- [ ] 인덱스 3개 존재
- [ ] security-web ~617, security-sysmon ~229, security-suricata ~149

**다음 단계로 넘어가는 기준**: 인덱스 3개 모두 생성, 문서 수 확인 완료

---

### Step 2: 로그 파싱 결과 확인 (2교시)

**목표**: Grok/ECS로 파싱된 필드를 Kibana에서 확인

```bash
# tools 컨테이너에서 실행 (권장): docker exec -it tools bash
# Windows 호스트에서는 curl → curl.exe, elasticsearch → localhost 로 변경

# 2-1. 웹 로그 샘플 1건 확인 (파싱된 필드)
curl -s 'http://elasticsearch:9200/security-web-*/_search?size=1&pretty' | head -40
# source.ip, url.path, http.response.status_code 등 필드 확인

# 2-2. Sysmon ECS 매핑 확인
curl -s 'http://elasticsearch:9200/security-sysmon-*/_search?size=1&pretty' | head -30
# process.executable, process.command_line, user.name 필드 확인

# 2-3. Suricata 이벤트 확인
curl -s 'http://elasticsearch:9200/security-suricata-*/_search?size=1&pretty' | head -30
# source.ip, destination.ip, rule.name, event_type 필드 확인
```

**Kibana에서 확인:**
1. http://localhost:5601 접속
2. **Stack Management** → **Data Views** → **Create**: `security-*`, `@timestamp`
3. **Discover** → `security-*` 선택 → 필드 추가: `source.ip`, `url.path`, `tags`
4. 문서 펼쳐서 구조화된 필드 확인

**확인 포인트:**
- [ ] source.ip, url.path 등 ECS 필드가 정상 파싱됨
- [ ] Sysmon: process.executable, process.command_line 존재
- [ ] Kibana Discover에서 로그 조회 가능

**다음 단계로 넘어가는 기준**: Kibana Discover에서 3종 로그 모두 조회 가능

---

### Step 3: 공격 로그 검색 (3교시)

**목표**: KQL로 4종 공격 패턴을 검색하고 건수 확인

**Kibana Discover에서 KQL 쿼리 실행** (하나씩 순서대로):

```
# 3-1. SQL Injection (security-web-*)
tags: sqli
→ 기대: 9건. user_agent에 sqlmap 확인

# 3-2. Brute-force
http.response.status_code: 401 AND url.path: *login*
→ 기대: 95건. 동일 IP(198.51.100.77)에서 2초 간격

# 3-3. XSS
tags: xss
→ 기대: 5건. url.path에 <script>, onerror 패턴

# 3-4. Path Traversal
tags: path_traversal
→ 기대: 3건. ../../../etc/passwd 시도

# 3-5. Sysmon 의심 프로세스 (Data View → security-sysmon-*)
tags: suspicious
→ 기대: 29건. powershell -enc, certutil, C2 연결

# 3-6. Suricata IDS 알림 (Data View → security-suricata-*)
event_type: alert
→ 기대: 49건. 포트 스캔 30건, 공격 시그니처 19건

# 3-7. 상관 분석 — 동일 IP 추적 (Data View → security-*)
source.ip: 203.0.113.42
→ 웹 공격 + IDS 알림이 같은 IP에서 발생 확인
```

**확인 포인트:**
- [ ] SQLi 9건, XSS 5건, Brute-force 95건, Path Traversal 3건
- [ ] 공격 IP 3개 식별: `203.0.113.42`, `198.51.100.77`, `185.220.101.33`
- [ ] 상관 분석: 동일 IP가 웹+IDS에서 동시 탐지

**다음 단계로 넘어가는 기준**: 모든 공격 유형별 건수 확인, 공격 IP 식별 완료

---

### Step 4: 보안 대시보드 구성 (4교시)

**목표**: Kibana Lens/Maps로 보안 대시보드 4개 패널 완성

**패널 1 — Error Rate Timeline (Area Chart):**
1. **Visualize Library** → **Create** → **Lens** → **Area**
2. Data view: `security-web-*`
3. X축: `@timestamp` (Date histogram)
4. Y축: Count, Filter: `http.response.status_code >= 400`
5. Save → "Error Rate Timeline"

**패널 2 — Top 10 Attack IP (Bar Chart):**
1. **Lens** → **Bar vertical**
2. X축: `source.ip.keyword` (Top values, 10개)
3. Y축: Count
4. Filter: `tags: attack OR tags: sqli OR tags: xss`
5. Save → "Top 10 Attack IPs"

**패널 3 — HTTP 상태 분포 (Pie Chart):**
1. **Lens** → **Pie**
2. Slice by: `http.response.status_code` (Top values)
3. Save → "HTTP Status Distribution"

**패널 4 — GeoIP 위협 맵:**
1. **Analytics** → **Maps** → **Create map**
2. **Add layer** → **Documents** → `security-web-*`
3. Geospatial field: `source.geo.location`
4. Save → "Threat Map"

**대시보드 조합:**
1. **Dashboard** → **Create** → **Add from library** → 4개 패널 추가
2. 레이아웃 배치:
```
┌────────────────────────────────────────────┐
│  Error Rate Timeline (전체 폭)              │
├─────────────────────┬──────────────────────┤
│  Top 10 IPs (Bar)   │  HTTP Status (Pie)    │
├─────────────────────┴──────────────────────┤
│  GeoIP Threat Map (전체 폭)                 │
└────────────────────────────────────────────┘
```
3. Auto-refresh: 30초, Save → "SIEM Security Dashboard"

**확인 포인트:**
- [ ] Error Rate에 Brute-force 시간대 spike 확인
- [ ] Top IP에 공격 IP 3개 표시
- [ ] 지도에 공격 출발지 점/히트맵 표시
- [ ] IP 클릭 시 글로벌 필터 적용 (드릴다운)

**다음 단계로 넘어가는 기준**: 4개 패널 대시보드 완성, 드릴다운 동작 확인

---

### Step 5: Sigma Rule 변환 및 실행 (5교시)

**목표**: Sigma Rule을 ES 쿼리로 변환하고 탐지 확인

```bash
# 5-1. tools 컨테이너 접속
docker exec -it tools bash

# 5-2. Sigma Rule 확인
cat /lab/sigma-rules/sqli-detection.yml
# title, logsource, detection, level, tags 구조 확인

# 5-3. ES Lucene 쿼리로 변환
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml
# 출력: cs-uri-query:(*UNION SELECT* OR *1=1* OR *DROP TABLE* ...)

# 5-4. 전체 룰 변환 테스트
for rule in /lab/sigma-rules/*.yml; do
    echo "=== $(basename $rule) ==="
    sigma convert -t lucene --without-pipeline "$rule"
    echo ""
done
# 4개 룰 모두 변환 성공 확인

# 5-5. 컨테이너 나가기
exit
```

**Kibana Dev Tools에서 실행:**
1. http://localhost:5601 → **Dev Tools**
2. 변환된 쿼리로 검색:
```json
GET security-web-*/_search
{
  "query": {
    "query_string": {
      "query": "cs-uri-query:(*UNION SELECT* OR *1=1* OR *DROP TABLE*)"
    }
  }
}
```
3. 실행 → 탐지 결과 확인

**확인 포인트:**
- [ ] sigma-cli 정상 동작 (4개 룰 변환 성공)
- [ ] 변환된 쿼리가 Kibana에서 실행 가능
- [ ] sqli 룰: 탐지 결과 확인

**다음 단계로 넘어가는 기준**: Sigma Rule → ES 변환 → Kibana 실행 → 탐지 확인 전체 흐름 완료

---

### Step 6: 종합 관제 시나리오 (6교시)

**목표**: 실전 관제 흐름 수행 — 탐지 → 분석 → 대응 → 보고

**시나리오**: 외부 IP에서 다수의 비정상 요청 탐지, Error Rate 급증, IDS 알림 발생

**6-1. 대시보드 모니터링** (5분)
- 4교시에 만든 대시보드에서 Error Spike 시간대 확인
- Top Attack IP 확인

**6-2. IP 드릴다운 분석** (8분)
- 공격 IP 클릭 → Discover에서 상세 로그 확인
- 각 IP의 공격 유형, User-Agent, 상태 코드 분석

**6-3. Kill Chain 매핑** (5분)
```
정찰       → 포트 스캔 (Suricata: nmap)
익스플로잇 → SQLi, XSS (웹 로그: sqlmap)
인증 공격  → Brute-force (401 × 95회)
탐색       → Path Traversal (../etc/passwd)
내부 활동  → 의심 프로세스 + C2 연결 (Sysmon)
```

**6-4. 오탐 식별** (7분)
- 정상 검색 vs 실제 공격 구분
- 핵심: User-Agent, 출발지 IP, 반복 패턴 종합 판단

**6-5. 위험도 산정** (5분)
```
위험도 = 위협(1~5) × 취약성(1~5) × 자산가치(1~5)

SQLi:        5 × 4 × 5 = 100 → Critical
Brute-force: 4 × 3 × 4 = 48  → High
포트 스캔:   2 × 2 × 3 = 12  → Low
```

**6-6. 관제 보고서 작성** (12분)
| 섹션 | 내용 |
|------|------|
| 탐지 개요 | 일시, 탐지 소스, 공격 요약 |
| 공격 분석 | 공격 IP, 유형, 도구(sqlmap), Kill Chain |
| 영향 평가 | 위험도 점수, 성공 여부, 데이터 유출 |
| 대응 조치 | IP 차단, 계정 점검, WAF 설정 |
| 개선 권고 | 입력 검증, Rate Limiting, Sigma 운영 |

**확인 포인트:**
- [ ] 공격 IP 3개 식별 및 전체 활동 추적 완료
- [ ] Kill Chain 5단계 이상 매핑
- [ ] 위험도 산정 (Critical/High/Low 분류)
- [ ] 관제 보고서 5개 섹션 작성 완료

---

### Step 7: 자동 검증 (선택)

전체 환경이 정상인지 한 번에 검증합니다.

```bash
# 자동 테스트 (30개 항목)
docker-compose --profile test run --rm tester

# 기대: 30/30 PASS
```

---

### 학습 완료 체크리스트

| # | 학습 항목 | 확인 |
|---|----------|:----:|
| 1 | ELK Stack Docker 환경 구성 | ☐ |
| 2 | Filebeat → Logstash → ES 파이프라인 이해 | ☐ |
| 3 | Grok 패턴으로 로그 파싱 원리 이해 | ☐ |
| 4 | ECS 필드 매핑 (source.ip, url.path 등) | ☐ |
| 5 | KQL로 SQLi/XSS/Brute-force 검색 | ☐ |
| 6 | Kibana Lens로 Area/Bar/Pie 차트 생성 | ☐ |
| 7 | GeoIP Maps로 공격 출발지 시각화 | ☐ |
| 8 | 보안 대시보드 구성 + 드릴다운 | ☐ |
| 9 | Sigma Rule YAML 구조 이해 | ☐ |
| 10 | sigma-cli로 ES 쿼리 변환 | ☐ |
| 11 | 상관 분석 (동일 IP 교차 추적) | ☐ |
| 12 | Kill Chain 매핑 | ☐ |
| 13 | 오탐 식별 (True Positive vs False Positive) | ☐ |
| 14 | 위험도 산정 (위협 × 취약성 × 자산) | ☐ |
| 15 | 관제 보고서 작성 | ☐ |

---

## 디렉토리 구조

```
elk-siem-lab/
├── docker-compose.yml              # ELK Stack 4개 서비스 정의
├── .env                            # 환경 변수 (버전, 메모리)
│
├── logstash/pipeline/              # Logstash 파이프라인 설정
│   ├── web-access.conf             #   웹 로그 파싱 (Grok + GeoIP + 공격 태깅)
│   ├── sysmon.conf                 #   Sysmon ECS 매핑 + 의심 프로세스 태깅
│   └── suricata.conf               #   Suricata IDS 알림 파싱 + 공격 분류
│
├── filebeat/
│   └── filebeat.yml                # 3종 로그 수집 설정
│
├── sample-logs/                    # 사전 생성된 샘플 로그 (공격 포함)
│   ├── web-access.log              #   Apache Combined 형식 (617건)
│   ├── sysmon.json                 #   Windows Sysmon JSON (229건)
│   └── suricata-eve.json           #   Suricata eve.json (149건)
│
├── sigma-rules/                    # Sigma 탐지 룰 (YAML)
│   ├── sqli-detection.yml          #   SQL Injection (T1190)
│   ├── xss-detection.yml           #   Cross-Site Scripting (T1189)
│   ├── bruteforce-detection.yml    #   Brute-force Login (T1110)
│   └── path-traversal.yml          #   Path Traversal (T1083)
│
├── kibana/
│   └── dashboards.ndjson           # 보안 대시보드 (Kibana import용)
│
├── scripts/
│   ├── generate-attack-logs.py     # 공격 로그 재생성 스크립트
│   └── import-dashboards.sh        # Kibana 인덱스 패턴 + 대시보드 자동 설정
│
└── labs/                           # 교시별 실습 가이드 (Korean)
    ├── 0교시_실습환경_설치가이드.md   #   사전 준비: Docker 기반 환경 구성
    ├── 0교시_ELK_수동설치_가이드.md   #   사전 준비: Plain Linux 수동 설치 (심화)
    ├── 1교시_로그수집_파이프라인.md   #   1교시: 로그 수집 파이프라인
    ├── 2교시_인제스트_정규화.md      #   2교시: 인제스트 및 정규화
    ├── 3교시_이상징후_분석.md        #   3교시: 이상 징후 분석
    ├── 4교시_Kibana_대시보드.md     #   4교시: Kibana 대시보드 구성
    ├── 5교시_Sigma_Rule.md         #   5교시: Sigma Rule 작성
    └── 6교시_종합관제_실습.md        #   6교시: 종합 관제 실습
```

---

## 샘플 로그 상세

### 웹 로그 (web-access.log) — 617건

Apache Combined Log Format. 정상 트래픽 + 4종 공격 패턴 포함.

| 공격 유형 | 건수 | 공격 IP | 탐지 태그 | 예시 페이로드 |
|----------|:----:|---------|----------|-------------|
| SQL Injection | 9 | 203.0.113.42, 198.51.100.77 | `sqli` | `' OR '1'='1'--`, `UNION SELECT`, `SLEEP(5)` |
| XSS | 5 | 203.0.113.42, 198.51.100.77 | `xss` | `<script>alert('XSS')</script>`, `onerror=alert(1)` |
| Brute-force | 95 | 198.51.100.77 | - | POST /login → 401 반복 (2초 간격) |
| Path Traversal | 3 | 203.0.113.42 | `path_traversal` | `../../../etc/passwd`, `..%2F..%2Fetc%2Fshadow` |
| 정상 트래픽 | 500 | 10.0.x.x, 192.168.x.x | - | GET /, /api/users, /css/style.css |

### Sysmon 로그 (sysmon.json) — 229건

Windows Sysmon 이벤트 (JSON). EventID 1(프로세스 생성), 3(네트워크 연결), 11(파일 생성).

| 이벤트 유형 | 건수 | 탐지 태그 | 의심 패턴 |
|------------|:----:|----------|----------|
| 정상 프로세스 (EventID 1) | 200 | - | svchost, chrome, notepad, python |
| 의심 프로세스 (EventID 1) | 20 | `suspicious`, `execution` | `powershell -enc`, `certutil -urlcache`, `cmd /c whoami` |
| C2 네트워크 (EventID 3) | 9 | `suspicious`, `c2` | 외부 IP:4444/5555/8888 연결 |

### Suricata 로그 (suricata-eve.json) — 149건

Suricata IDS eve.json 포맷. flow + alert 이벤트.

| 이벤트 유형 | 건수 | 탐지 태그 | 시그니처 |
|------------|:----:|----------|---------|
| 정상 flow | 100 | - | TCP 80/443/8080 |
| 포트 스캔 | 30 | `attack`, `reconnaissance` | `GPL SCAN nmap TCP` |
| 웹 공격 | ~11 | `attack` | `SQL Injection`, `XSS`, `Path Traversal` |
| 악성코드/익스플로잇 | ~9 | `attack`, `malware` | `Trojan C2 Activity`, `CVE-2024 RCE` |

---

## Logstash 파이프라인 상세

### 이벤트 라우팅

각 conf 파일은 `tags` 기반으로 이벤트를 라우팅합니다 (단일 파이프라인, 조건부 처리):

```
web-access.log  → tags: ["web"]      → filter(web)      → security-web-*
sysmon.json     → tags: ["sysmon"]   → filter(sysmon)   → security-sysmon-*
suricata.json   → tags: ["suricata"] → filter(suricata) → security-suricata-*
```

### web-access.conf 처리 흐름

```
Input (file) → Grok 파싱 → Date 변환 → GeoIP 보강 → UserAgent 파싱
            → URL Decode (copy + urldecode)
            → 공격 패턴 매칭 (regex → tag 추가)
              ├── SQLi: union select, or 1=1, drop table, sleep(), '--
              ├── XSS: <script, javascript:, onerror=, onload=
              └── Path Traversal: ../, ..%2f, ..%5c
            → Output (Elasticsearch)
```

### ECS 필드 매핑

| 소스 | 원본 필드 | ECS 필드 |
|------|----------|---------|
| Web | IP (Grok) | `source.ip` |
| Web | URI (Grok) | `url.path` |
| Web | Status (Grok) | `http.response.status_code` |
| Sysmon | `Image` | `process.executable` |
| Sysmon | `CommandLine` | `process.command_line` |
| Sysmon | `ParentImage` | `process.parent.executable` |
| Sysmon | `SourceIp` | `source.ip` |
| Suricata | `src_ip` | `source.ip` |
| Suricata | `dest_ip` | `destination.ip` |
| Suricata | `alert.signature` | `rule.name` |
| Suricata | `alert.severity` | `event.severity` |

---

## Sigma Rules 상세

| 룰 | 파일 | 탐지 키워드 | MITRE | 조건 |
|----|------|-----------|-------|------|
| SQLi | sqli-detection.yml | `UNION SELECT`, `1=1`, `DROP TABLE`, `SLEEP(`, `information_schema` | T1190 | URI에 키워드 포함 |
| XSS | xss-detection.yml | `<script>`, `javascript:`, `onerror=`, `onload=`, `document.cookie` | T1189 | URI에 키워드 포함 |
| Brute-force | bruteforce-detection.yml | `/login`, `/auth`, 401 상태 | T1110 | 5분 내 동일 IP에서 20회 초과 |
| Path Traversal | path-traversal.yml | `../`, `..%2f`, `/etc/passwd`, `.htaccess` | T1083 | URI에 패턴 또는 대상 파일 포함 |

### Sigma → Elasticsearch 변환

```bash
# 설치
pip install sigma-cli pySigma-backend-elasticsearch

# 단일 룰 변환
sigma convert -t lucene --without-pipeline sigma-rules/sqli-detection.yml

# 전체 룰 변환
for rule in sigma-rules/*.yml; do
    echo "=== $(basename $rule) ==="
    sigma convert -t lucene --without-pipeline "$rule"
    echo ""
done

# 변환 결과를 Kibana Dev Tools에서 실행
# POST security-web-*/_search
# { "query": { "query_string": { "query": "cs-uri-query:(*UNION SELECT* OR *1=1*)" } } }
```

---

## 실습 가이드

| 교시 | 실습 | 소요 | 핵심 학습 | 사용 도구 |
|:----:|------|:----:|----------|----------|
| 0-A | [실습 환경 설치 가이드](labs/0교시_실습환경_설치가이드.md) | 사전 | Docker Compose로 ELK 전체 환경 구성 | docker-compose |
| 0-B | [ELK 수동 설치 가이드](labs/0교시_ELK_수동설치_가이드.md) | 사전 | Plain Linux에서 ELK 직접 설치 (심화) | apt, systemctl |
| 1 | [로그 수집 파이프라인](labs/1교시_로그수집_파이프라인.md) | 50분 | Filebeat/Logstash 구성, 이기종 로그 통합 | docker-compose, curl |
| 2 | [인제스트 및 정규화](labs/2교시_인제스트_정규화.md) | 50분 | Grok 패턴, ECS 매핑, GeoIP 보강 | Kibana Discover |
| 3 | [이상 징후 분석](labs/3교시_이상징후_분석.md) | 50분 | KQL 검색, 공격 패턴 식별, 상관 분석 | Kibana Discover, KQL |
| 4 | [Kibana 대시보드](labs/4교시_Kibana_대시보드.md) | 50분 | Lens/TSVB 시각화, GeoIP Map, 드릴다운 | Kibana Dashboard |
| 5 | [Sigma Rule 작성](labs/5교시_Sigma_Rule.md) | 50분 | Sigma YAML 작성, ES 변환, Watcher | sigma-cli, Dev Tools |
| 6 | [종합 관제 실습](labs/6교시_종합관제_실습.md) | 50분 | 실시간 탐지, 오탐 제거, 보고서 작성 | 전체 도구 |

### 실습 파일 경로 (로컬)

```
labs/
├── 0교시_실습환경_설치가이드.md        # 사전 준비: Docker 기반 환경 구성
├── 0교시_ELK_수동설치_가이드.md        # 사전 준비: Plain Linux 수동 설치 (심화)
├── 1교시_로그수집_파이프라인.md         # 1교시: Filebeat → Logstash → ES 파이프라인
├── 2교시_인제스트_정규화.md            # 2교시: Grok 파싱, ECS 매핑, GeoIP
├── 3교시_이상징후_분석.md              # 3교시: KQL 검색, 공격 패턴, 상관 분석
├── 4교시_Kibana_대시보드.md           # 4교시: Lens, TSVB, Maps, 드릴다운
├── 5교시_Sigma_Rule.md               # 5교시: Sigma YAML 작성, ES 변환, Watcher
└── 6교시_종합관제_실습.md              # 6교시: 탐지→분석→대응→보고 전체 흐름
```

---

## 교시별 테스트 가이드

ELK Stack이 실행 중인 상태에서 각 교시별로 아래 명령어로 정상 동작을 확인합니다.

> **실행 환경 안내**: 아래 명령어는 **tools 컨테이너 내부**(`docker exec -it tools bash`) 기준입니다.
> - tools 컨테이너: `curl http://elasticsearch:9200/...`
> - macOS/Linux 호스트: `curl http://localhost:9200/...`
> - Windows 호스트: `curl.exe http://localhost:9200/...`

### 1교시: 로그 수집 파이프라인

```bash
# ELK 시작 (호스트에서 실행)
docker-compose up -d

# tools 컨테이너 접속
docker exec -it tools bash

# Elasticsearch 상태 확인 (~60초 대기)
curl -s http://elasticsearch:9200/_cluster/health?pretty | grep status
# 기대: "status" : "green" 또는 "yellow"

# 인덱스 생성 확인 (Logstash 처리 후 ~90초)
curl -s http://elasticsearch:9200/_cat/indices/security-*?v
# 기대: security-web-*, security-sysmon-*, security-suricata-* 3개 인덱스

# 각 인덱스 문서 수 확인
curl -s http://elasticsearch:9200/security-web-*/_count?pretty
curl -s http://elasticsearch:9200/security-sysmon-*/_count?pretty
curl -s http://elasticsearch:9200/security-suricata-*/_count?pretty
# 기대: Web ~617, Sysmon ~229, Suricata ~149
```

### 2교시: 인제스트 및 정규화

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)

# Grok 파싱 필드 확인 (웹 로그)
curl -s 'http://elasticsearch:9200/security-web-*/_search?size=1' | head -15
# 기대: 5개 필드 모두 값이 있어야 함

# ECS 매핑 확인 (Sysmon)
curl -s 'http://elasticsearch:9200/security-sysmon-*/_search?size=1' | head -15
# 기대: process.executable, process.command_line, user.name 필드 존재

# GeoIP 필드 확인
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"exists":{"field":"source.geo"}},"size":1}' | head -15
# 기대: 0 이상 (외부 IP에 대해 GeoIP 적용)
```

### 3교시: 이상 징후 분석

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)

# SQLi 공격 로그 검색
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"sqli"}}]}},"size":0}' | head -15
# 기대: ~9건

# Brute-force 로그 (401 상태 + /login)
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"must":[{"term":{"http.response.status_code":401}},{"wildcard":{"url.path":"*login*"}}]}},"size":0}' | head -15
# 기대: ~95건

# XSS 공격 로그
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"xss"}}]}},"size":0}' | head -15
# 기대: ~5건

# Path Traversal 공격 로그
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"path_traversal"}}]}},"size":0}' | head -15
# 기대: ~3건

# Sysmon 의심 프로세스
curl -s 'http://elasticsearch:9200/security-sysmon-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"filter":[{"term":{"tags":"suspicious"}}]}},"size":0}' | head -15
# 기대: ~29건

# Suricata 공격 알림
curl -s 'http://elasticsearch:9200/security-suricata-*/_search' -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"event_type":"alert"}},"size":0}' | head -15
# 기대: ~49건
```

### 4교시: Kibana 대시보드

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# Kibana 상태 확인
curl -s http://kibana:5601/api/status | head -15
# 기대: "available"

# 인덱스 패턴 자동 생성 (호스트에서 실행)
# bash scripts/import-dashboards.sh
```

**Kibana에서 수동 확인:**

1. http://localhost:5601 접속
2. **Discover** → `security-*` Data View 생성 → 로그 조회 확인
3. **Visualize** → Lens → Area Chart 생성 (X: @timestamp, Y: Count)
4. **Maps** → `source.geo.location` 필드로 공격 출발지 지도 시각화
5. **Dashboard** → 패널 배치 → 10초 자동 새로고침 설정

### 5교시: Sigma Rule

```bash
# sigma-cli 설치
pip install sigma-cli pySigma-backend-elasticsearch

# SQLi Sigma Rule → ES Query 변환
sigma convert -t lucene --without-pipeline sigma-rules/sqli-detection.yml
# 기대: Elasticsearch bool 쿼리 JSON 출력

# 전체 Sigma Rule 변환 테스트
for rule in sigma-rules/*.yml; do
    echo "=== $(basename $rule) ==="
    sigma convert -t lucene --without-pipeline "$rule" 2>&1 | head -3
    echo ""
done
# 기대: 4개 룰 모두 변환 성공
```

### 6교시: 종합 관제

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)

# 전체 공격 현황 요약
echo "=== SIEM Lab Attack Summary ==="
for tag in sqli xss path_traversal; do
    count=$(curl -s "http://elasticsearch:9200/security-web-*/_count" -H 'Content-Type: application/json' \
      -d "{\"query\":{\"bool\":{\"filter\":[{\"term\":{\"tags\":\"$tag\"}}]}}}")
    echo "  $tag: $count"
done

# Brute-force
bf=$(curl -s 'http://elasticsearch:9200/security-web-*/_count' -H 'Content-Type: application/json' \
  -d '{"query":{"bool":{"must":[{"term":{"http.response.status_code":401}},{"wildcard":{"url.path":"*login*"}}]}}}')
echo "  bruteforce: ${bf}"

# 공격 IP Top 3
echo ""
echo "=== Top Attack IPs ==="
curl -s 'http://elasticsearch:9200/security-web-*/_search' -H 'Content-Type: application/json' \
  -d '{"size":0,"query":{"bool":{"filter":[{"terms":{"tags":["sqli","xss","path_traversal"]}}]}},"aggs":{"top_ips":{"terms":{"field":"source.ip.keyword","size":3}}}}' | head -15

# IDS 시그니처 Top 5
echo ""
echo "=== Top IDS Signatures ==="
curl -s 'http://elasticsearch:9200/security-suricata-*/_search' -H 'Content-Type: application/json' \
  -d '{"size":0,"query":{"term":{"event_type":"alert"}},"aggs":{"sigs":{"terms":{"field":"rule.name.keyword","size":5}}}}' | head -15

echo ""
echo "=== All Tests Complete ==="
```

---

## 검증 완료 결과

아래는 실제 `docker-compose up` 후 검증한 결과입니다 (2026-03-25).

| 항목 | 기대값 | 실측값 | 상태 |
|------|:------:|:------:|:----:|
| ES Cluster Health | yellow | yellow | PASS |
| security-web docs | ~617 | 617 | PASS |
| security-sysmon docs | ~229 | 229 | PASS |
| security-suricata docs | ~149 | 149 | PASS |
| SQLi 탐지 (tag) | ~10 | 9 | PASS |
| XSS 탐지 (tag) | ~5 | 5 | PASS |
| Path Traversal 탐지 (tag) | ~3 | 3 | PASS |
| Brute-force (401+login) | ~95 | 95 | PASS |
| Sysmon suspicious | ~30 | 29 | PASS |
| Suricata IDS alerts | ~50 | 49 | PASS |
| Kibana status | available | available | PASS |
| Grok 필드 파싱 | OK | OK | PASS |
| Sysmon ECS 매핑 | OK | OK | PASS |
| Suricata ECS 매핑 | OK | OK | PASS |

---

## 트러블슈팅

### ES가 시작되지 않는 경우

```bash
# 메모리 부족 확인
docker logs elasticsearch 2>&1 | tail -20

# vm.max_map_count 설정 (Linux)
sudo sysctl -w vm.max_map_count=262144

# .env에서 메모리 줄이기
ES_JAVA_OPTS=-Xms1g -Xmx1g
```

### 인덱스가 생성되지 않는 경우

```bash
# Logstash 로그 확인
docker logs logstash 2>&1 | grep ERROR

# 파이프라인 상태 확인
docker logs logstash 2>&1 | grep "Pipeline started"
# 기대: Pipeline started {"pipeline.id"=>"main"}
```

### Kibana에 데이터가 보이지 않는 경우

```bash
# 인덱스 존재 확인
curl -s http://localhost:9200/_cat/indices/security-*?v

# Data View(인덱스 패턴) 생성
# Kibana → Stack Management → Data Views → Create → "security-*" → @timestamp
```

### 로그를 다시 수집하고 싶은 경우

```bash
# 데이터 초기화 후 재시작
docker-compose down -v
docker-compose up -d
# ~90초 대기 후 인덱스 확인
```

### 샘플 로그 재생성

```bash
python3 scripts/generate-attack-logs.py
# sample-logs/ 디렉토리에 3개 파일 재생성
```

---

## 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Docker | Desktop 4.x | Desktop 4.x 이상 |
| RAM | 8GB | 16GB |
| 디스크 | 10GB 여유 | 20GB 여유 |
| OS | Windows 10, macOS, Linux | - |
| Python | 3.8+ (Sigma 변환용) | 3.10+ |

---

## 종료

```bash
docker-compose down          # 컨테이너 종료 (데이터 유지)
docker-compose down -v       # 컨테이너 + 데이터 완전 삭제
```

---

## 참고 자료

| 리소스 | URL |
|--------|-----|
| Elastic SIEM | https://www.elastic.co/security/siem |
| Sigma Rules (SigmaHQ) | https://github.com/SigmaHQ/sigma |
| Filebeat Docs | https://www.elastic.co/guide/en/beats/filebeat/8.12 |
| Logstash Grok Patterns | https://www.elastic.co/guide/en/logstash/8.12/plugins-filters-grok.html |
| Kibana Lens | https://www.elastic.co/guide/en/kibana/8.12/lens.html |
| ECS (Elastic Common Schema) | https://www.elastic.co/guide/en/ecs/current |
| MITRE ATT&CK | https://attack.mitre.org |
