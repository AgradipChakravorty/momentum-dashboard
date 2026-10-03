import sys
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from main import run_pipeline

def scheduled_job():
    now = datetime.now()
    # Check if current time is within NSE market hours (Mon-Fri, 09:15 to 15:30 IST)
    if now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Triggering market hours pipeline update...")
        run_pipeline()
    else:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Market closed. Skipping update.")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # Runs every 15 minutes
    scheduler.add_job(scheduled_job, 'cron', minute='*/15')
    print("🚀 Automated Market-Hour Scheduler Started...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
