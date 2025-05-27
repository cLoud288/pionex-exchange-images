import os
import json
import requests
import random
from pathlib import Path
from tqdm import tqdm
import argparse
from urllib.parse import urlparse
import time

# Конфигурация
ALCHEMY_API_KEY = "Vt9PSYxJRwQ985sKyfB9X"
ALCHEMY_BASE_URL = "https://eth-mainnet.g.alchemy.com/v2/"
IPFS_GATEWAY = "https://ipfs.io/ipfs/"

# Список коллекций из скриншотов
POPULAR_COLLECTIONS = [
    # Успешно скачанные коллекции
    {"name": "Phanta Bear", "address": "0x67D9417C9C3c250f61A83C7e8658daC487B56B09"},
    {"name": "Azuki", "address": "0xED5AF388653567Af2F388E6224dC7C4b3241C544"},
    {"name": "Moonbirds", "address": "0x23581767a106ae21c074b2276D25e5C3e136a68b"},
    {"name": "PudgyPenguins", "address": "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8"},
    {"name": "DeadFellaz", "address": "0x2acAb3DEa77832C09420663b0E1cB386031bA17B"},
    {"name": "ALIENFRENS", "address": "0x123b30E25973FeCd8354dd5f41Cc45A3065eF88C"},
    {"name": "Wrapped Cryptopunks", "address": "0xb7F7F6C52F2e2fdb1963Eab30438024864c313F6"},
    {"name": "Hashmasks", "address": "0xC2C747E0F7004F9E8817Db2ca4997657a7746928"},
    {"name": "DigiDaigaku", "address": "0xd1258DB6Ac08eB0e625B75b371C023dA478E94A9"},
    {"name": "BASTARD GAN PUNKS V2", "address": "0x31385d3520bCED94f77AaE104b406994D8F2168C"},
    
    # Новые коллекции взамен проблемных
    {"name": "Cool Cats", "address": "0x1A92f7381B9F03921564a437210bB9396471050C"},
    {"name": "Doodles", "address": "0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e"},
    {"name": "World of Women", "address": "0xe785E82358879F061BC3dcAC6f0444462D4b5330"},
    {"name": "CloneX", "address": "0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B"},
    {"name": "VeeFriends", "address": "0xa3AEe8BcE55BEeA1951EF834b99f3Ac60d1ABeeB"},
    {"name": "Bored Ape Yacht Club", "address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"},
    {"name": "CryptoPunks", "address": "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB"},
    {"name": "Art Blocks", "address": "0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270"},
    {"name": "CyberKongz", "address": "0x57a204AA1042f6E66DD7730813f4024114d74f37"},
    {"name": "Mutant Ape Yacht Club", "address": "0x60E4d786628Fea6478F785A6d7e704777c86a7c6"}
]

