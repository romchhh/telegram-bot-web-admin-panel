import asyncio
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.settings_db import update_mailing_status, get_scheduled_mailings
from utils.cron_functions import send_mailing_to_users
from aiogram import Bot

from config import token



class MailingCronDaemon:
    def __init__(self, token: str):
        self.token = token
        self.bot = None
        
    async def init_bot(self):
        try:
            self.bot = Bot(token=self.token)
            return True
        except Exception as e:
            print(f"❌ Error initializing bot: {e}")
            return False
    
    async def close_bot(self):
        if self.bot:
            try:
                await self.bot.session.close()
            except Exception as e:
                print(f"❌ Error closing bot session: {e}")
    
    async def check_and_send_scheduled_mailings(self):
        try:
            # Використовуємо локальний час (київський)
            current_time = datetime.now()
            print(f"🕐 Cron check at: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Киев)")
            
            scheduled_mailings = get_scheduled_mailings()
            
            if not scheduled_mailings:
                print("📭 No scheduled mailings found")
                return
            
            print(f"📋 Found {len(scheduled_mailings)} scheduled mailings")
            
            
            for mailing in scheduled_mailings:
                mailing_id = mailing[0]
                mailing_name = mailing[1]
                scheduled_at_str = mailing[10]  # scheduled_at
                is_recurring = mailing[13]  # is_recurring
                
                print(f"📧 Checking mailing '{mailing_name}' (ID: {mailing_id})")
                print(f"   Scheduled at: {scheduled_at_str}")
                print(f"   Is recurring: {is_recurring}")
                
                if not scheduled_at_str:
                    print(f"   ⚠️ No scheduled_at time")
                    continue
                
                try:
                    # Парсимо київський час у форматі YYYY-MM-DDTHH:MM
                    if 'T' in scheduled_at_str:
                        if '+00:00' in scheduled_at_str:
                            # Убираем UTC offset
                            scheduled_at_str = scheduled_at_str.replace('+00:00', '')
                        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%dT%H:%M')
                    else:
                        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Сравниваем время с точностью до минуты
                    current_time_minutes = current_time.replace(second=0, microsecond=0)
                    scheduled_at_minutes = scheduled_at.replace(second=0, microsecond=0)
                    
                    if current_time_minutes >= scheduled_at_minutes:
                        print(f"📤 Sending mailing '{mailing_name}' (ID: {mailing_id})")
                        print(f"   Current time: {current_time_minutes.strftime('%Y-%m-%d %H:%M')} (Киев)")
                        print(f"   Scheduled time: {scheduled_at_minutes.strftime('%Y-%m-%d %H:%M')} (Киев)")
                        
                        success = await send_mailing_to_users(self.bot, mailing_id)
                        
                        if success:
                            # Для обычных рассылок обновляем статус на 'sent'
                            # Для повторяющихся рассылок schedule_next_recurring уже вызывается в send_mailing_to_users
                            from database.settings_db import get_mailing_by_id
                            mailing_data = get_mailing_by_id(mailing_id)
                            if not mailing_data.get('is_recurring'):
                                update_mailing_status(mailing_id, 'sent')
                            
                            print(f"✅ Mailing '{mailing_name}' sent successfully")
                        else:
                            update_mailing_status(mailing_id, 'failed')
                            print(f"❌ Failed to send mailing '{mailing_name}'")
                    else:
                        time_diff = scheduled_at_minutes - current_time_minutes
                        minutes_left = int(time_diff.total_seconds() / 60)
                        print(f"⏳ Mailing '{mailing_name}' scheduled in {minutes_left} minutes")
                    
                except Exception as e:
                    print(f"❌ Error processing mailing {mailing_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error checking scheduled mailings: {e}")
    
    async def run_daemon(self):
        print("🚀 Starting cron daemon for mailings...")
        
        if not await self.init_bot():
            print("❌ Failed to initialize bot. Stopping...")
            return
        
        try:
            while True:
                await self.check_and_send_scheduled_mailings()
                
                print("⏳ Waiting 1 minute before next check...")
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            print("\n🛑 Received shutdown signal...")
        except Exception as e:
            print(f"❌ Critical error in daemon: {e}")
        finally:
            await self.close_bot()
            print("✅ Daemon stopped")


def main():
    print("📢 Cron daemon for scheduled mailings")

    daemon = MailingCronDaemon(token)
    
    try:
        asyncio.run(daemon.run_daemon())
    except Exception as e:
        print(f"❌ Error starting daemon: {e}")


if __name__ == "__main__":
    main()
