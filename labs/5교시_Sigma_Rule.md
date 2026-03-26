# 실습 5: Sigma Rule 작성

## 목표

**Sigma Rule** YAML 형식을 이해하고 직접 작성한다.
작성된 룰을 Elasticsearch 쿼리로 변환하여 실제 탐지에 활용한다.


---

## 실습 환경 시작

```bash
# 호스트에서 실행
# ELK Stack 시작 (이미 실행 중이면 생략)
cd elk-siem-lab
docker-compose up -d

# 컨테이너 상태 확인
docker-compose ps
# 기대: elasticsearch, kibana, logstash, filebeat, tools 모두 Up

# tools 컨테이너 접속 (curl, python3, sigma 사용)
docker exec -it tools bash
```

> **CLI 실행 환경**
> | 환경 | 명령 |
> |------|------|
> | **tools 컨테이너 (권장)** | `docker exec -it tools bash` → 내부에서 curl, python3, sigma 사용 |
> | **macOS/Linux** | 호스트 터미널에서 `curl localhost:9200/...` |
> | **Windows PowerShell** | `curl.exe localhost:9200/...` 또는 브라우저 직접 접속 |
> | **브라우저** | http://localhost:9200 (ES) / http://localhost:5601 (Kibana) |

### 컨테이너 접속 및 파일 확인

```bash
# tools 컨테이너 — Sigma 룰 읽기 및 변환 (권장)
docker exec -it tools bash
# Sigma 룰 파일 목록
ls -la /lab/sigma-rules/
# 각 룰 내용 읽기
cat /lab/sigma-rules/sqli-detection.yml
cat /lab/sigma-rules/xss-detection.yml
cat /lab/sigma-rules/bruteforce-detection.yml
cat /lab/sigma-rules/path-traversal.yml
# Sigma 변환 테스트
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml
# 전체 룰 변환
for rule in /lab/sigma-rules/*.yml; do
    echo "=== $(basename $rule) ==="
    sigma convert -t lucene --without-pipeline "$rule"
    echo ""
done
```

```powershell
# 호스트(Windows)에서 — Sigma 룰 파일 직접 읽기
type sigma-rules\sqli-detection.yml
type sigma-rules\xss-detection.yml
type sigma-rules\bruteforce-detection.yml
type sigma-rules\path-traversal.yml
```

---

## 컴포넌트 설치: Sigma CLI

### sigma-cli 설치

Sigma Rule을 SIEM 제품별 쿼리로 변환하는 CLI 도구입니다.

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# Python 가상환경 (권장)
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# tools 컨테이너에는 sigma-cli가 사전 설치되어 있습니다
# 설치 확인
sigma version
# 기대: pySigma version x.x.x

# 미설치 시 수동 설치:
# pip install sigma-cli pySigma-backend-elasticsearch
```

### 주요 패키지

| 패키지 | 역할 |
|--------|------|
| `sigma-cli` | Sigma Rule 파싱 및 변환 CLI |
| `pySigma-backend-elasticsearch` | ES Query DSL 변환 백엔드 |

### sigma-cli 주요 명령어

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# 단일 룰 변환 → ES Query DSL
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml

# 전체 룰 변환
sigma convert -t lucene --without-pipeline /lab/sigma-rules/

# 지원 백엔드 목록
sigma list targets

# 지원 파이프라인 목록
sigma list pipelines
```

### SigmaHQ 커뮤니티 룰셋 (참고)

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# 3000+ 오픈소스 탐지 룰
git clone https://github.com/SigmaHQ/sigma.git

# 웹 공격 룰 확인
ls sigma/rules/web/
# web_sqli.yml, web_xss.yml, web_path_traversal.yml ...
```

### Sigma Rule YAML 구조

```yaml
title: 룰 이름
id: UUID
status: experimental | test | stable
description: 설명
author: 작성자
date: YYYY/MM/DD
logsource:
    category: webserver        # 로그 소스 카테고리
    product: apache            # 제품
