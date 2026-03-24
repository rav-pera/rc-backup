#!/usr/bin/env python3
"""
RC-BACKUP: Backup de fotos de usuários do Crédito de Regeneração
Baixa proofPhotos do IPFS para cada usuário registrado na blockchain
"""

import json
import sys
from web3 import Web3
import requests
from pathlib import Path
from datetime import datetime

RPC_URL = "https://rpc.sintrop.com"
DATA_DIR = Path("/root/.openclaw/workspace/rc-backup")
USERS_DIR = DATA_DIR / "users"
LAST_BLOCK_FILE = DATA_DIR / "last_block.txt"
LOG_FILE = DATA_DIR / "backup.log"

CONTRACTS = {
    "RegeneratorRules": "0x984Add883400C6E11241B9109Db59484917dF566",
    "InspectorRules": "0x753B8cAea6D0BCF23DD29aF0dF2e2E9d0d494E2f",
    "ResearcherRules": "0x74A6eff5c2E696F683d878710F840ce4c652b4f6",
    "DeveloperRules": "0x8C2b66D1aB42ebf226fe88a815385D3ce4E752CB",
    "ContributorRules": "0x1eA2264b2B881CB8A12f799dbf9A6926c6c8Fba1",
    "ActivistRules": "0xe6D42dFd5c38f7aC2D81bdfC73cd7e770f235841",
}

TYPE_MAPPING = {
    1: ("RegeneratorRules", "getRegenerator", "regenerator"),
    2: ("InspectorRules", "getInspector", "inspector"),
    3: ("ResearcherRules", "getResearcher", "researcher"),
    4: ("DeveloperRules", "getDeveloper", "developer"),
    5: ("ContributorRules", "getContributor", "contributor"),
    6: ("ActivistRules", "getActivist", "activist"),
}

# Event signatures
EVENT_SIGNATURES = {
    1: "0xc72da1a7d243084fc78268f63547c26a810a95b377ce6fa1deb0df48c04912d8",
    2: "0xf497df17d0f8e81cbbeac1fab2ef010533e6b0010216eb360160fc9021a060fa",
    3: "0xd9e252c4299740928760c15af4c9d6fee5a786293f1f330440036039a6ed533a",
    4: "0xffa85be86549e867f33ff3ad03f00922b2f7113b07f58ca22d923ed22fdebb6e",
    5: "0xc8261a89bb2ba1bec86e2467cbc6d7c91bcceef268691b418bc08e888e43f338",
    6: "0x465f144a166d5efbf5d238fa355c743be298b6a91abf5e53628b9a87dacbe3c3",
}

ABIS_DIR = Path("/root/.openclaw/crons/regeneration-credit/abis")

def load_abi(contract_name):
    with open(ABIS_DIR / f"{contract_name}.json") as f:
        return json.load(f)["abi"]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_last_block():
    if LAST_BLOCK_FILE.exists():
        with open(LAST_BLOCK_FILE) as f:
            return int(f.read().strip())
    return 0

def save_last_block(block):
    with open(LAST_BLOCK_FILE, "w") as f:
        f.write(str(block))

def download_ipfs_image(ipfs_hash, output_path):
    """Baixa imagem do IPFS e salva"""
    if not ipfs_hash or ipfs_hash == "" or ipfs_hash == "0":
        return False
    
    # Remover prefixo ipfs:// se existir
    ipfs_hash = ipfs_hash.replace("ipfs://", "")
    
    urls = [
        f"https://ipfs.io/ipfs/{ipfs_hash}",
        f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}",
        f"https://cloudflare-ipfs.com/ipfs/{ipfs_hash}",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Verificar se é imagem pelos bytes
                if response.content[:4] in [b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF"]:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return True
        except:
            continue
    return False

def main():
    log("=" * 60)
    log("RC-BACKUP: Backup de fotos via eventos")
    log("=" * 60)
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        log("ERRO: Não foi possível conectar ao RPC")
        sys.exit(1)
    
    current_block = w3.eth.block_number
    log(f"Conectado! Bloco atual: {current_block}")
    
    last_block = get_last_block()
    log(f"Último bloco processado: {last_block}")
    
    if last_block >= current_block:
        log("Nenhum novo bloco para processar")
        return
    
    # Criar diretórios
    for type_id in range(1, 7):
        type_name = TYPE_MAPPING[type_id][2]
        (USERS_DIR / type_name).mkdir(parents=True, exist_ok=True)
    
    total_downloaded = 0
    total_users = 0
    
    # Processar cada tipo de usuário
    for user_type in range(1, 7):
        contract_name = TYPE_MAPPING[user_type][0]
        get_func = TYPE_MAPPING[user_type][1]
        type_name = TYPE_MAPPING[user_type][2]
        event_sig = EVENT_SIGNATURES[user_type]
        
        log(f"Buscando eventos {type_name}...")
        
        rules_abi = load_abi(contract_name)
        rules_contract = w3.eth.contract(
            address=CONTRACTS[contract_name],
            abi=rules_abi
        )
        
        try:
            event_filter = {
                "fromBlock": last_block + 1,
                "toBlock": current_block,
                "topics": [event_sig]
            }
            
            logs = w3.eth.get_logs(event_filter)
            log(f"  Encontrados {len(logs)} eventos")
            
            for log_entry in logs:
                try:
                    # Decodificar evento
                    event = getattr(rules_contract.events, list([e for e in dir(rules_contract.events) if not e.startswith('_')])[0])()
                    decoded = event().process_log(log_entry)
                    args = decoded.args
                    
                    # Extrair ID e endereço
                    user_id = args.get('id') or args.get('researcherId')
                    user_address = args.get(f'{type_name}Address') or args.get('researcherAddress') or args.get('developerAddress') or args.get('contributorAddress') or args.get('activistAddress')
                    
                    if not user_id or not user_address:
                        continue
                    
                    total_users += 1
                    log(f"  {type_name} ID {user_id}: {user_address}")
                    
                    # Buscar proofPhoto
                    try:
                        user_data = rules_contract.functions[get_func](user_address).call()
                        
                        # O proofPhoto pode estar em diferentes posições da tupla
                        if isinstance(user_data, tuple):
                            # Geralmente o proofPhoto está na posição 3 (índice)
                            proof_photo = user_data[3] if len(user_data) > 3 else ""
                        else:
                            proof_photo = user_data.get('proofPhoto', '') if isinstance(user_data, dict) else ""
                        
                        if proof_photo and proof_photo != "0":
                            output_file = USERS_DIR / type_name / f"{user_id}.jpg"
                            if download_ipfs_image(proof_photo, output_file):
                                log(f"    -> Foto salva: {output_file.name}")
                                total_downloaded += 1
                            else:
                                log(f"    -> ERRO ao baixar: {proof_photo[:40]}...")
                        else:
                            log(f"    -> Sem proofPhoto")
                    except Exception as e:
                        log(f"    -> ERRO ao buscar dados: {e}")
                        
                except Exception as e:
                    continue
        except Exception as e:
            log(f"  AVISO: {e}")
    
    # Salvar último bloco processado
    save_last_block(current_block)
    
    log(f"Resumo: {total_users} usuários encontrados, {total_downloaded} fotos baixadas")
    log(f"Último bloco salvo: {current_block}")
    log("Backup concluído!")

if __name__ == "__main__":
    main()
