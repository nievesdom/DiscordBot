# Yamai Bot  
  
Bot modular para Discord desarrollado en Python que implementa un sistema de cartas coleccionables con mecánicas de gacha, sistema de batallas competitivas, integración con APIs externas y una mini-aplicación web. Diseñado con arquitectura escalable basada en Cogs, persistencia en la nube con Firebase Firestore y interfaces interactivas utilizando Discord UI Components. El bot opera en múltiples servidores de Discord simultáneamente, gestionando estado persistente, sistemas de economía virtual, y proporcionando experiencias interactivas en tiempo real.
  
## Arquitectura Técnica  
  
### Patrón de Diseño: Modular Cogs  
  
El bot implementa una arquitectura modular utilizando el patrón Cogs de `discord.ext.commands`. Cada módulo funcional es una clase independiente que hereda de `commands.Cog`, permitiendo:  
  
- **Separación de responsabilidades**: Cada sistema (cartas, batallas, wiki, moderación) está aislado  
- **Carga dinámica**: Los módulos se cargan en tiempo de ejecución desde `main.py` [2-cite-0](#2-cite-0)   
- **Mantenibilidad escalable**: Añadir nuevas funcionalidades no requiere modificar el código existente  
  
### Capa de Persistencia: Firebase Firestore  
  
Implementación de una capa de abstracción para Firebase Firestore que gestiona toda la persistencia de datos:  
  
- **Cliente singleton**: Inicialización única de Firebase con credenciales desde variables de entorno [2-cite-1](#2-cite-1)   
- **Operaciones atómicas**: Funciones especializadas para cada tipo de dato (settings, inventarios, mazos, packs) [2-cite-2](#2-cite-2)   
- **Merge strategy**: Uso de `merge=True` para evitar sobrescritura de datos concurrentes  
- **Estructura de datos**: Documentos anidados por servidor y usuario para multi-tenancy  
  
### Servidor Flask Integrado  
  
Servidor HTTP concurrente que opera en un hilo separado para:  
  
- **Keep-alive**: Mantiene el bot activo en plataformas como Render [2-cite-3](#2-cite-3)   
- **Servicio de assets**: Expone imágenes de cartas vía HTTP para Discord embeds [2-cite-4](#2-cite-4)   
- **Non-blocking**: Ejecución asíncrona que no interfiere con el bot principal  
  
## Funcionalidades Detalladas  
  
### 1. Sistema de Cartas RGGO  
  
Sistema de cartas coleccionables inspirado en Yakuza: Like a Dragon con más de 400 cartas únicas.  
  
#### Estructura de Datos de Cartas  
  
Cada carta contiene metadatos completos:  
  
```json  
{  
  "id": 1,  
  "nombre": "UR Kazuma Kiryu",  
  "rareza": "UR",  
  "imagen": "https://...",  
  "atributo": "heart",  // heart, technique, body, light, shadow  
  "tipo": "attack",     // attack, defense, recovery, support  
  "health": 1050,  
  "attack": 320,  
  "defense": 280,  
  "speed": 180  
}
```

#### Sistema de Rarezas  
  
- **UR (Ultra Rare)**
- **KSR (Kiwami Super Rare)**
- **SSR (Super Super Rare)**
- **SR (Super Rare)**
- **R (Rare)**
- **N (Normal)**
  
#### Generación de Estadísticas  
  
Script automatizado (`actualizar_lista.py`) que genera estadísticas balanceadas utilizando:  
  
- **OpenCV**: Detección de color predominante para determinar el atributo de la carta a partir de su imagen
- **EasyOCR**: Reconocimiento de texto japonés para identificar el tipo de la carta también a partir de la imagen
- **Algoritmo de balanceo**: Rangos base por rareza + multiplicadores por tipo + boosts aleatorios  
  
#### Sistema de Gacha y Packs  
  
- **Packs diarios**: Límite configurable por servidor con ventanas de tiempo distribuidas  
- **Sistema de cooldowns**: Validación de tiempo entre aperturas para prevenir abuso  
- **Inventario persistente**: Cartas almacenadas por servidor y usuario en Firestore  
  
#### UI Interactiva: Navegador de Colecciones  
  
Implementación de `discord.ui.View` para navegación visual:  
  
- **Paginación**: Navegación bidireccional con botones  
- **Ordenamiento múltiple**: Por fecha, alfabético (ignorando rareza), o por rareza  
- **Embeds dinámicos**: Actualización en tiempo real sin reenviar mensajes  
- **Timeout handling**: Limpieza automática después de 5 minutos de inactividad  
  
### 2. Sistema de Spawns Automáticos  
  
Sistema asíncrono que genera cartas automáticamente en canales configurados.  
  
#### Características Técnicas  
  
- **Multi-servidor**: Tareas independientes por servidor con `asyncio.Task`  
- **Intervalos configurables**: Administradores pueden definir tiempo mínimo (0-max_horas) y máximo diario  
- **Rate limiting**: Límite de cartas por día con reset automático a medianoche  
- **Autosave optimizado**: Bucle que guarda cambios cada 60s solo si hay modificaciones pendientes  
- **Error handling**: Captura de errores de límite de GitHub API y logging centralizado  
- **Semaphore pattern**: Máximo de 5 envíos concurrentes para prevenir rate limiting  
  
#### Flujo de Spawn  
  
1. Calcular tiempo de espera aleatorio dentro del intervalo configurado  
2. Dormir hasta el momento del spawn  
3. Seleccionar carta aleatoria de la base de datos  
4. Crear embed con colores según rareza  
5. Enviar con vista interactiva para reclamo  
6. Actualizar contador y marcar cambios para autosave  
  
### 3. Sistema de Batallas Competitivas  
  
Sistema de combate por turnos basado en estadísticas con interfaz interactiva en tiempo real.  
  
#### Mecánicas de Combate  
  
- **Best of 5**: Primer jugador en ganar 3 rondas gana la partida  
- **Selección de mazos**: Cada jugador tiene 3 mazos (A, B, C) de 8 cartas  
- **Selección de cartas**: Los jugadores eligen cartas de forma privada y simultánea  
- **Comparación de stats**: Se comparan health, attack, defense, speed según la ronda  
  
#### Implementación Técnica  
  
- **Session management**: Clase `BattleSession` que mantiene estado de la partida  
- **Vistas modales**: AcceptDuelView, ChooseDeckView, ChooseCardView  
- **Timeout handling**: 180 segundos por acción con abandono automático  
- **Mensajes efímeros**: Selección de cartas en DM para privacidad  
- **Embeds visuales**: Tres embeds simultáneos (carta P1, VS, carta P2) con stats comparados  
  
#### Flujo de Batalla  
  
1. Jugador 1 desafía a Jugador 2 con `/battle`  
2. Jugador 2 recibe vista con botones Accept/Decline  
3. Ambos jugadores seleccionan mazo (A/B/C)  
4. Por cada ronda (máx 5):  
   - Sistema elige stat aleatorio a comparar  
   - Jugadores seleccionan carta en privado  
   - Sistema compara stats y asigna punto  
5. Primer jugador en 3 puntos gana  
  
### 4. Integración con Wiki API  
  
Cliente asíncrono para la API de Yakuza Fandom.  
  
#### Implementación  
  
- **Búsqueda**: Query a la API de MediaWiki con término de búsqueda  
- **Resultados por DM**: Envío privado para mantener orden en canales  
- **Error handling**: Captura de errores de privacidad de DM  
- **Comandos duales**: Implementación tanto slash como prefijo para compatibilidad  
  
### 5. Yakuzadle: Mini-App Web  
  
Aplicación web independiente desarrollada con React + Vite integrada al ecosistema.  
  
#### Scraper de Contenido  
  
Script Python (`scrape_yakuza.py`) que extrae datos de wikis:  
  
- **BeautifulSoup4**: Parsing de HTML de páginas de personajes  
- **Extracción estructurada**: Nombre japonés, aliases, afiliaciones, estilos de lucha, ocupaciones  
- **Limpieza de datos**: Funciones de normalización para remover referencias, paréntesis, y formato inconsistente  
- **Descarga de imágenes**: Almacenamiento local de imágenes de personajes  
- **Persistencia en Firestore**: Datos estructurados guardados en colección separada  
  
#### Frontend React  
  
- **Vite**: Build tool optimizado para desarrollo rápido  
- **Canvas-confetti**: Efectos visuales para celebraciones  
- **Componentes modulares**: Arquitectura de componentes reutilizables  
  
### 6. Sistema de Moderación  
  
Herramientas administrativas para gestión de comunidades.  
  
#### Migración de Contenido  
  
Comando `migrate` que transfiere contenido de AO3 linker:  
  
- **Parsing de embeds**: Extracción de título, autor, relaciones, personajes, tags  
- **Simplificación de tags**: Normalización de etiquetas complejas  
- **Creación de hilos**: Publicación en foros con etiquetas aplicadas automáticamente  
- **Deduplicación**: Prevención de migración de enlaces duplicados  
  
#### Análisis de Tags  
  
Comandos `tags1` y `tags2` que:  
  
- Analizan historial de mensajes del canal  
- Cuentan frecuencia de relaciones, personajes y tags adicionales  
- Presentan resultados ordenados por relevancia  
  
## Stack Tecnológico  
  
### Backend  
- **Python 3.10+**: Lenguaje principal  
- **discord.py**: Librería oficial para Discord API  
- **firebase-admin**: Cliente oficial de Firebase  
- **aiohttp**: Cliente HTTP asíncrono para llamadas API  
- **Flask**: Servidor web para keep-alive y serving de assets  
  
### Procesamiento de Datos  
- **OpenCV**: Detección de color en imágenes  
- **EasyOCR**: Reconocimiento de texto japonés  
- **BeautifulSoup4**: Web scraping  
- **PyGithub**: Interacción con GitHub API  
  
### Frontend (Yakuzadle)  
- **React 19**: Framework de UI  
- **Vite**: Build tool y dev server  
- **canvas-confetti**: Efectos de partículas  
  
### Infraestructura  
- **Firebase Firestore**: Base de datos NoSQL en la nube  
- **Render**: Plataforma de hosting (keep-alive server)  
  
## Estructura del Proyecto
DiscordBot/  
├── cartas/                    # Assets y metadatos de cartas  
│   ├── cartas.json           # Base de datos de 400+ cartas  
│   ├── boosts_aplicados.json # Boosts estadísticos aplicados  
│   └── boosts_especiales.json # Configuración de boosts  
├── commands/                  # Módulos Cog (lógica de negocio)  
│   ├── cartas.py            # Sistema de cartas (gacha, inventario)  
│   ├── battle.py            # Sistema de batallas competitivas  
│   ├── wiki.py              # Integración con Yakuza Fandom API  
│   ├── generales.py         # Comandos generales y utilidades  
│   ├── moderation.py        # Herramientas de moderación  
│   ├── auto_cards.py        # Spawns automáticos asíncronos  
│   ├── packs_reset.py       # Gestión de límites de packs  
│   └── debug.py             # Comandos de desarrollo  
├── core/                      # Capa de abstracción y utilidades  
│   ├── firebase_client.py   # Inicialización de Firebase  
│   ├── firebase_storage.py  # Operaciones de persistencia  
│   ├── cartas.py            # Carga y gestión de cartas  
│   ├── loader.py            # Cargador de módulos  
│   └── propiedades.py       # Gestión de propiedades  
├── views/                     # Componentes UI interactivos  
│   ├── navegador.py         # Navegador de colecciones  
│   ├── battle_views.py      # UI de batallas (accept, deck, card)  
│   ├── navegador_mazo.py    # Navegador de mazos  
│   ├── navegador_paquete.py # UI de apertura de packs  
│   ├── navegador_trade.py   # UI de intercambios  
│   ├── reclamar.py          # UI de reclamo de spawns  
│   └── gift_view.py         # UI de regalos  
├── yakuzadle/                # Mini-app React  
│   ├── scrape_yakuza.py     # Scraper de contenido de wikis  
│   └── yakuzadle/           # Frontend React + Vite  
├── data/                     # Datos locales y configuraciones  
├── main.py                   # Punto de entrada y carga de Cogs  
├── config.py                 # Configuración del bot  
├── keep_alive.py             # Servidor Flask para keep-alive  
├── actualizar_lista.py       # Script de generación de stats  
├── requirements.txt          # Dependencias Python  
└── README.md                 # Este archivo

## Configuración y Despliegue  

### Requisitos Previos  
Antes de instalar y ejecutar el proyecto, asegúrate de tener:  
- **Python 3.10 o superior**: El proyecto utiliza características modernas de Python como type hints y pattern matching  
- **Token de bot de Discord**: Crea una aplicación en [Discord Developer Portal](https://discord.com/developers/applications), habilita el bot y obtén el token  
- **Cuenta de Firebase**:   
  - Crea un proyecto en [Firebase Console](https://console.firebase.google.com/)  
  - Habilita Firestore Database  
  - Genera un archivo de credenciales JSON desde Project Settings > Service Accounts  
- **Git**: Para clonar el repositorio  
- **Pip**: Gestor de paquetes de Python (incluido con Python)

**Opcional pero recomendado:**
- **Entorno virtual**: Para aislar las dependencias del proyecto  
- **Cuenta en Render** (u otro hosting): Si planeas desplegar el bot en la nube

### Variables de Entorno  
```env  
DISCORD_TOKEN=tu_token_de_discord  
FIREBASE_CREDENTIALS_JSON=tu_json_de_credenciales_firebase  
PORT=8080
```

### Instalación
```bash 
git clone https://github.com/nievesdom/DiscordBot.git  
cd DiscordBot  
python -m venv venv  
source venv/bin/activate  # Linux/Mac  
venv\Scripts\activate  # Windows  
pip install -r requirements.txt
```

### Ejecución
```bash
python main.py
```

## Habilidades Técnicas Demostradas  
  
- **Programación asíncrona**: Manejo de concurrencia con asyncio  
- **Diseño de APIs**: Interfaces limpias y modulares  
- **Persistencia de datos**: Modelado de datos en NoSQL  
- **UI/UX en Discord**: Componentes interactivos y embeds dinámicos  
- **Web scraping**: Extracción y limpieza de datos de fuentes externas  
- **Computer Vision**: Detección de patrones en imágenes  
- **OCR**: Reconocimiento de texto en múltiples idiomas  
- **Desarrollo web**: React y herramientas modernas de frontend  
- **DevOps**: Despliegue en plataforma cloud, configuración de CI/CD  
- **Testing**: Manejo robusto de errores y edge cases  
- **Documentación**: Código bien documentado y estructurado