detection:
    selection:
        field|modifier:        # 필드 + 연산자
            - "value1"
            - "value2"
    condition: selection       # 조건식
level: low | medium | high | critical
falsepositives:
    - 오탐 사례
tags:
    - attack.t1190             # MITRE ATT&CK
```

### 탐지 연산자

| 연산자 | 설명 | 예시 |
|--------|------|------|
| `|contains` | 부분 매칭 | `field|contains: "UNION"` |
| `|startswith` | 접두사 매칭 | `field|startswith: "/admin"` |
| `|endswith` | 접미사 매칭 | `field|endswith: ".php"` |
| `|re` | 정규표현식 | `field|re: "^[0-9]+$"` |
| `count()` | 집계 (timeframe 필요) | `count(src_ip) > 20` |

---

## Step 1: Sigma Rule 구조 이해

Sigma는 SIEM 제품에 독립적인 탐지 룰 작성 표준이다. 하나의 Sigma Rule을 작성하면 Elasticsearch, Splunk, QRadar 등 다양한 SIEM 쿼리로 변환할 수 있다.

### 기본 구조

```yaml
title: 룰 제목
id: 고유 UUID
status: experimental | test | stable
level: informational | low | medium | high | critical
description: 룰 설명

logsource:
    category: webserver        # 로그 카테고리
    product: apache            # 제품명 (선택)

detection:
    selection:
        fieldname|modifier:    # 필드명과 수정자
            - 'value1'
            - 'value2'
    condition: selection       # 조건 표현식

falsepositives:
    - 오탐 가능 상황 설명

tags:
    - attack.initial_access    # MITRE ATT&CK 태그
    - attack.t1190
```

### 주요 수정자 (Modifiers)

| 수정자 | 설명 | 예시 |
|--------|------|------|
| `contains` | 부분 일치 | `url\|contains: 'UNION SELECT'` |
| `startswith` | 접두사 일치 | `path\|startswith: '/admin'` |
| `endswith` | 접미사 일치 | `file\|endswith: '.exe'` |
| `re` | 정규표현식 | `cmd\|re: '.*whoami.*'` |
| `all` | 모든 값 포함 | `url\|contains\|all:` |

---

## Step 2: SQLi 탐지 룰 분석

기존 제공된 SQL Injection 탐지 룰을 분석한다.

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
cat /lab/sigma-rules/sqli-detection.yml
```

### 핵심 분석 포인트

```yaml
detection:
    selection:
        cs-uri-query|contains:
            - 'UNION SELECT'
            - 'OR 1=1'
            - "' OR '"
            - 'DROP TABLE'
            - 'INSERT INTO'
            - '; SELECT'
            - 'WAITFOR DELAY'
            - 'BENCHMARK('
            - 'SLEEP('
    condition: selection
```

분석 질문:
- `cs-uri-query|contains`에서 `contains` 수정자의 역할은?
- 각 탐지 문자열이 어떤 SQLi 기법에 해당하는가?
- `WAITFOR DELAY`와 `SLEEP()`은 어떤 공격 유형인가? (Blind SQLi / Time-based)

### 2-3. 탐지 키워드별 공격 원리

| 키워드 | 공격 기법 | 원리 | 예시 |
|--------|---------|------|------|
| `UNION SELECT` | Union-based SQLi | 추가 SELECT로 다른 테이블 데이터 추출 | `' UNION SELECT username, password FROM users--` |
| `OR '1'='1'` | Authentication Bypass | WHERE 조건을 항상 참으로 만듦 | `' OR '1'='1' --` → 모든 행 반환 |
| `DROP TABLE` | Destructive SQLi | 테이블 삭제 | `'; DROP TABLE users--` |
| `SLEEP(` | Time-based Blind SQLi | 응답 지연으로 참/거짓 판단 | `' AND SLEEP(5)--` → 5초 지연이면 참 |
| `'--` | Comment Injection | 뒤의 SQL 구문 무시 | `admin'--` → 비밀번호 검증 우회 |
| `information_schema` | Schema Enumeration | DB 구조 파악 | `UNION SELECT table_name FROM information_schema.tables` |

