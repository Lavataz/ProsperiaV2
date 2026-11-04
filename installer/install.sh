#!/bin/bash

# ============================================================
# Prosperia V2 — Installatiescript
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Start Prosperia V2 Installatie ===${NC}"

if [ ! -f "middleware.base" ]; then
    echo -e "${YELLOW}Fout: middleware.base niet gevonden. Voer dit uit vanuit de hoofdmap.${NC}"
    exit 1
fi

echo -e "\n${GREEN}[1/3] Systeempakketten installeren...${NC}"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-dev build-essential libmariadb-dev libffi-dev libssl-dev mariadb-client git curl wget

if [ -f /etc/rpi-issue ]; then
    if [ ! -f /swapfile ]; then
        echo -e "\n${GREEN}[Info] Raspberry Pi gedetecteerd. 2GB Swap aanmaken...${NC}"
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
fi

echo -e "\n${GREEN}[2/3] Python virtuele omgeving (venv313) opzetten...${NC}"
if [ -d "venv313" ]; then
    echo "De map venv313 bestaat al."
else
    python3 -m venv venv313
fi

sudo chown -R $USER:$USER .

echo -e "\n${GREEN}[3/3] Python-pakketten installeren uit middleware.base...${NC}"
source venv313/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r middleware.base

echo -e "\n${GREEN}=== Installatie succesvol afgerond! ===${NC}"
echo -e "Activeer de omgeving met: ${YELLOW}source venv313/bin/activate${NC}"
