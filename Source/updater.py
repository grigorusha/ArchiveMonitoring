import sys, os, time 
import shutil, subprocess, psutil, requests

firma_name, telegram_bot, telegram_bot_token, telegram_bot_users = "", "", "", []
APP_UPDATER = "ArchiveMonitoringUpdater.exe"

def check_and_kill_process(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == process_name.lower():
            print(f"Процесс {process_name} (PID: {proc.info['pid']}) найден, завершаю...")
            fl_kill = False
            for _ in range(5):
                if not proc.is_running():
                    fl_kill = True
                    break
                try:
                    proc.terminate()  # Пробуем мягкое завершение
                    proc.wait(timeout=3)
                    proc.kill()
                    time.sleep(3)
                    print(f"Процесс {process_name} завершен.")
                    fl_kill = True
                    break
                except:
                    time.sleep(3)
            if not fl_kill:
                print(f"Процесс {process_name} не удалось звершить.")
            return fl_kill
    print(f"Процесс {process_name} не найден.")
    return False

def run_as_exe_app(APP_FILENAME):
    # проверим среду исполнения: если отладка (python.exe), то ложь, если автономное приложение, то истина
    current_app_path = sys.executable  # Путь к текущему исполняемому файлу (.exe)
    return os.path.basename(current_app_path).lower()==APP_FILENAME.lower()

def read_config():
    global firma_name, telegram_bot, telegram_bot_token, telegram_bot_users
    firma_name, telegram_bot, telegram_bot_token, telegram_bot_users = "", "", "", []

    dir = os.path.abspath(os.curdir)
    filename = dir + "\\config.ini"
    if os.path.isfile(filename):
        with open(filename, mode='r') as f:
            lines = f.readlines()
    else:
        return

    for nom, stroka in enumerate(lines):
        stroka = stroka.replace('\n', '')
        stroka = stroka.strip()
        if stroka == "": continue

        if stroka[0] == "#": continue
        pos = stroka.find("#")
        if pos >= 0:
            stroka = stroka[0:pos]

        pos = stroka.find("=")
        if pos == -1: continue
        if pos == len(stroka) - 1: continue

        command = stroka[0:pos].strip()
        params = stroka[pos + 1:].strip()

        param_mas = params.split(",")
        for num, par in enumerate(param_mas):
            param_mas[num] = par.strip()

        command = command.lower()
        if command == "FirmaName".lower():
            firma_name = params.replace('"', '')
        elif command == "TelegramBot".lower():
            telegram_bot = params.replace('"', '')
        elif command == "TelegramBotToken".lower():
            telegram_bot_token = params.replace('"', '')
        elif command == "TelegramBotUsers".lower():
            telegram_bot_users = params.replace('"', '')
            bot_users = telegram_bot_users.split(";")
            telegram_bot_users = []
            for b_user in bot_users:
                user_list = b_user.split(",")
                if len(user_list)<2: continue
                telegram_bot_users.append( [user_list[0],user_list[1]] )
    return

def send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, message):
    if telegram_bot == "" or telegram_bot_token == "":
        print("Не заданы настройки для Бота в Телеграм")
        return
    elif len(telegram_bot_users) == 0:
        print("Не настроен список пользователей Телеграм для рассылки")
        return

    if firma_name != "":
        firma_msg = "Обновление приложения мониторинга: <b>" + firma_name + "</b>\n"
    else:
        firma_msg = "Обновление приложения мониторинга\n"
    message = firma_msg + message

    print("")
    # отправить сообщение в чат
    print("Отправляем сообщения в Телеграм")
    chat_user, chat_id = telegram_bot_users[0]
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=HTML"
    data = requests.get(url).json()
    print(" + сообщение - " + chat_user + ": " + str(data['ok']))

def main():
    global firma_name, telegram_bot, telegram_bot_token, telegram_bot_users
    if len(sys.argv)<4:
        print("Запуск только в режиме Обновления...")
        return

    read_config()

    original_file = sys.argv[1]
    new_file = sys.argv[2]
    start_after_update_flag = sys.argv[3]

    print(f"Updater: Замена {original_file} на {new_file}")

    process_name = os.path.basename(original_file)
    check_and_kill_process(process_name)

    backup_path = original_file + ".bak"
    if os.path.exists(backup_path):
        os.remove(backup_path)  # Удаляем старый бэкап, если есть
    shutil.copy(original_file, backup_path)

    try:
        # Удаляем старый файл
        if os.path.exists(original_file):
            try:
                os.remove(original_file)
                print("Updater: Старый файл удален.")
            except OSError as e:
                print(f"Updater: Ошибка удаления старого файла {original_file}: {e}")
                # Попытка переименовать вместо удаления - иногда работает, если файл занят
                try:
                     if os.path.exists(backup_path):
                          os.remove(backup_path) # Удаляем старый бэкап, если есть
                     os.rename(original_file, backup_path)
                     print(f"Updater: Старый файл переименован в {backup_path}.")
                except OSError as e_rename:
                     print(f"Updater: Не удалось переименовать старый файл {original_file}: {e_rename}")
                     print("Updater: Обновление не выполнено из-за занятого файла.")
                     # Попытка запуска новой версии из временного расположения (может не сработать) subprocess.Popen([new_file])
                     send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, "Обновление не выполнено из-за занятого файла.")
                     sys.exit(1) # Выходим с ошибкой

        # Перемещаем скачанный файл на место старого
        shutil.move(new_file, original_file)
        print("Updater: Обновление успешно выполнено.")

        # сначала надо проверить среду исполнения: если отладка (python.exe), то пропускаем, если автономное приложение, то старт
        if run_as_exe_app(APP_UPDATER) and start_after_update_flag.lower()=="yes":
            # Запускаем новую версию приложения
            print(f"Updater: Запуск новой версии {original_file}")
            subprocess.Popen([original_file], creationflags=0)

    except Exception as e:
        print(f"Updater: Критическая ошибка в скрипте обновления: {e}")
        # input("нажмите энтер")
        send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, "Ошибка в скрипте обновления.")

        print("\nПауза 10 сек...")
        time.sleep(10)
        sys.exit(1)
    finally:
        pass

    print("Updater: Скрипт обновления завершен.")
    send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, "Обновление успешно выполнено.")

    print("\nПауза 10 сек...")
    time.sleep(10)
    sys.exit(0) # Скрипт завершился успешно

main()