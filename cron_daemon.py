import asyncio
import time
import sys
import os
from datetime import datetime
import pytz

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.settings_db import update_mailing_status, get_scheduled_mailings
from utils.cron_functions import send_mailing_to_users
from aiogram import Bot

from config import token



class MailingCronDaemon:
    def __init__(self, token: str):
        self.token = token
        self.bot = None
        self.kyiv_tz = pytz.timezone('Europe/Kiev')
        
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
            
            scheduled_mailings = get_scheduled_mailings()
            
            if not scheduled_mailings:
                print("📭 No scheduled mailings found")
                return
            
            
            for mailing in scheduled_mailings:
                mailing_id = mailing[0]
                mailing_name = mailing[1]
                scheduled_at_str = mailing[10]  # scheduled_at
                
                if not scheduled_at_str:
                    continue
                
                try:
                    # Парсимо київський час у форматі YYYY-MM-DDTHH:MM
                    if 'T' in scheduled_at_str:
                        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%dT%H:%M')
                    else:
                        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M:%S')
                    
                    if current_time >= scheduled_at:
                        print(f"📤 Sending mailing '{mailing_name}' (ID: {mailing_id})")
                        print(f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Киев)")
                        print(f"   Scheduled time: {scheduled_at.strftime('%Y-%m-%d %H:%M:%S')} (Киев)")
                        
                        success = await send_mailing_to_users(self.bot, mailing_id)
                        
                        if success:
                            update_mailing_status(mailing_id, 'sent')
                            print(f"✅ Mailing '{mailing_name}' sent successfully")
                            
                            # Якщо це повторювана розсилка, пересчитываем наступну
                            from database.settings_db import get_mailing_by_id, schedule_next_recurring
                            mailing_data = get_mailing_by_id(mailing_id)
                            if mailing_data and mailing_data.get('is_recurring'):
                                print(f"🔄 Rescheduling recurring mailing '{mailing_name}'")
                                schedule_next_recurring(mailing_id)
                        else:
                            update_mailing_status(mailing_id, 'failed')
                            print(f"❌ Failed to send mailing '{mailing_name}'")
                    else:
                        time_diff = scheduled_at - current_time
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
