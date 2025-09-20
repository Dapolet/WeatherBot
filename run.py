import subprocess
import time
import sys
BOT_FILE = 'bot.py'
while True:
    try:
        print('🚀 Запуск бота...')
        process = subprocess.Popen([sys.executable, BOT_FILE])
        process.wait()
    except KeyboardInterrupt:
        print('⛔ Остановлено пользователем.')
        break
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    print('🔄 Перезапуск через 5 секунд...')
    time.sleep(5)
