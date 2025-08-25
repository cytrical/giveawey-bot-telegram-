### 🎁 Telegram Giveaway Bot

Bot para gestionar sorteos en grupos de Telegram.
Permite configurar título, descripción, imagen, duración, meta de miembros y arranque anticipado.

## 🚀 Características

- Crear sorteos desde grupos con /newgift

- Configuración guiada en privado (título, descripción, imagen, duración, meta)

- Vista previa antes de publicar

- Arranque automático cuando el grupo llega a la meta

- Opción de inicio anticipado si faltan pocos

- Botón inline para unirse y contador en tiempo real

- Selección automática de ganador

- Mensajes de estado que se actualizan cada cierto tiempo

- Borrado automático de mensajes intermedios en la configuración


## 📖 Comandos disponibles

/start → Inicia el bot en privado.

/newgift → Crear un nuevo sorteo en el grupo.

/end → Finaliza manualmente un sorteo activo.



---

## 📦 Instalación

### 🔹 Windows

1. Instalar Python (3.9 o superior).


2. Abrir CMD o PowerShell y ejecutar:

git clone https://github.com/usuario/telegram-giveaway-bot
cd telegram-giveaway-bot
pip install -r requirements.txt


3. Editar el archivo bot.py y poner tu TOKEN de BotFather.


4. Ejecutar:

python bot.py




---

### 🔹 Linux / VPS / Hosting

1. Instalar Python 3 y Git:

sudo apt update && sudo apt install -y python3 python3-pip git


2. Descargar el proyecto:

git clone https://github.com/usuario/telegram-giveaway-bot
cd telegram-giveaway-bot
pip install -r requirements.txt


3. Editar el archivo bot.py y poner tu TOKEN.


4. Ejecutar:

python3 bot.py



👉 Opcional: mantenerlo corriendo en background

nohup python3 bot.py &


---

### 🔹 Android (Termux)

1. Instalar Termux desde F-Droid o su web oficial.


2. Ejecutar:

pkg update && pkg upgrade -y
pkg install python git -y
pkg install clang make libjpeg-turbo -y   # recomendado
pip install --upgrade pip setuptools wheel


3. Descargar el proyecto:

git clone https://github.com/usuario/telegram-giveaway-bot
cd telegram-giveaway-bot
pip install -r requirements.txt


4. Editar el archivo bot.py y poner tu TOKEN (puedes usar nano bot.py).


5. Iniciar el bot:

python bot.py




---

## 📜 Requisitos

- **Python 3.9+**
- Librerías de Python indicadas en `requirements.txt`

## 📂 requirements.txt

pyTelegramBotAPI>=4.15.0
Pillow>=10.0.0
requests>=2.31.0
python-dateutil>=2.9.0

---

📜 Licencia

Este proyecto está bajo la licencia MIT.
Puedes usarlo, modificarlo y distribuirlo libremente.
