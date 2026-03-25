# 실습 0-B: ELK Stack 수동 설치 (Plain Linux)

> **목표**: Plain Linux 컨테이너에서 ELK 각 컴포넌트를 직접 설치하고 설정하여 동작 원리를 이해합니다.

---

## 왜 수동 설치를 배우는가?

| 항목 | docker-compose (본 실습) | 수동 설치 (본 가이드) |
|------|:----------------------:|:-------------------:|
| 설치 난이도 | 낮음 (1줄 명령) | 높음 (패키지별 설정) |
| 운영 이해도 | 낮음 (블랙박스) | **높음** (내부 구조 파악) |
| 실무 적용 | POC, 개발 환경 | **운영 서버, 커스텀 설정** |
| 트러블슈팅 | 제한적 | **깊이 있는 디버깅** |

> 실무에서는 Docker가 아닌 **베어메탈/VM에 직접 설치**하는 경우가 많습니다. 각 컴포넌트의 설정 파일 위치, 서비스 관리, 포트 설정을 직접 경험합니다.

---

## 실습 환경

> **주의**: 이 가이드는 docker-compose와 **별도로** 실행합니다. 독립적인 Ubuntu 컨테이너에서 ELK를 직접 설치합니다.

### 컨테이너 시작

```bash
# 호스트에서 실행 — Plain Ubuntu 컨테이너 생성
docker run -d --name elk-manual -p 19200:9200 -p 15601:5601 -p 15044:5044 --memory=4g ubuntu:22.04 tail -f /dev/null
```

### 컨테이너 접속

```bash
# 호스트에서 실행 — 컨테이너 내부로 접속
docker exec -it elk-manual bash
```

> 이후 모든 명령은 **elk-manual 컨테이너 내부**에서 실행합니다.
> **포트**: 기존 ELK(9200/5601)과 충돌 방지를 위해 19200, 15601, 15044 사용

---

## Step 1: 기본 패키지 설치

```bash
# 패키지 업데이트
apt-get update && apt-get install -y \
  curl \
  wget \
  gnupg \
  apt-transport-https \
  openjdk-17-jdk-headless \
  jq

# Java 확인
java -version
# 기대: openjdk version "17.x.x"
```

### Java가 필요한 이유

| 컴포넌트 | Java 필요 | 이유 |
|---------|:---------:|------|
| Elasticsearch | O | Java 기반 (Lucene 검색 엔진) |
| Logstash | O | JRuby 기반 파이프라인 엔진 |
| Kibana | X | Node.js 기반 |
| Filebeat | X | Go 기반 바이너리 |

---

## Step 2: Elastic APT 저장소 등록

```bash
# Elastic GPG 키 추가
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | \
  gpg --dearmor -o /usr/share/keyrings/elastic-keyring.gpg

# APT 저장소 추가
echo "deb [signed-by=/usr/share/keyrings/elastic-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | \
  tee /etc/apt/sources.list.d/elastic-8.x.list

# 패키지 목록 갱신
apt-get update
```

### APT 저장소에서 설치 가능한 패키지

```bash
apt-cache search elastic
# elasticsearch - Distributed RESTful search engine
# kibana - Explore and visualize your data
# logstash - Server-side data processing pipeline
# filebeat - Lightweight shipper for log data
# metricbeat - Lightweight shipper for metrics
# packetbeat - Lightweight shipper for network data
# auditbeat - Lightweight shipper for audit data
```

---

## Step 3: Elasticsearch 설치

```bash
# 설치
apt-get install -y elasticsearch

# 버전 확인
/usr/share/elasticsearch/bin/elasticsearch --version
# 기대: Version: 8.x.x
```

### 주요 파일 위치

| 경로 | 용도 |
|------|------|
| `/etc/elasticsearch/elasticsearch.yml` | **메인 설정 파일** |
| `/etc/elasticsearch/jvm.options` | JVM 힙 메모리 설정 |
| `/var/lib/elasticsearch/` | 데이터 저장 디렉토리 |
| `/var/log/elasticsearch/` | 로그 디렉토리 |
| `/usr/share/elasticsearch/bin/` | 실행 바이너리 |

