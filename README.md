# Encrypted-Socks5-proxy
I try to encrypt the socks5 proxy by add some encryption algorithm in sake of enhance security and anonymity. Refer from shadowsocks structure but more easier and intelligible. The code just for study purpose. 




# Usage

<br>

### -->Window(PowerShell) 


clone the project and enter the directory:
```bash
git clone https://github.com/peterrayn/Encrypted-Socks5-proxy.git
cd Encrypted-Socks5-proxy
```
run in a new environment(optional):
 ```bash
python -m venv env
./env/Scripts/Activate.ps1
```
install the dependance:
```bash
pip install cryptography
```
run local file:
 ```bash
python src/local.py
```
OR run server file:
 ```bash
python src/server.py
```



### -->MAC OR Linux
same process from above
```bash
git clone https://github.com/peterrayn/Encrypted-Socks5-proxy.git
cd Encrypted-Socks5-proxy
python3 -m venv env
source env/bin/activate
pip install cryptography
```
run local file:
 ```bash
python3 src/local.py
```
OR run server file:
 ```bash
python3 src/server.py
```
