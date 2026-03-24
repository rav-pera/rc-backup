#!/usr/bin/env python3
"""
RC-BACKUP: Backup de Conteúdos (Pesquisas, Relatórios, Contribuições)
======================================================================
"""

import json
import sys
from web3 import Web3, HTTPProvider
import requests
from pathlib import Path
from datetime import datetime
import re

RPC_URL = "https://rpc.sintrop.com"
IPFS_GATEWAY = "https://ipfs.sintrop.com/ipfs/"
DATA_DIR = Path("/root/.openclaw/workspace/rc-backup")
LOG_FILE = DATA_DIR / "backup_content.log"

ABIS_DIR = Path("/root/.openclaw/crons/regeneration-credit/abis")

def sanitize_hash(hash_str):
    hash_str = hash_str.replace("ipfs://", "").strip()
    return re.sub(r'[^\w\-.]', '_', hash_str)[:50]

def download_ipfs(ipfs_hash, output_path):
    if not ipfs_hash or ipfs_hash == "" or ipfs_hash == "0":
        return False
    try:
        url = f"{IPFS_GATEWAY}{ipfs_hash}"
        response = requests.get(url, timeout=180)
        if response.status_code == 200 and len(response.content) > 100:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def main():
    log("=" * 60)
    log("RC-BACKUP: Backup de Conteúdos")
    log("=" * 60)
    
    w3 = Web3(HTTPProvider(RPC_URL))
    if not w3.is_connected():
        log("ERRO: Não foi possível conectar ao RPC")
        sys.exit(1)
    
    log("Conectado ao RPC")
    total = 0
    
    # =======================
    # 1. RELATÓRIOS (DeveloperRules)
    # =======================
    log("\n=== REPORTS ===")
    with open(ABIS_DIR / "DeveloperRules.json") as f:
        abi = json.load(f)["abi"]
    
    contract = w3.eth.contract(address="0x8C2b66D1aB42ebf226fe88a815385D3ce4E752CB", abi=abi)
    
    total_reports = contract.functions.reportsTotalCount().call()
    log(f"Total: {total_reports} reports")
    
    output_dir = DATA_DIR / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for item_id in range(1, total_reports + 1):
        try:
            data = contract.functions.getReport(item_id).call()
            content_hash = str(data[4])  # posição do report hash
            
            if content_hash.startswith("Qm"):
                folder_name = f"{item_id}-{sanitize_hash(content_hash)}"
                item_dir = output_dir / folder_name
                item_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = item_dir / f"report_{item_id}_{sanitize_hash(content_hash)}.pdf"
                
                if not output_file.exists():
                    if download_ipfs(content_hash, output_file):
                        log(f"  report {item_id}: OK")
                        total += 1
        except Exception as e:
            log(f"  Erro report {item_id}: {e}")
    
    # =======================
    # 2. CONTRIBUIÇÕES (ContributorRules)
    # =======================
    log("\n=== CONTRIBUTIONS ===")
    with open(ABIS_DIR / "ContributorRules.json") as f:
        abi = json.load(f)["abi"]
    
    contract = w3.eth.contract(address="0x1eA2264b2B881CB8A12f799dbf9A6926c6c8Fba1", abi=abi)
    
    total_contribs = contract.functions.contributionsTotalCount().call()
    log(f"Total: {total_contribs} contributions")
    
    output_dir = DATA_DIR / "contributions"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for item_id in range(1, total_contribs + 1):
        try:
            data = contract.functions.getContribution(item_id).call()
            content_hash = str(data[4])  # posição do contribution hash
            
            if content_hash.startswith("Qm"):
                folder_name = f"{item_id}-{sanitize_hash(content_hash)}"
                item_dir = output_dir / folder_name
                item_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = item_dir / f"contribution_{item_id}_{sanitize_hash(content_hash)}.pdf"
                
                if not output_file.exists():
                    if download_ipfs(content_hash, output_file):
                        log(f"  contribution {item_id}: OK")
                        total += 1
        except Exception as e:
            log(f"  Erro contribution {item_id}: {e}")
    
    # =======================
    # 3. PESQUISAS (ResearcherRules)
    # =======================
    log("\n=== RESEARCHES ===")
    with open(ABIS_DIR / "ResearcherRules.json") as f:
        abi = json.load(f)["abi"]
    
    contract = w3.eth.contract(address="0x74A6eff5c2E696F683d878710F840ce4c652b4f6", abi=abi)
    
    total_research = contract.functions.researchesTotalCount().call()
    log(f"Total: {total_research} researches")
    
    output_dir = DATA_DIR / "researches"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for item_id in range(1, total_research + 1):
        try:
            data = contract.functions.getResearch(item_id).call()
            content_hash = str(data[5])  # posição do research hash
            
            if content_hash.startswith("Qm"):
                folder_name = f"{item_id}-{sanitize_hash(content_hash)}"
                item_dir = output_dir / folder_name
                item_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = item_dir / f"research_{item_id}_{sanitize_hash(content_hash)}.pdf"
                
                if not output_file.exists():
                    if download_ipfs(content_hash, output_file):
                        log(f"  research {item_id}: OK")
                        total += 1
        except Exception as e:
            log(f"  Erro research {item_id}: {e}")
    
    log(f"\nTotal baixado: {total} arquivos")
    log("Concluído!")

if __name__ == "__main__":
    main()
