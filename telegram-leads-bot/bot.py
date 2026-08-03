#!/usr/bin/env python3
# Robô de Leads Telegram - Versão Resiliente com Checkpoint
# Desenvolvido por INFINIT TEC

import os
import sys
import random
import asyncio
import csv
import json
import requests
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
from telethon.tl.types import (
    UserStatusRecently,
    UserStatusLastWeek,
    UserStatusLastMonth,
    UserStatusOnline,
    ChannelParticipantAdmin,
)
from telethon.errors import (
    FloodWaitError,
    PeerFloodError,
    UserPrivacyRestrictedError,
    UserNotMutualContactError
)
import pandas as pd

# --- Versão do Bot ---
VERSION = "1.0"

# --- Cores para o terminal ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- Configurações ---
SESSIONS_DIR = "sessions"
DEFAULT_SESSION = "session_default"
MEMBERS_CSV = "membros_extraidos.csv"
RESULTS_CSV = "resultado_adicoes.csv"
CHECKPOINT_FILE = "checkpoint.json"
REPO_URL = "https://raw.githubusercontent.com/SEU_USUARIO/telegram-leads-bot/main"

def check_for_updates():
    """Verifica se há uma versão mais recente disponível."""
    try:
        response = requests.get(f"{REPO_URL}/version.txt", timeout=5)
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != VERSION:
                print(f"\n{Colors.WARNING}🔄 Nova versão disponível: {latest_version}{Colors.ENDC}")
                print(f"{Colors.WARNING}Execute 'update' para atualizar.{Colors.ENDC}")
    except Exception:
        pass

def print_header():
    print(f"""
{Colors.HEADER}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════╗
║        🤖 Robô de Leads Telegram - Versão {VERSION} - INFINIT TEC      ║
║  Extração e Adição de Membros com Checkpoint e Retomada de Execução   ║
╚═══════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
    """)

def get_user_input(prompt, input_type=str, default=None, min_value=None, max_value=None):
    while True:
        try:
            user_input = input(f"{Colors.OKBLUE}{prompt}{Colors.ENDC} ").strip()
            if not user_input and default is not None:
                return default
            if input_type == int:
                value = int(user_input)
                if min_value is not None and value < min_value:
                    print(f"{Colors.FAIL}❌ Valor deve ser pelo menos {min_value}.{Colors.ENDC}")
                    continue
                if max_value is not None and value > max_value:
                    print(f"{Colors.FAIL}❌ Valor deve ser no máximo {max_value}.{Colors.ENDC}")
                    continue
                return value
            elif input_type == list:
                values = [int(x.strip()) for x in user_input.split(",") if x.strip()]
                if not values:
                    return default if default is not None else []
                return values
            return user_input
        except ValueError:
            print(f"{Colors.FAIL}❌ Entrada inválida. Tente novamente.{Colors.ENDC}")

def load_sessions():
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)
        return []
    return [os.path.join(SESSIONS_DIR, f) for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]

async def create_default_session(api_id, api_hash):
    session_path = os.path.join(SESSIONS_DIR, DEFAULT_SESSION)
    print(f"\n{Colors.WARNING}⚠️ Criando session padrão: {DEFAULT_SESSION}.session{Colors.ENDC}")
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"{Colors.WARNING}🔑 Fazendo login no Telegram...{Colors.ENDC}")
        await client.start()
    await client.disconnect()
    return session_path

def select_sessions(sessions, api_id, api_hash):
    if not sessions:
        create = get_user_input("\n🔘 Nenhuma session encontrada. Criar uma nova? (s/n): ", default="s").lower() == "s"
        if not create:
            return []
        session_path = asyncio.run(create_default_session(api_id, api_hash))
        return [session_path]

    print(f"\n{Colors.OKBLUE}📋 Sessions disponíveis:{Colors.ENDC}")
    for i, session in enumerate(sessions, 1):
        print(f"{i}. {os.path.basename(session)}")

    use_all = get_user_input("\n🔘 Usar todas as sessions? (s/n): ", default="n").lower() == "s"
    if use_all:
        return sessions

    print(f"\n{Colors.WARNING}💡 Digite '0' para criar uma nova session.{Colors.ENDC}")
    num_sessions = len(sessions)
    selected_indices = get_user_input(
        f"🔢 Informe os números das sessions (0 para nova, 1-{num_sessions}): ",
        input_type=list,
        min_value=0,
        max_value=num_sessions
    )

    selected_sessions = []
    for idx in selected_indices:
        if idx == 0:
            new_session_path = asyncio.run(create_default_session(api_id, api_hash))
            selected_sessions.append(new_session_path)
        elif 1 <= idx <= num_sessions:
            selected_sessions.append(sessions[idx - 1])

    return selected_sessions if selected_sessions else sessions