---

## Step 3: XSS 탐지 룰 직접 작성

제공된 예시를 참고하여 XSS 탐지 룰의 구조를 이해한다.

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
cat /lab/sigma-rules/xss-detection.yml
```

### XSS 탐지 핵심 패턴

아래 패턴들이 포함되어야 한다:

```yaml
detection:
    selection:
        cs-uri-query|contains:
            - '<script>'
            - '<script'
            - 'javascript:'
            - 'onerror='
            - 'onload='
            - 'onmouseover='
            - 'alert('
            - 'document.cookie'
            - 'eval('
    condition: selection
```

### 실습: 룰 보강

기존 XSS 룰에 다음 패턴을 추가하여 `sigma-rules/xss-detection-v2.yml`을 작성하시오:

```yaml
title: Enhanced XSS Detection via Web Access Logs
id: b3f8a1c4-9e72-4d56-a8b1-2c7e5f309d12
status: experimental
level: high
description: 웹 접근 로그에서 향상된 XSS 공격 패턴 탐지

logsource:
    category: webserver

detection:
    selection_basic:
        cs-uri-query|contains:
            - '<script'
            - 'javascript:'
            - 'onerror='
            - 'onload='
    selection_advanced:
        cs-uri-query|contains:
            - 'String.fromCharCode'
            - 'document.write'
            - 'window.location'
            - 'innerHTML'
            - '.appendChild('
    selection_encoded:
        cs-uri-query|contains:
            - '%3Cscript'
            - '%3cscript'
            - '&#x3C;script'
    condition: selection_basic or selection_advanced or selection_encoded

falsepositives:
    - 정상적인 JavaScript 개발 관련 검색
    - 보안 교육 자료 접근

tags:
    - attack.initial_access
    - attack.t1189
```

---

## Step 4: 브루트포스 탐지 룰 작성

로그인 실패가 짧은 시간 내에 반복되는 패턴을 탐지한다.

### count 조건과 timeframe

Sigma는 `count()` 함수와 `timeframe`을 사용하여 임계값 기반 탐지를 지원한다.

```yaml
title: Web Login Brute Force Detection
id: a0f7e8d2-1234-5678-9abc-def012345678
status: experimental
level: high
description: 동일 IP에서 짧은 시간 내 다수의 로그인 실패 탐지

logsource:
    category: webserver

detection:
    selection:
        cs-uri-stem|contains:
            - '/login'
            - '/auth'
            - '/wp-login'
            - '/admin/login'
        sc-status:
            - 401
            - 403
    timeframe: 5m
    condition: selection | count(source.ip) > 10

falsepositives:
    - 비밀번호 관리 도구의 자동 로그인 시도
    - 공유 NAT IP에서의 다중 사용자 접근

tags:
    - attack.credential_access
    - attack.t1110
```

### 핵심 포인트

- `timeframe: 5m` - 5분 윈도우 내에서 집계
- `count(source.ip) > 10` - 동일 IP에서 10회 초과 시 탐지
- 임계값은 환경에 따라 조정 필요

---

## Step 5: sigma-cli로 ES Query DSL 변환

작성된 Sigma Rule을 Elasticsearch 쿼리로 변환한다.

### sigma-cli 설치

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# tools 컨테이너에는 sigma-cli가 사전 설치되어 있습니다
sigma version
# 미설치 시: pip install sigma-cli pySigma-backend-elasticsearch
```

### 변환 명령

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# SQLi 탐지 룰 변환
sigma convert -t lucene --without-pipeline /lab/sigma-rules/sqli-detection.yml

# XSS 탐지 룰 변환
sigma convert -t lucene --without-pipeline /lab/sigma-rules/xss-detection.yml

