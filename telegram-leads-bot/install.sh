#!/data/data/com.termux/files/usr/bin/bash

clear

echo "===================================
 INSTALANDO TELEGRAM LEADS BOT
==================================="

# Atualiza pacotes
pkg update -y
pkg upgrade -y

# Instala dependências
pkg install -y python git curl

# Atualiza pip
pip install --upgrade pip

# Cria diretório
mkdir -p $HOME/TelegramLeadsBot
cd $HOME/TelegramLeadsBot

# Baixa arquivos do repositório
echo "Baixando arquivos..."
git clone https://github.com/rass35/telegram-leads-bot.git .
chmod +x install.sh update.sh

# Instala dependências Python
pip install -r requirements.txt

# Cria pasta de sessions
mkdir -p sessions

# Cria atalho para executar o bot
echo '#!/data/data/com.termux/files/usr/bin/bash
cd $HOME/TelegramLeadsBot && python bot.py' > $PREFIX/bin/telegramleadsbot

# Cria atalho para atualizar
echo '#!/data/data/com.termux/files/usr/bin/bash
cd $HOME/TelegramLeadsBot && bash update.sh' > $PREFIX/bin/updateleadsbot

chmod +x $PREFIX/bin/telegramleadsbot
chmod +x $PREFIX/bin/updateleadsbot

echo
echo "✅ INSTALADO COM SUCESSO!"
echo
echo "Agora basta executar:"
echo
echo "telegramleadsbot"
echo
echo "Para atualizar, execute:"
echo
echo "updateleadsbot"
