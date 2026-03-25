# 실습 4: Kibana 대시보드 구성

## 목표

Kibana **Lens** 및 **TSVB**를 활용하여 보안 모니터링 대시보드를 구성한다.
완성된 대시보드에서 공격 트래픽을 시각적으로 식별할 수 있다.


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
---

## 컴포넌트 설명: Kibana 시각화 도구

### Kibana 접속

```
URL: http://localhost:5601
```

### Kibana 주요 메뉴

| 메뉴 | 경로 | 용도 |
|------|------|------|
| **Discover** | Analytics → Discover | 로그 검색, KQL 쿼리 |
| **Visualize** | Analytics → Visualize Library | 개별 차트 생성 |
| **Dashboard** | Analytics → Dashboard | 패널 조합 대시보드 |
| **Maps** | Analytics → Maps | GeoIP 지도 시각화 |
| **Dev Tools** | Management → Dev Tools | ES API 직접 실행 |
| **Data Views** | Stack Management → Data Views | 인덱스 패턴 관리 |

### Data View (인덱스 패턴) 설정

실습 전 반드시 Data View를 생성해야 합니다.

1. **Stack Management** → **Data Views** → **Create data view**
2. 이름: `security-*`, 타임스탬프: `@timestamp`
3. 필요 시 개별 패턴도 생성:
   - `security-web-*` (웹 로그만)
   - `security-sysmon-*` (Sysmon만)
   - `security-suricata-*` (IDS만)

또는 스크립트로 자동 생성:
```bash
# 호스트에서 실행 (elk-siem-lab 디렉토리에서)
bash scripts/import-dashboards.sh
```

### Lens 시각화 유형

| 유형 | 용도 | 대표 사용 |
|------|------|----------|
| **Area Chart** | 시간대별 추이 | Error Rate Timeline |
| **Bar Chart** | 순위/비교 | Top 10 공격 IP |
| **Pie Chart** | 비율/분포 | HTTP 상태 코드 분포 |
| **Metric** | 단일 수치 | 총 공격 건수 |
| **Data Table** | 상세 목록 | 공격 로그 리스트 |

### TSVB (Time Series Visual Builder)

다중 메트릭, 이동 평균, 임계값 라인을 하나의 차트에 표시합니다.
- Panel options → Index pattern → `security-*`
- Metrics → Count / Average / Sum
- Annotations → 특정 이벤트 마커

---

## Step 1: Lens로 Error Rate Timeline 생성

HTTP 4xx/5xx 에러 발생 추이를 시계열로 시각화한다.

1. Kibana 좌측 메뉴에서 **Dashboard** > **Create dashboard** 클릭
2. **Create visualization** 클릭 (Lens 에디터 진입)
3. 차트 타입: **Area**
4. 설정:
   - **Horizontal axis**: `@timestamp` (Date Histogram, interval: auto)
   - **Vertical axis**: Count, 필터 조건 추가

5. Vertical axis 필터에 아래 KQL 입력:

```
response >= 400
```

6. 제목을 `Error Rate Timeline`으로 설정하고 **Save and return**

> 정상 트래픽 대비 에러 비율이 급증하는 구간이 공격 시점이다.

### Step 1 상세: Lens Area Chart 생성 순서

1. **Kibana** → **Analytics** → **Visualize Library** → **Create visualization**
2. **Lens** 선택
3. 좌측 **Data view**: `security-web-*` 선택
4. **Visualization type**: `Area` 선택 (상단 드롭다운)

**X축 설정:**
5. 하단 **Horizontal axis** 클릭
6. **Field**: `@timestamp`
7. **Function**: `Date histogram`
8. **Minimum interval**: `Auto` (또는 `1 minute`)

**Y축 설정:**
9. 좌측 **Vertical axis** 클릭
10. **Function**: `Count`
11. **Filter** (KQL): `http.response.status_code >= 400`

**스타일:**
12. 색상: 빨간색 계열 (에러 강조)
13. 제목: "Error Rate Timeline"
14. **Save** → Dashboard에 추가