def get_collection_info(contract_address):
    """Получает информацию о коллекции через Alchemy API"""
    url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}/getNFTMetadata"
    params = {
        "contractAddress": contract_address,
        "tokenId": "1"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        collection_info = {
            "name": data.get("contractMetadata", {}).get("openSea", {}).get("collectionName", "Unknown"),
            "floor_price": data.get("contractMetadata", {}).get("openSea", {}).get("floorPrice", 0),
            "description": data.get("contractMetadata", {}).get("openSea", {}).get("description", ""),
            "contract_address": contract_address
        }
        return collection_info
    except Exception as e:
        print(f"Ошибка при получении информации о коллекции {contract_address}: {str(e)}")
        return None

def get_nft_metadata(contract_address, token_id):
    """Получает метаданные NFT через Alchemy API"""
    url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}/getNFTMetadata"
    params = {
        "contractAddress": contract_address,
        "tokenId": str(token_id),
        "refreshCache": "false"
    }
    headers = {
        "accept": "application/json"
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к Alchemy API для токена {token_id}: {str(e)}")
        return None

def get_nft_price(contract_address, token_id):
    """Получает текущую цену NFT через OpenSea API"""
    try:
        # Используем floor price коллекции как приблизительную цену
        url = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}/getNFTMetadata"
        params = {
            "contractAddress": contract_address,
            "tokenId": str(token_id)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        floor_price = data.get("contractMetadata", {}).get("openSea", {}).get("floorPrice", 0)
        return floor_price
    except Exception as e:
        print(f"Ошибка при получении цены для токена {token_id}: {str(e)}")
        return 0

def download_image(url, save_path):
    """Скачивает изображение по URL"""
    try:
        if not url:
            return False
            
        response = requests.get(url)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Ошибка при скачивании {url}: {str(e)}")
        return False

def process_token(args):
    """Обрабатывает один токен: получает метаданные и скачивает изображение"""
    contract_address = args.contract_address
    token_id = args.token_id
    save_dir = args.save_dir

    metadata = get_nft_metadata(contract_address, token_id)
    if not metadata:
        return False

    try:
        # Получаем цену NFT
        price = get_nft_price(contract_address, token_id)
        
        # Получаем атрибуты и другие метаданные
        nft_data = {
            "token_id": token_id,
            "price_eth": price,
            "attributes": metadata.get("metadata", {}).get("attributes", []),
            "name": metadata.get("title", f"Token #{token_id}"),
            "description": metadata.get("description", "")
        }
        
        if 'media' in metadata and len(metadata['media']) > 0:
            image_url = metadata['media'][0]['gateway']
            parsed_url = urlparse(image_url)
            extension = os.path.splitext(parsed_url.path)[1] or '.png'
            
            # Сохраняем изображение
            image_filename = f"{token_id}{extension}"
            save_path = os.path.join(save_dir, image_filename)
            
            if download_image(image_url, save_path):
                # Сохраняем метаданные в JSON файл
                nft_data["image_filename"] = image_filename
                metadata_path = os.path.join(save_dir, f"{token_id}_metadata.json")
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(nft_data, f, indent=2, ensure_ascii=False)
                return True
                
        return False
    except Exception as e:
        print(f"Ошибка при обработке токена {token_id}: {str(e)}")
        return False

def download_collection_sample(collection_info, num_samples=50):
    """Скачивает случайную выборку NFT из коллекции"""
    contract_address = collection_info["contract_address"]
    collection_name = collection_info["name"]
    
    # Создаем директорию для коллекции
    save_dir = f"collections/{collection_name}"
    os.makedirs(save_dir, exist_ok=True)
    
    # Сохраняем информацию о коллекции
    with open(os.path.join(save_dir, "collection_info.json"), "w", encoding='utf-8') as f:
        json.dump(collection_info, f, indent=2, ensure_ascii=False)
    
    print(f"\nСкачивание {num_samples} NFT из коллекции {collection_name}")
    print(f"Минимальная цена коллекции: {collection_info.get('floor_price', 'Неизвестно')} ETH")
    
    # Генерируем случайные ID токенов
    token_ids = random.sample(range(0, 1000), num_samples)
    
    args_list = []
    for token_id in token_ids:
        args_list.append(argparse.Namespace(
            contract_address=contract_address,
            token_id=token_id,
            save_dir=save_dir
        ))

    with tqdm(total=len(args_list), desc="Скачивание NFT") as pbar:
        for args in args_list:
            success = process_token(args)
            time.sleep(0.1)  # Небольшая задержка между запросами
            pbar.update(1)

def main():
    # Создаем основную директорию для коллекций
    os.makedirs("collections", exist_ok=True)
    
    # Скачиваем все коллекции
    for collection in POPULAR_COLLECTIONS:
        print(f"\nОбработка коллекции: {collection['name']}")
        collection_info = get_collection_info(collection["address"])
        if collection_info:
            collection_info["contract_address"] = collection["address"]
            # Скачиваем по 50 NFT из каждой коллекции
            download_collection_sample(collection_info, num_samples=50)
            time.sleep(1)  # Задержка между коллекциями
        else:
            print(f"Не удалось получить информацию о коллекции {collection['name']}")

if __name__ == "__main__":
    main() 