### 설정 파일 수정

```bash
# elasticsearch.yml 수정
cat > /etc/elasticsearch/elasticsearch.yml << 'EOF'
# 클러스터 이름
cluster.name: siem-lab-manual

# 노드 이름
node.name: node-1

# 네트워크 바인딩 (외부 접근 허용)
network.host: 0.0.0.0

# 단일 노드 모드
discovery.type: single-node

# 보안 비활성화 (실습용)
xpack.security.enabled: false
xpack.security.enrollment.enabled: false

# HTTP 포트
http.port: 9200
EOF
```

### JVM 메모리 설정

```bash
# jvm.options 수정 (컨테이너 메모리에 맞게)
cat > /etc/elasticsearch/jvm.options.d/heap.options << 'EOF'
-Xms1g
-Xmx1g
EOF
```

> **규칙**: Xms와 Xmx는 반드시 동일하게 설정. 전체 메모리의 50% 이하 권장.

### SSL 키스토어 초기화 (보안 비활성화 시 필수)

> **주의**: `apt install elasticsearch`는 자동으로 SSL 키스토어에 비밀번호를 설정합니다. `xpack.security.enabled: false`로 비활성화했지만 키스토어에 SSL 설정이 남아있으면 시작 시 에러가 발생합니다.

```bash
# 디렉토리 소유권 먼저 변경 (키스토어 파일 수정을 위해)
chown -R elasticsearch:elasticsearch /etc/elasticsearch
chown -R elasticsearch:elasticsearch /usr/share/elasticsearch

# APT 설치 시 자동 생성된 SSL 키스토어 설정 제거 — elasticsearch 사용자로 실행
su -s /bin/bash elasticsearch -c '/usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.keystore.secure_password'
su -s /bin/bash elasticsearch -c '/usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.truststore.secure_password'

# 확인 (남은 설정 목록)
su -s /bin/bash elasticsearch -c '/usr/share/elasticsearch/bin/elasticsearch-keystore list'
# 기대: keystore.seed 만 남아있으면 정상
```

### 시작 및 확인

> **주의**: Elasticsearch는 보안상 root 사용자로 실행할 수 없습니다. `apt install elasticsearch` 시 자동 생성된 `elasticsearch` 사용자로 실행해야 합니다.

```bash
# 나머지 디렉토리 소유권 변경 (위에서 /etc, /usr/share는 완료)
chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
chown -R elasticsearch:elasticsearch /var/log/elasticsearch

# 서비스 시작 — elasticsearch 사용자로 실행 (root로 실행 시 에러 발생)
su -s /bin/bash elasticsearch -c '/usr/share/elasticsearch/bin/elasticsearch -d -p /tmp/es.pid'

# ~30초 대기 후 확인
curl -s http://localhost:9200?pretty
# 기대: cluster_name: "siem-lab-manual", version.number: "8.x.x"

# 클러스터 상태
curl -s http://localhost:9200/_cluster/health?pretty
# 기대: status: "green" (데이터 없으므로 green)
```

> **트러블슈팅**:
> - `can not run elasticsearch as root` → 위의 `su -s /bin/bash elasticsearch -c '...'` 명령으로 실행
> - `Permission denied: gc.log` → `chown -R elasticsearch:elasticsearch /usr/share/elasticsearch` 실행 후 재시도
> - `xpack.security.transport.ssl` 관련 에러 → 위의 "SSL 키스토어 초기화" 단계 수행 후 재시도

### 확인 포인트
- [ ] `curl localhost:9200` → JSON 응답
- [ ] `status: green`
- [ ] `cluster_name: siem-lab-manual`

---

## Step 4: Kibana 설치

```bash
# 설치
apt-get install -y kibana

# 버전 확인
/usr/share/kibana/bin/kibana --version
```

### 주요 파일 위치

