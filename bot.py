import telebot
import schedule
import time
import datetime
from datetime import timedelta
import sqlite3
import threading
import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', '7599482029:AAF2Y-d07nB3sfQvXSvEj4c5ocUz8KFiiA0')
ADMIN_ID = os.environ.get('ADMIN_ID', '1037845888')
WALLET_ADDRESS = os.environ.get('WALLET_ADDRESS', 'Eqt2H5DcZjRrV36VXYq6dq4Zc8RYa3zF4KZrk7FazskW')
PRIVATE_GROUP_ID = os.environ.get('PRIVATE_GROUP_ID', '-1002384485204')

bot = telebot.TeleBot(BOT_TOKEN)

def setup_database():
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers
                 (user_id TEXT PRIMARY KEY, 
                  username TEXT, 
                  first_name TEXT,
                  next_payment_date TEXT,
                  payment_amount REAL,
                  payment_method TEXT,
                  status TEXT,
                  join_date TEXT,
                  reminded TEXT DEFAULT 'no')''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_members
                 (user_id TEXT PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  is_subscriber TEXT DEFAULT 'no')''')
    conn.commit()
    conn.close()
    print("✅ Base de datos configurada")

def add_group_member(user_id, username, first_name):
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    join_date = datetime.date.today().strftime('%Y-%m-%d')
    c.execute("INSERT OR REPLACE INTO group_members VALUES (?, ?, ?, ?, 'no')",
              (str(user_id), username or 'N/A', first_name or 'N/A', join_date))
    conn.commit()
    conn.close()

def convert_member_to_subscriber(user_id, payment_date, amount, method='crypto'):
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("SELECT username, first_name FROM group_members WHERE user_id = ?", (str(user_id),))
    result = c.fetchone()
    if result:
        username, first_name = result
        join_date = datetime.date.today().strftime('%Y-%m-%d')
        c.execute("INSERT OR REPLACE INTO subscribers VALUES (?, ?, ?, ?, ?, ?, 'active', ?, 'no')",
                  (str(user_id), username, first_name, payment_date, amount, method, join_date))
        c.execute("UPDATE group_members SET is_subscriber = 'yes' WHERE user_id = ?", (str(user_id),))
        conn.commit()
        conn.close()
        return True
    return False

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    if str(message.chat.id) == PRIVATE_GROUP_ID:
        for new_member in message.new_chat_members:
            user_id = new_member.id
            username = new_member.username
            first_name = new_member.first_name
            add_group_member(user_id, username, first_name)
            notification = f"""🆕 **NUEVO MIEMBRO DETECTADO**

👤 **Nombre:** {first_name}
🔗 **Username:** @{username if username else 'N/A'}
🆔 **ID:** {user_id}
📅 **Fecha:** {datetime.date.today().strftime('%Y-%m-%d')}

**Para convertir en suscriptor:**
/convert {user_id} 2024-MM-DD MONTO crypto

**Ejemplo:**
/convert {user_id} 2024-08-27 50 crypto"""
            bot.send_message(ADMIN_ID, notification)

@bot.message_handler(content_types=['left_chat_member'])
def member_left(message):
    if str(message.chat.id) == PRIVATE_GROUP_ID:
        left_member = message.left_chat_member
        user_id = left_member.id
        notification = f"""❌ **MIEMBRO SALIÓ DEL GRUPO**

👤 **Nombre:** {left_member.first_name}
🔗 **Username:** @{left_member.username if left_member.username else 'N/A'}
🆔 **ID:** {user_id}"""
        bot.send_message(ADMIN_ID, notification)

def check_pending_payments():
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    today = datetime.date.today()
    reminder_date = today + timedelta(days=2)
    c.execute("SELECT * FROM subscribers WHERE next_payment_date = ? AND status = 'active' AND payment_method = 'crypto' AND reminded = 'no'", 
              (reminder_date.strftime('%Y-%m-%d'),))
    upcoming_payments = c.fetchall()
    for user in upcoming_payments:
        user_id, username, first_name, payment_date, amount, method, status, join_date, reminded = user
        display_name = f"{first_name}" if first_name != 'N/A' else f"@{username}"
        copy_paste_message = f"""📋 **MENSAJE PARA COPIAR Y ENVIAR A {display_name}**

---COPIA DESDE AQUÍ---

🚀 **ALEX CRYPTO UNIVERSE - RECORDATORIO DE PAGO**

¡Hola {first_name if first_name != 'N/A' else username}! 👋

Tu acceso VIP vence en **48 horas** ({payment_date})

💰 **Monto:** {amount}€
⏰ **Vencimiento:** {payment_date}

🪙 **MÉTODOS DE PAGO CRYPTO:**
• USDT (Solana)
• USDC (Solana)  
• SOL (Solana)

📍 **WALLET SOLANA:**
```
{WALLET_ADDRESS}
```

❓ **¿Necesitas otra wallet?** 
Envía DM a @alex.worksout

⚡ **¡No pierdas acceso a las señales ganadoras!**
🎯 **Mantén tu spot en la comunidad VIP**

Gracias por confiar en Alex Crypto Universe 🔥

---HASTA AQUÍ---

✅ **Cuando lo envíes, responde:** /sent_{user_id}"""
        try:
            bot.send_message(ADMIN_ID, copy_paste_message, parse_mode='Markdown')
            c.execute("UPDATE subscribers SET reminded = 'pending' WHERE user_id = ?", (user_id,))
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ Error preparando mensaje para {display_name}: {str(e)}")
    c.execute("SELECT * FROM subscribers WHERE next_payment_date < ? AND status = 'active' AND payment_method = 'crypto'", 
              (today.strftime('%Y-%m-%d'),))
    overdue_payments = c.fetchall()
    for user in overdue_payments:
        user_id, username, first_name, payment_date, amount, method, status, join_date, reminded = user
        display_name = f"{first_name}" if first_name != 'N/A' else f"@{username}"
        overdue_copy_paste = f"""⚠️ **MENSAJE DE PAGO VENCIDO PARA {display_name}**

---COPIA DESDE AQUÍ---

⚠️ **ALEX CRYPTO UNIVERSE - PAGO VENCIDO**

Hola {first_name if first_name != 'N/A' else username},

Tu acceso VIP ha vencido ({payment_date})

Para reactivar tu membresía:

🪙 **Realiza el pago de {amount}€**
📍 **Wallet:** `{WALLET_ADDRESS}`
💬 **Confirma el pago:** @alex.worksout

⚡ **¡Reactiva tu acceso ya para no perderte las próximas señales!**

---HASTA AQUÍ---

**Opciones:**
/paid_{user_id} - Marcar como pagado
/kick_user {user_id} - Expulsar del grupo
/extend_{user_id} - Dar 7 días más"""
        bot.send_message(ADMIN_ID, overdue_copy_paste, parse_mode='Markdown')
        c.execute("UPDATE subscribers SET status = 'overdue' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start_command(message):
    if str(message.from_user.id) == ADMIN_ID:
        admin_message = """🚀 **ALEX CRYPTO UNIVERSE BOT - AUTO-DETECT**

**Funciones automáticas:**
✅ Detecta nuevos miembros en el grupo
✅ Captura IDs automáticamente
✅ Te notifica para convertirlos en suscriptores
✅ Sistema copy/paste para recordatorios

**Comandos:**
/members - Ver miembros del grupo
/subscribers - Ver suscriptores activos
/convert - Convertir miembro en suscriptor
/stats - Estadísticas

**¡100% Profesional y Automático!** 💪"""
    else:
        admin_message = """🚀 **ALEX CRYPTO UNIVERSE**

Para unirte a la comunidad VIP:
👉 Contacta @alex.worksout

¡Accede a señales ganadoras y análisis exclusivos! 🎯"""
    bot.send_message(message.chat.id, admin_message)

@bot.message_handler(commands=['convert'])
def convert_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 5:
            bot.send_message(ADMIN_ID, """**Formato para convertir miembro:**

/convert USER_ID 2024-08-27 50 crypto

**Ejemplo:**
/convert 123456789 2024-08-27 50 crypto""")
            return
        user_id = parts[1]
        payment_date = parts[2]
        amount = float(parts[3])
        method = parts[4]
        if convert_member_to_subscriber(user_id, payment_date, amount, method):
            bot.send_message(ADMIN_ID, f"✅ Miembro {user_id} convertido en suscriptor")
        else:
            bot.send_message(ADMIN_ID, f"❌ No encontré el miembro {user_id}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['members'])
def list_members_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("SELECT * FROM group_members ORDER BY join_date DESC")
    members = c.fetchall()
    conn.close()
    if members:
        response = "👥 **MIEMBROS DEL GRUPO**\n\n"
        for member in members:
            user_id, username, first_name, join_date, is_subscriber = member
            sub_emoji = "💰" if is_subscriber == "yes" else "👤"
            name = f"{first_name}" if first_name != 'N/A' else f"@{username}"
            response += f"{sub_emoji} {name} - ID: {user_id} - {join_date}\n"
    else:
        response = "❌ No hay miembros registrados"
    bot.send_message(ADMIN_ID, response)

@bot.message_handler(commands=['subscribers'])
def list_subscribers_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("SELECT * FROM subscribers ORDER BY next_payment_date")
    subscribers = c.fetchall()
    conn.close()
    if subscribers:
        response = "📋 **ALEX CRYPTO UNIVERSE - SUSCRIPTORES**\n\n"
        total_monthly = 0
        for sub in subscribers:
            user_id, username, first_name, payment_date, amount, method, status, join_date, reminded = sub
            status_emoji = "✅" if status == "active" else "⚠️"
            reminder_emoji = "📨" if reminded == "pending" else "📩" if reminded == "sent" else ""
            total_monthly += amount if status == "active" else 0
            name = f"{first_name}" if first_name != 'N/A' else f"@{username}"
            response += f"{status_emoji} {name} - {amount}€ - {payment_date} ({method}) {reminder_emoji}\n"
        response += f"\n💰 **Ingresos mensuales:** {total_monthly}€"
        response += f"\n👥 **Total miembros:** {len([s for s in subscribers if s[6] == 'active'])}"
    else:
        response = "❌ No hay suscriptores registrados"
    bot.send_message(ADMIN_ID, response)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(payment_amount) FROM subscribers WHERE status = 'active'")
    active_count, total_revenue = c.fetchone()
    c.execute("SELECT COUNT(*) FROM subscribers WHERE payment_method = 'crypto' AND status = 'active'")
    crypto_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subscribers WHERE status = 'overdue'")
    overdue_count = c.fetchone()[0]
    conn.close()
    stats_message = f"""📊 **ALEX CRYPTO UNIVERSE - ESTADÍSTICAS**

👥 **Miembros activos:** {active_count or 0}
💰 **Ingresos mensuales:** {total_revenue or 0}€
🪙 **Pagos crypto:** {crypto_count or 0}
⚠️ **Pagos vencidos:** {overdue_count or 0}

📈 **Proyección anual:** {(total_revenue or 0) * 12}€"""
    bot.send_message(ADMIN_ID, stats_message)

@bot.message_handler(commands=['kick_user'])
def kick_user_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = message.text.split()[1]
        bot.kick_chat_member(PRIVATE_GROUP_ID, int(user_id))
        conn = sqlite3.connect('alex_crypto_subscribers.db')
        c = conn.cursor()
        c.execute("UPDATE subscribers SET status = 'kicked' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ Usuario {user_id} expulsado del grupo")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Error expulsando usuario: {str(e)}")

@bot.message_handler(func=lambda message: message.text.startswith('/sent_'))
def confirm_sent(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    user_id = message.text.split('_', 1)[1]
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("UPDATE subscribers SET reminded = 'sent' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(ADMIN_ID, f"✅ Confirmado: Mensaje enviado al usuario {user_id}")

@bot.message_handler(func=lambda message: message.text.startswith('/paid_'))
def mark_paid(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    user_id = message.text.split('_', 1)[1]
    next_month = (datetime.date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("UPDATE subscribers SET next_payment_date = ?, status = 'active', reminded = 'no' WHERE user_id = ?", 
             (next_month, user_id))
    conn.commit()
    conn.close()
    bot.send_message(ADMIN_ID, f"✅ Pago confirmado. Próximo vencimiento: {next_month}")

@bot.message_handler(func=lambda message: message.text.startswith('/extend_'))
def extend_payment(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    user_id = message.text.split('_', 1)[1]
    new_date = (datetime.date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    conn = sqlite3.connect('alex_crypto_subscribers.db')
    c = conn.cursor()
    c.execute("UPDATE subscribers SET next_payment_date = ?, status = 'active', reminded = 'no' WHERE user_id = ?", 
             (new_date, user_id))
    conn.commit()
    conn.close()
    bot.send_message(ADMIN_ID, f"✅ Extendido 7 días. Nuevo vencimiento: {new_date}")

@bot.message_handler(commands=['check'])
def check_payments_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    bot.send_message(ADMIN_ID, "🔍 Verificando pagos...")
    check_pending_payments()
    bot.send_message(ADMIN_ID, "✅ Verificación completada")

@bot.message_handler(commands=['add_existing'])
def add_existing_subscriber(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 6:
            bot.send_message(ADMIN_ID, """**Formato para agregar suscriptor existente:**

/add_existing USER_ID USERNAME FIRST_NAME 2024-08-27 50 crypto

**Ejemplo:**
/add_existing 123456789 vincenzosolana Vincenzo 2024-08-27 50 crypto""")
            return
        user_id = parts[1]
        username = parts[2]
        first_name = parts[3]
        payment_date = parts[4]
        amount = float(parts[5])
        method = parts[6] if len(parts) > 6 else 'crypto'
        conn = sqlite3.connect('alex_crypto_subscribers.db')
        c = conn.cursor()
        join_date = datetime.date.today().strftime('%Y-%m-%d')
        c.execute("INSERT OR REPLACE INTO subscribers VALUES (?, ?, ?, ?, ?, ?, 'active', ?, 'no')",
                  (user_id, username, first_name, payment_date, amount, method, join_date))
        c.execute("INSERT OR REPLACE INTO group_members VALUES (?, ?, ?, ?, 'yes')",
                  (user_id, username, first_name, join_date))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ {first_name} (@{username}) agregado como suscriptor activo")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Error: {str(e)}")

def schedule_checks():
    schedule.every().day.at("10:00").do(check_pending_payments)
    schedule.every().day.at("18:00").do(check_pending_payments)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    setup_database()
    bot.send_message(ADMIN_ID, """🚀 **ALEX CRYPTO UNIVERSE BOT ACTIVADO**
🤖 **VERSIÓN RAILWAY PRODUCTION**

✅ Detectará automáticamente nuevos miembros
✅ Capturará IDs sin molestar a nadie
✅ Te notificará para conversiones
✅ Ejecutándose 24/7 en Railway

**¡SISTEMA PROFESIONAL EN PRODUCCIÓN!** 💪""")
    print("🚀 Alex Crypto Universe Bot iniciado en Railway")
    print(f"✅ Grupo configurado: {PRIVATE_GROUP_ID}")
    print(f"✅ Wallet configurada: {WALLET_ADDRESS}")
    scheduler_thread = threading.Thread(target=schedule_checks)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    bot.polling(none_stop=True)