**기대 결과:** 시간대별 에러 발생 추이 그래프. Brute-force 시간대에 **급격한 spike** 확인.

---

## Step 2: Top 10 공격 IP 바 차트

가장 많은 에러를 발생시킨 IP를 식별한다.

1. **Create visualization** > Lens > **Bar horizontal**
2. 설정:
   - **Vertical axis**: `source.ip` (Terms aggregation, Top 10)
   - **Horizontal axis**: Count

3. 필터 추가 (KQL):

```
response >= 400
```

4. 제목: `Top 10 공격 IP`로 저장

### Step 2 상세: Top 10 IP 바 차트 생성

1. **Create visualization** → **Lens** → `Bar vertical`
2. **Data view**: `security-web-*`

**X축:**
3. **Field**: `source.ip.keyword` (반드시 `.keyword` 사용)
4. **Function**: `Top values`
5. **Number of values**: `10`

**Y축:**
6. **Function**: `Count`

**필터:**
7. KQL: `tags: attack OR tags: sqli OR tags: xss OR tags: path_traversal`

**정렬:**
8. Y축 기준 내림차순 (가장 많은 공격 IP가 맨 왼쪽)

**기대 결과:** 공격 IP 3개 (`203.0.113.42`, `198.51.100.77`, `185.220.101.33`)가 상위에 표시.

---

## Step 3: HTTP 상태 코드 분포 Pie Chart

전체 트래픽의 상태 코드 분포를 파악한다.

1. **Create visualization** > Lens > **Pie**
2. 설정:
   - **Slice by**: `response` 필드 (Terms aggregation, Top 10)
   - **Size by**: Count

3. 제목: `HTTP 상태 코드 분포`로 저장

> 200번대가 대부분이어야 정상이다. 4xx/5xx 비율이 높으면 공격 또는 장애를 의심한다.

---

## Step 4: GeoIP 위협 맵

공격 IP의 지리적 위치를 지도에 표시한다.

1. Kibana 좌측 메뉴에서 **Maps** 클릭
2. **Add layer** > **Documents** 선택
3. 인덱스 패턴 선택 후, Geospatial field: `source.geo.location`
4. 필터 추가:

```
response >= 400
```

5. 스타일 설정:
   - Fill color: count 기반 그라데이션 (노랑 → 빨강)
   - Symbol size: count 비례

6. **Save and return** > 대시보드에 추가

### Step 4 상세: GeoIP 위협 맵 생성

1. **Analytics** → **Maps** → **Create map**
2. **Add layer** → **Documents**
3. **Data view**: `security-web-*`
4. **Geospatial field**: `source.geo.location`

**스타일 설정:**
5. **Fill color**: By value → `http.response.status_code`
   - 200: 초록, 4xx: 주황, 5xx: 빨강
6. **Icon size**: By value → `Count` (요청 수에 비례)

**필터:**
7. KQL: `source.geo: *` (GeoIP 데이터 있는 것만)
8. 시간 범위: 실습 날짜

**추가 레이어 (선택):**
9. **Add layer** → **Heat map** → 동일 필드
10. 공격 집중 지역을 히트맵으로 시각화

**기대 결과:** 공격 출발지가 지도에 점/히트맵으로 표시. 클릭 시 IP, 국가, 요청 수 팝업.

---

## Step 5: TSVB로 정상 vs 공격 트래픽 비교

**Time Series Visual Builder (TSVB)**를 사용하여 정상/공격 트래픽을 비교한다.

1. **Create visualization** > **TSVB** 선택
2. **Panel options** 탭:
   - Index pattern: 웹 로그 인덱스
   - Time field: `@timestamp`

3. **Data** 탭에서 시리즈 2개 구성:

**시리즈 1 - 정상 트래픽:**
- Label: `정상 (2xx)`
- Aggregation: Count
- Group by: Everything
- Filter (KQL):

```
response >= 200 AND response < 300
```

**시리즈 2 - 공격 트래픽:**
- Label: `공격 (4xx/5xx)`
- Aggregation: Count
- Group by: Everything
- Filter (KQL):