# 출력 형식 지정 (plain lucene 쿼리, default)
sigma convert -t lucene --without-pipeline -f default /lab/sigma-rules/sqli-detection.yml

# DSL 쿼리 형식 출력
sigma convert -t lucene --without-pipeline -f dsl_lucene /lab/sigma-rules/sqli-detection.yml

# 사용 가능한 출력 형식 확인
sigma list formats lucene
```

### 변환 결과 예시 (DSL)

sigma-cli 변환 결과는 Sigma 필드명을 그대로 사용합니다. **이 쿼리를 그대로 실행하면 결과가 0건**입니다:

```json
// ❌ sigma 변환 원본 — cs-uri-query 필드가 ES에 존재하지 않음
{
  "query": {
    "bool": {
      "should": [
        {"wildcard": {"cs-uri-query": {"value": "*' OR *"}}},
        {"wildcard": {"cs-uri-query": {"value": "*UNION SELECT*"}}},
        {"wildcard": {"cs-uri-query": {"value": "*1=1*"}}},
        {"wildcard": {"cs-uri-query": {"value": "*DROP TABLE*"}}},
        {"wildcard": {"cs-uri-query": {"value": "*SLEEP(*"}}},
        {"wildcard": {"cs-uri-query": {"value": "*information_schema*"}}}
      ],
      "minimum_should_match": 1
    }
  }
}
```

> **⚠️ 필드 매핑 필수**: Sigma 변환 결과의 필드명과 실제 ES 인덱스 필드명이 다릅니다.
> `--without-pipeline` 옵션은 필드 매핑 없이 변환하므로, 실행 전 반드시 아래 표를 참고하여 수정하세요.
>
> | Sigma 변환 결과 필드 | 실제 ES 필드 (`security-web-*`) | 설명 |
> |---|---|---|
> | `cs-uri-query` | `url.path_decoded.keyword` | URL 디코딩된 요청 경로 (wildcard 쿼리 시 `.keyword` 필수) |
> | `cs-uri-stem` | `url.path` | 요청 경로 원본 |
> | `sc-status` | `http.response.status_code` | HTTP 상태 코드 |
> | `c-ip` | `source.ip` | 클라이언트 IP |
>
> **왜 `.keyword`가 필요한가?** `url.path_decoded`는 `text` 타입으로 토큰화(tokenize)되어 저장됩니다.
> wildcard 쿼리는 토큰화된 텀을 검색하므로 `*UNION SELECT*` 같은 원본 문자열 매칭이 실패합니다.
> `.keyword` 서브필드는 원본 문자열 그대로 저장되므로 wildcard 매칭이 정상 동작합니다.

### 5-3. 필드 매핑 적용 후 쿼리

위 변환 결과에서 필드명을 실제 ES 필드로 수정한 쿼리:

```json
// ✅ 필드 매핑 적용 — 실제 ES에서 동작하는 쿼리
{
  "query": {
    "bool": {
      "should": [
        { "wildcard": { "url.path_decoded.keyword": "*UNION SELECT*" } },
        { "wildcard": { "url.path_decoded.keyword": "*OR 1=1*" } },
        { "wildcard": { "url.path_decoded.keyword": "*DROP TABLE*" } }
      ],
      "minimum_should_match": 1
    }
  }
}
```

### 5-4. 변환 오류 해결

```bash
# tools 컨테이너 내부에서 실행 (docker exec -it tools bash)
# 오류 1: 백엔드 미설치
# Error: No backend found for target 'elasticsearch'
pip install pySigma-backend-elasticsearch

# 오류 2: 파이프라인 미설치
# Warning: No pipeline specified

# 오류 3: 지원하지 않는 modifier
# Error: Unsupported modifier 'base64'
# → 해당 modifier를 |contains 등으로 대체

