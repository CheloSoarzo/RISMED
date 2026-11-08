#!/bin/bash
# PACS-RISMED (mamografía) · Pegar en Vultr: Deploy → Additional Features → "Cloud-Init User-Data".
# Instala PACS + informes + agenda automáticamente al crear el servidor (tarda unos 10-15 minutos).
#
# El repositorio RISMED (si es privado): el servidor lo baja con un token de solo lectura.
# Créalo en GitHub: Settings → Developer settings → Personal access tokens → Fine-grained tokens →
#   Generate new token · Repository access: Only select repositories → RISMED ·
#   Permissions → Contents: Read-only. Pégalo abajo en GITHUB_TOKEN.
export GITHUB_TOKEN='PEGA-AQUI-EL-TOKEN'
export PACS_INICIALES='mamo:Centro de Mamografía'   # nombre:Nombre del centro (el nombre va en minúsculas, sin espacios)
export ADMIN_PASSWORD='CAMBIA-ESTA-CLAVE'          # clave inicial del admin: cámbiala al entrar (Mi cuenta)
export REPO="https://x-access-token:${GITHUB_TOKEN}@github.com/CheloSoarzo/RISMED"

# Memoria de intercambio (2 GB) para servidores chicos: evita cortes al construir la app.
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

apt-get update -y && apt-get install -y git
[ -d /opt/pacs-rismed/.git ] || git clone "$REPO" /opt/pacs-rismed
bash /opt/pacs-rismed/servidor/instalar.sh
