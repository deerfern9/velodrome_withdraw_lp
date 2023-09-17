import random
import time
import requests
from web3 import Web3
from datetime import datetime
from colorama import Fore, init

from config import *
init()

colors = {
    'time': Fore.MAGENTA,
    'account_info': Fore.CYAN,
    'message': Fore.BLUE,
    'error_message': Fore.RED,
    'reset': Fore.RESET
}

web3 = Web3(Web3.HTTPProvider(op_rpc))
eth_web3 = Web3(Web3.HTTPProvider(ethereum_rpc))

velodrome_contract = web3.eth.contract(address=web3.to_checksum_address(velodrome_address), abi=velodrome_abi)
usdc_weth_lp_contract = web3.eth.contract(address=web3.to_checksum_address(usdc_weth_lp_address), abi=usdc_weth_lp_abi)
usdc_dai_lp_contract = web3.eth.contract(address=web3.to_checksum_address(usdc_dai_lp_address), abi=usdc_dai_lp_abi)
weth_contract = web3.eth.contract(address=web3.to_checksum_address(weth_address), abi=weth_abi)


def read_file(filename, read_type='r'):
    result = []
    with open(filename, read_type) as file:
        for tmp in file.readlines():
            result.append(tmp.strip())

    return result


def write_to_file(filename, text, write_type='a'):
    with open(filename, write_type) as file:
        file.write(f'{text}\n')


def new_print(message_type, message, is_error=False):
    print(f'{colors["time"]}{datetime.now().strftime("%d %H:%M:%S")}{colors["account_info"]} | {message_type} |'
          f' {colors[(["message", "error_message"])[is_error]]}{message}{colors["reset"]}')


def wait_normal_gwei():
    while (eth_gwei := web3.from_wei(eth_web3.eth.gas_price, 'gwei')) > max_gwei:
        new_print('INFO', f"Current gas fee {eth_gwei} gwei > {max_gwei} gwei. Waiting for 17 seconds...")
        time.sleep(17)


def get_eth_price():
    usd_price = requests.get('https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD')
    return usd_price.json()['USD']


def unwrap_eth(private, address, token_contract):
    try:
        tx = token_contract.functions.withdraw(token_contract.functions.balanceOf(address).call()).build_transaction({
            'from': address,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(address),
            'chainId': web3.eth.chain_id,
        })
        tx_create = web3.eth.account.sign_transaction(tx, private)
        tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)

        new_print(address, f'Withdrawing eth hash: {tx_hash.hex()}')
        write_to_file('Withdrawn eth.txt', f'{private};{address};{tx_hash.hex()}')
        web3.eth.wait_for_transaction_receipt(tx_hash)
        time.sleep(1)
    except Exception as err:
        new_print(web3.eth.account.from_key(private).address, f'Error: {err}', is_error=True)
        write_to_file('ERROR.txt', f'{private};{err}')


def approve(private, token_contract):
    try:
        wait_normal_gwei()
        address = web3.eth.account.from_key(private).address
        tx = token_contract.functions.approve(web3.to_checksum_address(velodrome_address), 2**256-1).build_transaction({
            'from': address,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(address),
            'chainId': web3.eth.chain_id,
        })
        tx_create = web3.eth.account.sign_transaction(tx, private)
        tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)

        new_print(address, f'Approving hash: {tx_hash.hex()}')
        write_to_file('approving hashes .txt', f'{private};{address};{tx_hash.hex()}')
        web3.eth.wait_for_transaction_receipt(tx_hash)
        time.sleep(1)
    except Exception as err:
        new_print(web3.eth.account.from_key(private).address, f'Error: {err}', is_error=True)
        write_to_file('ERROR.txt', f'{private};{err}')


def remove_liquidity_usdc_weth(private, address):
    try:
        wrapped_eth_address = '0x4200000000000000000000000000000000000006'
        usdc_address = '0x7F5c764cBc14f9669B88837ca1490cCa17c31607'
        stable = False
        liquidity = usdc_weth_lp_contract.functions.balanceOf(address).call()
        amount_a_min = int(1 / get_eth_price() * 4.9)
        amount_b_nin = int(4.9 * 1_000_000)
        to = address
        deadline = int(time.time() + 1800)
        approve(private, usdc_weth_lp_contract)
        wait_normal_gwei()
        tx = velodrome_contract.functions.removeLiquidity(
            wrapped_eth_address, usdc_address, stable, liquidity, amount_a_min, amount_b_nin, to, deadline
        ).build_transaction({
            'from': address,
            'nonce': web3.eth.get_transaction_count(address),
            'gasPrice': web3.eth.gas_price,
            'chainId': web3.eth.chain_id,
        })

        tx_create = web3.eth.account.sign_transaction(tx, private)
        tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)
        new_print(address, f'Liquidity removed: {tx_hash.hex()}')
        write_to_file('removed liquidity hashes .txt', f'{private};{address};{tx_hash.hex()}')
        web3.eth.wait_for_transaction_receipt(tx_hash)
        time.sleep(1)
        return True
    except Exception as err:
        new_print(web3.eth.account.from_key(private).address, f'Error: {err}', is_error=True)
        write_to_file('ERROR.txt', f'{private};{err}')
        return False


def remove_liquidity_usdc_dai(private, address):
    try:
        wrapped_eth_address = '0x7F5c764cBc14f9669B88837ca1490cCa17c31607'
        usdc_address = '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
        stable = False
        liquidity = usdc_dai_lp_contract.functions.balanceOf(address).call()
        amount_a_min = int(1 / get_eth_price() * 4.9)
        amount_b_nin = int(4.9 * 1_000_000)
        to = address
        deadline = int(time.time() + 1800)
        approve(private, usdc_dai_lp_contract)
        wait_normal_gwei()
        tx = velodrome_contract.functions.removeLiquidity(
            wrapped_eth_address, usdc_address, stable, liquidity, amount_a_min, amount_b_nin, to, deadline
        ).build_transaction({
            'from': address,
            'nonce': web3.eth.get_transaction_count(address),
            'gasPrice': web3.eth.gas_price,
            'chainId': web3.eth.chain_id,
        })

        tx_create = web3.eth.account.sign_transaction(tx, private)
        tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)
        new_print(address, f'Liquidity removed: {tx_hash.hex()}')
        write_to_file('removed liquidity hashes .txt', f'{private};{address};{tx_hash.hex()}')
        return True
    except Exception as err:
        new_print(web3.eth.account.from_key(private).address, f'Error: {err}', is_error=True)
        write_to_file('ERROR.txt', f'{private};{err}')
        return False


def main():
    privates = read_file('privates.txt')
    for private in privates:
        address = web3.eth.account.from_key(private).address
        if usdc_weth_lp_contract.functions.balanceOf(address).call() > web3.to_wei(0.00000001, 'ether'):
            if remove_liquidity_usdc_weth(private, address):
                unwrap_eth(private, address, weth_contract)
                time.sleep(random.randint(*delay))
        elif usdc_dai_lp_contract.functions.balanceOf(address).call() > web3.to_wei(0.00000005, 'ether'):
            remove_liquidity_usdc_dai(private, address)
            time.sleep(random.randint(*delay))
        else:
            new_print(address, 'Error: wallet doesn\'t have any lp', is_error=True)


if __name__ == '__main__':
    main()