# 변환 디버그 모드
sigma convert -t lucene --without-pipeline --debug /lab/sigma-rules/sqli-detection.yml
```

---

## Step 6: 변환된 쿼리를 Kibana Dev Tools에서 실행

1. Kibana 좌측 메뉴에서 **Management** > **Dev Tools** 클릭
2. 변환된 쿼리를 아래 형식으로 실행:

```json
GET /security-web-*/_search
{
  "query": {
    "bool": {
      "should": [
        { "wildcard": { "url.path_decoded.keyword": "*UNION SELECT*" } },
        { "wildcard": { "url.path_decoded.keyword": "*OR 1=1*" } },
        { "wildcard": { "url.path_decoded.keyword": "*' OR '*" } },
        { "wildcard": { "url.path_decoded.keyword": "*DROP TABLE*" } }
      ],
      "minimum_should_match": 1
    }
  },
  "size": 20,
  "sort": [{ "@timestamp": "desc" }]
}
```

3. 결과 확인:
   - `hits.total.value`: 탐지된 총 이벤트 수
   - `hits.hits[]._source`: 개별 이벤트 상세

4. 탐지 결과를 분석하여 다음을 기록:
   - 탐지된 SQLi 이벤트 수
   - 공격 소스 IP 목록
   - 사용된 공격 페이로드 유형

---

## Step 7: ES Watcher로 자동 탐지 등록

변환된 쿼리를 Elasticsearch Watcher에 등록하여 자동 탐지를 구성한다.

> **⚠️ 라이선스 요구사항**: Watcher는 Basic 라이선스에서 사용할 수 없습니다. 실습을 위해 Trial 라이선스를 활성화하세요:
> ```json
> POST _license/start_trial?acknowledge=true
> ```
> Trial은 30일간 유효하며, Watcher를 포함한 모든 Platinum 기능을 사용할 수 있습니다.

### Watcher 등록

Kibana Dev Tools에서 실행:

```json
PUT _watcher/watch/sqli-detection
{
  "trigger": {
    "schedule": {
      "interval": "1m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["security-web-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {
                  "bool": {
                    "should": [
                      { "wildcard": { "url.path_decoded.keyword": "*UNION SELECT*" } },
                      { "wildcard": { "url.path_decoded.keyword": "*OR 1=1*" } },
                      { "wildcard": { "url.path_decoded.keyword": "*DROP TABLE*" } }
                    ],
                    "minimum_should_match": 1
                  }
                },
                {
                  "range": {
                    "@timestamp": {
                      "gte": "now-1m"
                    }
                  }
                }
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total.value": {
        "gt": 0
      }
    }
  },
  "actions": {
    "log_alert": {
      "logging": {
        "text": "[SQLi Alert] {{ctx.payload.hits.total.value}} SQL Injection attempts detected in the last 1 minute"
      }
    }
  }
}
```

### Watcher 상태 확인

```json
GET _watcher/watch/sqli-detection

GET _watcher/stats
```

### Watcher 실행 테스트

```json
POST _watcher/watch/sqli-detection/_execute
```

### 7-4. Kibana Alerts로 간편 설정 (대안)

ES Watcher 대신 Kibana UI에서 알림을 설정할 수도 있습니다:

1. **Stack Management** → **Rules** → **Create rule**
2. **Rule type**: `Elasticsearch query`
3. **Index**: `security-web-*`
4. **Query** (KQL): `tags: sqli OR tags: xss`
5. **Threshold**: `> 0` (1건이라도 탐지 시)
6. **Check every**: `1 minute`
7. **Actions**: Server log (실습용) 또는 이메일/Slack

**Watcher vs Kibana Alerts 비교:**

| 항목 | ES Watcher | Kibana Alerts |
|------|:---------:|:------------:|
| 설정 방식 | JSON API | UI (클릭) |
| 학습 난이도 | 높음 | 낮음 |
| 유연성 | 높음 (script 지원) | 중간 |
| 권장 환경 | 자동화/대규모 | 소규모/POC |

---
