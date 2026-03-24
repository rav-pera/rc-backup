#!/usr/bin/env python3
"""
RC-BACKUP: Backup de Relatórios de Inspeção
============================================
Baixa relatórios e fotos das inspeções do IPFS

Salva em: rc-backup/inspections/{id-hash}/
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
INSPECTIONS_DIR = DATA_DIR / "inspections"
LAST_ID_FILE = DATA_DIR / "last_inspection_id.txt"
LOG_FILE = DATA_DIR / "backup_inspections.log"

CONTRACT_ADDR = "0x13A40b1Cacb10A065AdC19e98270a9CC0f583281"
ABIS_DIR = Path("/root/.openclaw/crons/regeneration-credit/abis")

def load_abi():
    with open(ABIS_DIR / "InspectionRules.json") as f:
        return json.load(f)["abi"]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_last_id():
    if LAST_ID_FILE.exists():
        with open(LAST_ID_FILE) as f:
            return int(f.read().strip())
    return 0

def save_last_id(last_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(last_id))

def sanitize_hash(hash_str):
    """Remove prefixo ipfs:// e limpa o hash para nome de arquivo"""
    hash_str = hash_str.replace("ipfs://", "").strip()
    # Remove caracteres inválidos para nome de arquivo
    return re.sub(r'[^\w\-.]', '_', hash_str)

def download_ipfs(ipfs_hash, output_path):
    """Baixa arquivo do IPFS"""
    if not ipfs_hash or ipfs_hash == "" or ipfs_hash == "0":
        return False
    
    ipfs_hash = sanitize_hash(ipfs_hash)
    
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

def main():
    log("=" * 60)
    log("RC-BACKUP: Backup de Inspeções (v2)")
    log("=" * 60)
    
    w3 = Web3(HTTPProvider(RPC_URL, request_kwargs={'timeout': 120}))
    
    if not w3.is_connected():
        log("ERRO: Não foi possível conectar ao RPC")
        sys.exit(1)
    
    log("Conectado ao RPC")
    
    contract = w3.eth.contract(address=CONTRACT_ADDR, abi=load_abi())
    
    total_inspections = contract.functions.inspectionsTotalCount().call()
    log(f"Total de inspeções na blockchain: {total_inspections}")
    
    last_id = get_last_id()
    log(f"Última inspeção processada: {last_id}")
    
    if last_id >= total_inspections:
        log("Nenhuma nova inspeção para processar")
        return
    
    INSPECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    
    for inspection_id in range(last_id + 1, total_inspections + 1):
        try:
            inspection = contract.functions.getInspection(inspection_id).call()
            
            # proofPhotos (posição 7) e justificationReport (posição 8)
            proof_photos = inspection[7] if len(inspection) > 7 else ""
            report = inspection[8] if len(inspection) > 8 else ""
            
            if not proof_photos and not report:
                continue
            
            # Criar nome da pasta com id-hash
            # Se tiver report, usar o hash do report no nome
            # Se não, usar o hash das proofPhotos
            folder_hash = sanitize_hash(report) if report else (sanitize_hash(proof_photos.split(",")[0].strip()) if proof_photos else f"insp_{inspection_id}")
            folder_name = f"{inspection_id}-{folder_hash[:20]}"
            
            insp_dir = INSPECTIONS_DIR / folder_name
            insp_dir.mkdir(parents=True, exist_ok=True)
            
            log(f"Inspeção {inspection_id}:")
            
            # Baixar proofPhotos (como PDF - proofPhotos é um PDF de fotos)
            if proof_photos:
                photos_list = proof_photos.split(",")
                for i, photo in enumerate(photos_list):
                    photo = photo.strip()
                    if photo:
                        photo_hash = sanitize_hash(photo)
                        output_file = insp_dir / f"proofPhotos_{i+1}_{photo_hash}.pdf"
                        if not output_file.exists():
                            if download_ipfs(photo, output_file):
                                log(f"  proofPhotos_{i+1}.pdf: OK")
                                downloaded += 1
                            else:
                                log(f"  proofPhotos_{i+1}.pdf: ERRO")
            
            # Baixar relatório (PDF)
            if report:
                report_hash = sanitize_hash(report)
                output_file = insp_dir / f"report_{report_hash}.pdf"
                if not output_file.exists():
                    if download_ipfs(report, output_file):
                        log(f"  report.pdf: OK")
                        downloaded += 1
                    else:
                        log(f"  report.pdf: ERRO")
            
            save_last_id(inspection_id)
            
        except Exception as e:
            log(f"  ERRO na inspeção {inspection_id}: {e}")
    
    log(f"Total baixado: {downloaded} arquivos")
    log("Concluído!")

if __name__ == "__main__":
    main()