| 경로 | 용도 |
|------|------|
| `/etc/kibana/kibana.yml` | **메인 설정 파일** |
| `/usr/share/kibana/bin/` | 실행 바이너리 |
| `/var/log/kibana/` | 로그 디렉토리 |

### 설정 파일 수정

```bash
cat > /etc/kibana/kibana.yml << 'EOF'
# Kibana 서버 포트
server.port: 5601

# 외부 접근 허용
server.host: "0.0.0.0"

# Elasticsearch 연결
elasticsearch.hosts: ["http://localhost:9200"]

# 보안 비활성화
xpack.security.enabled: false
EOF
```

### 시작 및 확인

> **주의**: Kibana도 root로 실행하는 것은 권장되지 않습니다. `apt install kibana` 시 자동 생성된 `kibana` 사용자로 실행합니다.

```bash
# 디렉토리 소유권 변경 (kibana 사용자에게)
chown -R kibana:kibana /etc/kibana
chown -R kibana:kibana /var/log/kibana
chown -R kibana:kibana /usr/share/kibana

# 서비스 시작 — kibana 사용자로 백그라운드 실행
su -s /bin/bash kibana -c '/usr/share/kibana/bin/kibana' &

# ~60초 대기 후 확인
curl -s http://localhost:5601/api/status | jq '.status.overall.level'
# 기대: "available"
```

> **대안**: root로 실행이 필요한 경우 `--allow-root` 플래그를 사용할 수 있습니다:
> ```bash
> /usr/share/kibana/bin/kibana --allow-root &
> ```

> **브라우저 접속**: http://localhost:15601 (호스트에서 접근 시 매핑된 포트)

### 확인 포인트
- [ ] `curl localhost:5601/api/status` → "available"
- [ ] 브라우저에서 Kibana UI 접근 가능

---

## Step 5: Logstash 설치

```bash
# 설치
apt-get install -y logstash

# 버전 확인
/usr/share/logstash/bin/logstash --version
```

### 주요 파일 위치

| 경로 | 용도 |
|------|------|
| `/etc/logstash/logstash.yml` | **메인 설정 파일** |
| `/etc/logstash/pipelines.yml` | 파이프라인 정의 |
| `/etc/logstash/conf.d/` | **파이프라인 conf 파일 디렉토리** |
| `/usr/share/logstash/bin/` | 실행 바이너리 |
| `/var/log/logstash/` | 로그 디렉토리 |

### 파이프라인 설정

```bash
# 테스트용 간단한 파이프라인 생성
cat > /etc/logstash/conf.d/test.conf << 'EOF'
input {
  # stdin으로 테스트 입력
  stdin {}
}

filter {
  # 메시지를 대문자로 변환
  mutate {
    uppercase => ["message"]
  }
}

output {
  # 콘솔 출력
  stdout {
    codec => rubydebug
  }

  # Elasticsearch로 전송
  elasticsearch {
    hosts => ["http://localhost:9200"]
    index => "test-logstash-%{+YYYY.MM.dd}"
  }
}
EOF
```

### 디렉토리 소유권 설정

> **주의**: Logstash도 `logstash` 사용자로 실행하는 것이 권장됩니다. `apt install logstash` 시 자동 생성된 `logstash` 사용자에게 소유권을 부여합니다.

```bash
# 디렉토리 소유권 변경 (logstash 사용자에게)
chown -R logstash:logstash /etc/logstash
chown -R logstash:logstash /var/log/logstash
chown -R logstash:logstash /usr/share/logstash
mkdir -p /tmp/logstash-test /tmp/logstash-data
chown -R logstash:logstash /tmp/logstash-test /tmp/logstash-data
```

### 설정 테스트

```bash
# 설정 파일 문법 검증 (--config.test_and_exit)
su -s /bin/bash logstash -c '/usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/test.conf --config.test_and_exit'
# 기대: "Configuration OK"
```

### 파이프라인 실행 테스트

```bash
# Logstash 실행 (포그라운드, 테스트용) — logstash 사용자로 실행
echo "hello siem lab" | su -s /bin/bash logstash -c '/usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/test.conf --path.data /tmp/logstash-test'

# 출력 확인:
# {
#     "message" => "HELLO SIEM LAB",    ← 대문자 변환됨
#     "@timestamp" => ...,
#     ...
# }
```

