import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting with device ID: {device_id}")
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {"User-Agent": random_user_agent}
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            
            # Create Proxy instance
            if '@' in socks5_proxy:  # Check if proxy is in username:password@ip:port format
                proxy = Proxy.from_url(f'socks5://{socks5_proxy}')
            else:  # Assume it is in ip:port format
                proxy = Proxy.from_url(f'socks5://{socks5_proxy}')
            
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(30)

                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "4.26.2"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))
                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)

async def main():
    # Baca daftar akun dari account.json
    with open('account.json', 'r') as account_file:
        accounts = json.load(account_file)
    
    # Buat tugas koneksi untuk setiap akun dan daftar proxy masing-masing
    tasks = []
    for account in accounts:
        user_id = account["_user_id"]
        proxy_file_path = account["proxy"]
        
        # Baca daftar proxy untuk akun ini
        with open(proxy_file_path, 'r') as file:
            socks5_proxy_list = file.read().splitlines()
        
        # Buat koneksi untuk setiap proxy
        for proxy in socks5_proxy_list:
            tasks.append(asyncio.ensure_future(connect_to_wss(proxy, user_id)))
    
    # Jalankan semua koneksi
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())

