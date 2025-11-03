# Bot modular para Discord en Python

Este proyecto es un bot para Discord desarrollado en Python. Está organizado por módulos y ofrece comandos agrupados por categorías como utilidades generales, gestión de cartas y acceso a información externa mediante APIs.

## Características

- Comandos organizados por categoría
- Integración con APIs externas usando `aiohttp`
- Estructura modular con `discord.ext.commands`
- Sistema de ayuda personalizado con agrupación por categorías

## Requisitos

- Python 3.10 o superior
- Discord bot token
- Librerías:
  - `discord.py`
  - `aiohttp`

## Instalación

```bash
git clone https://github.com/TU_USUARIO/NOMBRE_DEL_REPOSITORIO.git
cd NOMBRE_DEL_REPOSITORIO
python -m venv venv
venv\Scripts\activate  # En Windows
pip install -r requirements.txt