### 웹 로그 파이프라인 생성

```bash
# 실제 웹 로그 파싱 파이프라인
cat > /etc/logstash/conf.d/web-access.conf << 'CONF'
input {
  file {
    path => "/var/log/sample/web-access.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    tags => ["web"]
  }
}

filter {
  if "web" in [tags] {
    grok {
      match => {
        "message" => '%{IPORHOST:source.ip} - %{DATA:user.name} \[%{HTTPDATE:timestamp}\] "%{WORD:http.method} %{URIPATHPARAM:url.path} HTTP/%{NUMBER}" %{NUMBER:status:int} %{NUMBER:bytes:int} "%{DATA:referrer}" "%{DATA:user_agent}"'
      }
    }
    date {
      match => ["timestamp", "dd/MMM/yyyy:HH:mm:ss Z"]
      target => "@timestamp"
    }
  }
}

output {
  if "web" in [tags] {
    elasticsearch {
      hosts => ["http://localhost:9200"]
      index => "security-web-manual-%{+YYYY.MM.dd}"
    }
  }
}
CONF

# 파이프라인 설정 소유권 변경
chown logstash:logstash /etc/logstash/conf.d/web-access.conf
```

### Logstash 서비스 시작

```bash
# 샘플 로그 디렉토리 생성 및 읽기 권한 부여 (Step 7에서 로그 파일 생성)
mkdir -p /var/log/sample
chmod 755 /var/log/sample

# 백그라운드 실행 — logstash 사용자로 실행
su -s /bin/bash logstash -c '/usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/web-access.conf --path.data /tmp/logstash-data &'

# 로그 확인
tail -f /var/log/logstash/logstash-plain.log
# 기대: "Pipeline started"
```

### 확인 포인트
- [ ] `--config.test_and_exit` → "Configuration OK"
- [ ] stdin 테스트 → 대문자 변환 출력
- [ ] Pipeline started 메시지

---

## Step 6: Filebeat 설치

```bash
# 설치
apt-get install -y filebeat

# 버전 확인
filebeat version
```

### 주요 파일 위치

| 경로 | 용도 |
|------|------|
| `/etc/filebeat/filebeat.yml` | **메인 설정 파일** |
| `/etc/filebeat/modules.d/` | 모듈 설정 디렉토리 |
| `/usr/share/filebeat/bin/` | 실행 바이너리 |

### 설정 파일

```bash
cat > /etc/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/sample/*.log
    tags: ["web"]

# Logstash로 전송
output.logstash:
  hosts: ["localhost:5044"]

# 또는 ES로 직접 전송
#output.elasticsearch:
#  hosts: ["localhost:9200"]
#  index: "filebeat-%{+yyyy.MM.dd}"

logging.level: info
EOF
```

### 설정 파일 권한 수정

> **주의**: Filebeat는 설정 파일이 소유자만 쓸 수 있어야 합니다. `cat >` 등으로 생성하면 기본 `-rwxrwxrwx` 권한이 되어 에러가 발생합니다.

```bash
# 설정 파일 권한 수정 (소유자만 쓰기 가능하도록)
chmod go-w /etc/filebeat/filebeat.yml
```

### 설정 테스트

```bash
# 설정 검증
filebeat test config
# 기대: "Config OK"

# 출력 연결 테스트
filebeat test output
# Logstash 미실행 시 실패 → ES 직접 전송으로 전환하여 테스트
```

### Filebeat 서비스 시작

```bash
# 샘플 로그 디렉토리 확인 (Step 7에서 생성)
ls -la /var/log/sample/

# Filebeat 시작 (백그라운드) — Filebeat는 root로 실행 가능
filebeat -e -c /etc/filebeat/filebeat.yml &

# 로그 출력에서 Harvester 시작 확인
# 기대: "Harvester started for file: /var/log/sample/web-access.log"

# 데이터 디렉토리 확인
ls /var/lib/filebeat/registry/
```