async def get_telegram_client(api_id, api_hash, session_file):
    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print(f"\n{Colors.WARNING}⚠️ Session {os.path.basename(session_file)} não autorizada.{Colors.ENDC}")
        print(f"{Colors.WARNING}🔑 Fazendo login no Telegram...{Colors.ENDC}")
        await client.start()
    return client

async def is_admin(client, group, user_id):
    try:
        participant = await client(GetParticipantRequest(group, user_id))
        return isinstance(participant.participant, ChannelParticipantAdmin)
    except Exception:
        return False

async def get_user_last_active_days(user):
    if isinstance(user.status, UserStatusOnline):
        return 0
    elif isinstance(user.status, UserStatusRecently):
        return random.randint(0, 1)
    elif isinstance(user.status, UserStatusLastWeek):
        return random.randint(1, 7)
    elif isinstance(user.status, UserStatusLastMonth):
        return random.randint(7, 30)
    else:
        return 999

async def extract_members(client, source_group, max_inactive_days):
    try:
        print(f"\n{Colors.OKBLUE}🔍 Extraindo membros ativos de {source_group} (máx {max_inactive_days} dias inativos)...{Colors.ENDC}")
        group = await client.get_entity(source_group)
        active_members = []

        async for user in client.iter_participants(group):
            if user.bot or not user.username or user.username.lower().endswith('bot'):
                continue
            if await is_admin(client, group, user.id):
                print(f"{Colors.WARNING}👑 Pulando administrador: @{user.username}{Colors.ENDC}")
                continue
            inactive_days = await get_user_last_active_days(user)
            if inactive_days > max_inactive_days:
                continue
            active_members.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'inactive_days': inactive_days,
                'status': 'pending'
            })

        if not active_members:
            print(f"{Colors.FAIL}❌ Nenhum membro ativo encontrado.{Colors.ENDC}")
            return pd.DataFrame()

        df = pd.DataFrame(active_members)
        df.to_csv(MEMBERS_CSV, index=False)
        print(f"{Colors.OKGREEN}✅ {len(df)} membros extraídos e salvos em '{MEMBERS_CSV}'.{Colors.ENDC}")
        return df

    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro ao extrair membros: {e}{Colors.ENDC}")
        return pd.DataFrame()

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {'last_processed': None, 'success_count': 0, 'fail_count': 0, 'last_error': None}

def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=4)

def update_results_csv(username, status, reason=None):
    file_exists = os.path.exists(RESULTS_CSV)
    with open(RESULTS_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['username', 'status', 'reason', 'timestamp'])
        writer.writerow([username, status, reason or '', datetime.now().isoformat()])

async def is_user_in_group(client, group, user_id):
    try:
        async for participant in client.iter_participants(group):
            if participant.id == user_id:
                return True
        return False
    except Exception:
        return False

async def add_members(client, target_group, usuarios, checkpoint):
    try:
        group = await client.get_entity(target_group)
        print(f"\n{Colors.OKBLUE}📤 Iniciando adição de {len(usuarios)} membros a {target_group}...{Colors.ENDC}")

        last_processed = checkpoint.get('last_processed')
        start_index = 0
        if last_processed and last_processed in usuarios:
            start_index = usuarios.index(last_processed) + 1
            print(f"{Colors.WARNING}🔄 Retomando a partir do usuário: @{last_processed}{Colors.ENDC}")

        for username in usuarios[start_index:]:
            try:
                user_entity = await client.get_entity(username)
                await client(InviteToChannelRequest(group, [user_entity]))

                await asyncio.sleep(5)

                if await is_user_in_group(client, group, user_entity.id):
                    print(f"{Colors.OKGREEN}✅ @{username} adicionado e confirmado!{Colors.ENDC}")
                    update_results_csv(username, 'success')
                    checkpoint['success_count'] += 1
                else:
                    print(f"{Colors.FAIL}❌ @{username} NÃO entrou no grupo.{Colors.ENDC}")
                    update_results_csv(username, 'failed', 'Convite não aceito')
                    checkpoint['fail_count'] += 1

                checkpoint['last_processed'] = username
                save_checkpoint(checkpoint)

                wait_time = random.randint(70, 150)
                print(f"{Colors.WARNING}⏳ Aguardando {wait_time}s (anti-ban)...{Colors.ENDC}")
                await asyncio.sleep(wait_time)

            except FloodWaitError as e:
                print(f"{Colors.WARNING}⚠️ FloodWait! Pausando por {e.seconds}s...{Colors.ENDC}")
                await asyncio.sleep(e.seconds)
                checkpoint['last_processed'] = username
                checkpoint['last_error'] = f"FloodWaitError: {e.seconds}s"
                save_checkpoint(checkpoint)
                print(f"{Colors.FAIL}❌ Interrompido por FloodWaitError. Retome depois.{Colors.ENDC}")
                return False

            except PeerFloodError:
                print(f"{Colors.FAIL}❌ PeerFloodError: Conta bloqueada para adições.{Colors.ENDC}")
                checkpoint['last_processed'] = username
                checkpoint['last_error'] = "PeerFloodError"
                save_checkpoint(checkpoint)
                return False

            except (UserPrivacyRestrictedError, UserNotMutualContactError):
                print(f"{Colors.WARNING}🔒 @{username} não permite adição. Pulando...{Colors.ENDC}")
                update_results_csv(username, 'failed', 'Privacidade restrita')
                checkpoint['fail_count'] += 1

            except Exception as e:
                print(f"{Colors.FAIL}❌ Erro ao adicionar @{username}: {e}{Colors.ENDC}")
                update_results_csv(username, 'failed', str(e))
                checkpoint['fail_count'] += 1

        return True

    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro no processo de adição: {e}{Colors.ENDC}")
        checkpoint['last_error'] = str(e)
        save_checkpoint(checkpoint)
        return False