```
response >= 400
```

4. **Options** 탭에서 색상 지정:
   - 정상: 초록색 (`#00BFA5`)
   - 공격: 빨간색 (`#FF1744`)

5. 제목: `정상 vs 공격 트래픽 추이`로 저장

---

## Step 6: Dashboard에 패널 배치 및 필터 설정

생성한 시각화를 하나의 대시보드로 통합 배치한다.

### 권장 레이아웃

```
+---------------------------+---------------------------+
| Error Rate Timeline       | 정상 vs 공격 트래픽 추이     |
| (Area, 전체 너비 1/2)       | (TSVB, 전체 너비 1/2)      |
+---------------------------+---------------------------+
| Top 10 공격 IP            | HTTP 상태 코드 분포         |
| (Bar, 1/2)                | (Pie, 1/2)                |
+---------------------------+---------------------------+
|         GeoIP 위협 맵 (Maps, 전체 너비)                 |
+-------------------------------------------------------+
```

### 글로벌 필터 설정

1. 대시보드 상단 **Add filter** 클릭
2. 시간 범위를 로그 데이터가 포함된 기간으로 설정
3. 필요시 특정 인덱스 패턴 필터 추가

대시보드 제목을 `보안 관제 대시보드`로 저장한다.

### 대시보드 완성 예시

```
┌─────────────────────────────────────────────────────────┐
│  [Metric] 총 이벤트  [Metric] 공격 탐지  [Metric] IDS 알림 │
├───────────────────────────┬─────────────────────────────┤
│                           │                             │
│  Error Rate Timeline      │  Top 10 Attack IPs          │
│  (Area Chart)             │  (Bar Chart)                │
│                           │                             │
├───────────────────────────┼─────────────────────────────┤
│                           │                             │
│  GeoIP Threat Map         │  HTTP Status Distribution   │
│  (Maps)                   │  (Pie Chart)                │
│                           │                             │
├───────────────────────────┴─────────────────────────────┤
│                                                         │
│  IDS Signature Top 5 (Data Table)                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**글로벌 설정:**
- Time range: 실습 날짜 전체
- Auto-refresh: `10초` 또는 `30초`
- 글로벌 필터: `source.ip.keyword` 클릭 → 특정 IP 전체 패널 필터링

---

## Step 7: 드릴다운 설정

IP 클릭 시 Discover 화면으로 이동하여 상세 로그를 조회할 수 있도록 드릴다운을 구성한다.

1. **Top 10 공격 IP** 패널 편집 모드 진입
2. 우측 상단 **...** > **Create drilldown** 클릭
3. 드릴다운 유형: **Go to Discover**
4. 설정:
   - Name: `IP 상세 조회`
   - Index pattern: 웹 로그 인덱스
   - Filters: `source.ip: {{value}}`

5. 저장 후, 바 차트에서 특정 IP 클릭 시 해당 IP의 전체 로그가 Discover에 표시되는지 확인

### 드릴다운 테스트

1. 대시보드 보기 모드로 전환
2. Top 10 공격 IP 차트에서 가장 상위 IP 클릭
3. Discover 화면에서 해당 IP의 요청 패턴 확인:
   - 어떤 URL을 요청했는가?
   - 어떤 공격 패턴이 보이는가?
   - 시간대별 요청 빈도는?

---

## 트러블슈팅

### 시각화에 데이터가 표시되지 않는 경우

1. **Time range 확인**: 좌측 상단 Time picker → 샘플 로그 날짜 포함 여부
2. **Data View 확인**: 올바른 인덱스 패턴 선택 (`security-*` 또는 `security-web-*`)
3. **필드 존재 확인**: Discover에서 해당 필드에 데이터가 있는지 확인
4. **필드 타입 확인**: `.keyword` 접미사 필요 여부 (Terms aggregation 시)

### GeoIP 맵에 점이 표시되지 않는 경우

- `source.geo.location` 필드가 `geo_point` 타입인지 확인
- 사설 IP (10.x, 192.168.x)는 GeoIP 변환 불가 → 외부 IP만 표시

---