> **참고**: Filebeat는 Go 바이너리로, Elasticsearch/Logstash와 달리 root 실행이 허용됩니다. 단, 운영 환경에서는 전용 사용자 사용을 권장합니다.

### Filebeat 모듈 활용

```bash
# 사용 가능한 모듈 목록
filebeat modules list

# Apache 모듈 활성화
filebeat modules enable apache

# 모듈 설정 확인
cat /etc/filebeat/modules.d/apache.yml

# Nginx 모듈 활성화
filebeat modules enable nginx

# Suricata 모듈 활성화
filebeat modules enable suricata
```

### 확인 포인트
- [ ] `filebeat version` → 버전 출력
- [ ] `filebeat test config` → "Config OK"
- [ ] `filebeat modules list` → 모듈 목록 출력

---

## Step 7: 전체 통합 테스트

모든 컴포넌트가 설치된 상태에서 통합 테스트를 수행합니다.

```bash
# 1. ES 동작 확인
curl -s http://localhost:9200/_cluster/health | jq '{status, number_of_nodes}'

# 2. Kibana 동작 확인
curl -s http://localhost:5601/api/status | jq '.status.overall.level'

# 3. 샘플 로그 생성
mkdir -p /var/log/sample
cat > /var/log/sample/web-access.log << 'LOG'
203.0.113.42 - - [26/Mar/2026:10:00:00 +0900] "GET /login?user=admin'OR'1'='1 HTTP/1.1" 200 1234 "-" "sqlmap/1.7"
10.0.1.50 - - [26/Mar/2026:10:00:01 +0900] "GET /index.html HTTP/1.1" 200 5678 "-" "Mozilla/5.0"
198.51.100.77 - - [26/Mar/2026:10:00:02 +0900] "POST /login HTTP/1.1" 401 100 "-" "Mozilla/5.0"
LOG

# 샘플 로그 파일 읽기 권한 부여 (logstash 사용자가 읽을 수 있도록)
chmod 644 /var/log/sample/web-access.log

# 4. Logstash로 파싱 확인
# (Step 5에서 시작한 Logstash가 자동으로 처리)
# Logstash가 실행 중이 아니면 아래 명령으로 시작:
# su -s /bin/bash logstash -c '/usr/share/logstash/bin/logstash -f /etc/logstash/conf.d/web-access.conf --path.data /tmp/logstash-data &'

# 5. ~30초 대기 후 인덱스 확인
curl -s http://localhost:9200/_cat/indices?v
# 기대: security-web-manual-* 인덱스 생성, 3건

# 6. 파싱된 문서 확인
curl -s 'http://localhost:9200/security-web-manual-*/_search?size=1&pretty'
# source.ip, url.path, status 등 필드 확인

# 7. 파일 내용 확인 (CLI로 원본 로그 읽기)
cat /var/log/sample/web-access.log
wc -l /var/log/sample/web-access.log
# 기대: 3줄
```

---

## Step 8: 설치 패키지 비교 정리

### APT vs tar.gz vs Docker

| 방법 | 장점 | 단점 | 적합 환경 |
|------|------|------|----------|
| **APT** (본 가이드) | 서비스 관리 (systemctl), 자동 업데이트 | Debian/Ubuntu만 | 운영 서버 |
| **RPM/YUM** | 서비스 관리 | RHEL/CentOS만 | 운영 서버 |
| **tar.gz** | OS 무관, 다중 버전 | 서비스 등록 수동 | 테스트, 다중 인스턴스 |
| **Docker** | 격리, 재현성, 1줄 실행 | 운영 복잡도 | 개발, POC, CI/CD |

### 설정 파일 위치 비교

| 컴포넌트 | APT 경로 | Docker 경로 |
|---------|---------|------------|
| ES config | `/etc/elasticsearch/` | `/usr/share/elasticsearch/config/` |
| ES data | `/var/lib/elasticsearch/` | 볼륨 마운트 |
| Kibana config | `/etc/kibana/` | `/usr/share/kibana/config/` |
| Logstash pipeline | `/etc/logstash/conf.d/` | 볼륨 마운트 (`./logstash/pipeline/`) |
| Filebeat config | `/etc/filebeat/` | 볼륨 마운트 (`./filebeat/filebeat.yml`) |