async def process_session(client, session_file, source_group, target_group, limit, max_inactive_days):
    try:
        print(f"\n{Colors.BOLD}🔄 Processando session: {os.path.basename(session_file)}{Colors.ENDC}")

        df = await extract_members(client, source_group, max_inactive_days)
        if df.empty:
            return

        usuarios = df['username'].dropna().tolist()[:limit]
        if not usuarios:
            print(f"{Colors.FAIL}❌ Nenhum usuário válido para adicionar.{Colors.ENDC}")
            return

        checkpoint = load_checkpoint()
        print(f"\n{Colors.OKBLUE}📊 Estatísticas anteriores:")
        print(f"   Sucessos: {checkpoint['success_count']}")
        print(f"   Falhas: {checkpoint['fail_count']}")
        if checkpoint['last_processed']:
            print(f"   Último processado: @{checkpoint['last_processed']}")
        if checkpoint['last_error']:
            print(f"   Último erro: {checkpoint['last_error']}{Colors.ENDC}")

        success = await add_members(client, target_group, usuarios, checkpoint)
        if not success:
            print(f"\n{Colors.FAIL}❌ Execução interrompida. Você pode retomar depois.{Colors.ENDC}")
            print(f"{Colors.OKGREEN}✅ Progresso salvo. Sucessos: {checkpoint['success_count']}, Falhas: {checkpoint['fail_count']}{Colors.ENDC}")
            if checkpoint['last_processed']:
                print(f"   Parou em: @{checkpoint['last_processed']}")
            if checkpoint['last_error']:
                print(f"   Motivo: {checkpoint['last_error']}{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}❌ Erro na session {os.path.basename(session_file)}: {e}{Colors.ENDC}")

async def main():
    print_header()
    check_for_updates()

    print(f"{Colors.BOLD}{Colors.UNDERLINE}Configurações Iniciais{Colors.ENDC}")
    api_id = get_user_input("🔑 Informe sua API_ID do Telegram: ", int)
    api_hash = get_user_input("🔑 Informe sua API_HASH do Telegram: ")
    source_group = get_user_input("📥 Grupo de ORIGEM (ex: @meu_grupo): ")
    target_group = get_user_input("📤 Grupo de DESTINO (ex: @meu_grupo): ")
    limit = get_user_input("📊 Quantidade de membros a adicionar por session: ", int, default=10, min_value=1)
    max_inactive_days = get_user_input("📅 Membros ativos nos últimos X dias (0 = todos): ", int, default=30, min_value=0)

    sessions = load_sessions()
    selected_sessions = select_sessions(sessions, api_id, api_hash)

    if not selected_sessions:
        print(f"{Colors.FAIL}❌ Nenhuma session selecionada ou criada.{Colors.ENDC}")
        return

    for session_file in selected_sessions:
        client = None
        try:
            client = await get_telegram_client(api_id, api_hash, session_file)
            await process_session(client, session_file, source_group, target_group, limit, max_inactive_days)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ Operação cancelada pelo usuário.{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.FAIL}❌ Erro com {os.path.basename(session_file)}: {e}{Colors.ENDC}")
        finally:
            if client:
                await client.disconnect()

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ Operação concluída ou interrompida.{Colors.ENDC}")

if __name__ == "__main__":
    asyncio.run(main())