### 서비스 관리 (systemctl — 실제 서버에서)

```bash
# 시작
systemctl start elasticsearch
systemctl start kibana
systemctl start logstash
systemctl start filebeat

# 부팅 시 자동 시작
systemctl enable elasticsearch
systemctl enable kibana
systemctl enable logstash
systemctl enable filebeat

# 상태 확인
systemctl status elasticsearch
systemctl status kibana

# 로그 확인
journalctl -u elasticsearch -f
journalctl -u kibana -f
```

> **참고**: Docker 컨테이너 내부에서는 systemctl 사용 불가. 직접 실행(`/usr/share/*/bin/*`)으로 대체.

---

## 정리 및 삭제

```bash
# 컨테이너 종료 및 삭제
exit
docker stop elk-manual && docker rm elk-manual
```

---

## 핵심 정리

| 단계 | 명령 | 실행 사용자 | 확인 |
|------|------|:----------:|------|
| Java 설치 | `apt install openjdk-17-jdk-headless` | root | `java -version` |
| APT 저장소 | `echo "deb ..." > /etc/apt/sources.list.d/elastic-8.x.list` | root | `apt-cache search elastic` |
| ES 설치 | `apt install elasticsearch` | root | `/usr/share/elasticsearch/bin/elasticsearch --version` |
| ES 소유권 | `chown -R elasticsearch:elasticsearch /etc/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch /usr/share/elasticsearch` | root | - |
| ES 시작 | `su -s /bin/bash elasticsearch -c '...elasticsearch -d -p /tmp/es.pid'` | **elasticsearch** | `curl localhost:9200` |
| ES 설정 | `/etc/elasticsearch/elasticsearch.yml` | root (편집) | `cluster.name`, `discovery.type` |
| Kibana 설치 | `apt install kibana` | root | `/usr/share/kibana/bin/kibana --version` |
| Kibana 소유권 | `chown -R kibana:kibana /etc/kibana /var/log/kibana /usr/share/kibana` | root | - |
| Kibana 시작 | `su -s /bin/bash kibana -c '/usr/share/kibana/bin/kibana' &` | **kibana** | `curl localhost:5601/api/status` |
| Kibana 설정 | `/etc/kibana/kibana.yml` | root (편집) | `elasticsearch.hosts` |
| Logstash 설치 | `apt install logstash` | root | `/usr/share/logstash/bin/logstash --version` |
| Logstash 소유권 | `chown -R logstash:logstash /etc/logstash /var/log/logstash /usr/share/logstash` | root | - |
| Logstash 시작 | `su -s /bin/bash logstash -c '...logstash -f ... &'` | **logstash** | `Pipeline started` |
| Logstash 설정 | `/etc/logstash/conf.d/*.conf` | root (편집) | `--config.test_and_exit` |
| Filebeat 설치 | `apt install filebeat` | root | `filebeat version` |
| Filebeat 시작 | `filebeat -e -c /etc/filebeat/filebeat.yml &` | root (허용) | `Harvester started` |
| Filebeat 설정 | `/etc/filebeat/filebeat.yml` | root (편집) | `filebeat test config` |

### 사용자 권한 요약

> **핵심 규칙**: 설정 파일 편집은 root로, 서비스 시작은 전용 사용자로 실행합니다.

| 컴포넌트 | 설치 시 생성되는 사용자 | root 실행 | 권장 실행 사용자 |
|----------|:-------------------:|:---------:|:--------------:|
| Elasticsearch | `elasticsearch` | **불가** (에러 발생) | `elasticsearch` |
| Kibana | `kibana` | 가능 (`--allow-root`) | `kibana` |
| Logstash | `logstash` | 가능 | `logstash` |
| Filebeat | - | **가능** (Go 바이너리) | `root` |
