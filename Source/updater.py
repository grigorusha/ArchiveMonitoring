import sys, os, time 
import shutil, subprocess, psutil, requests

firma_name, telegram_bot, telegram_bot_token, telegram_bot_users = "", "", "", []
APP_UPDATER = "ArchiveMonitoringUpdater.exe"

def check_and_kill_process(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == process_name.lower():
            print(f"Процесс {process_name} (PID: {proc.info['pid']}) найден, завершаю...")
            proc.kill()
            time.sleep(3)
            print(f"Процесс {process_name} завершен.")
            return True
    print(f"Процесс {process_name} не найден.")
    return False

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
    read_config()

    original_file = sys.argv[1]
    new_file = sys.argv[2]

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
        current_app_path = sys.executable  # Путь к текущему исполняемому файлу (.exe)
        if current_app_path.lower()==APP_UPDATER.lower():
            # Запускаем новую версию приложения
            print(f"Updater: Запуск новой версии {original_file}")
            subprocess.Popen([original_file], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)

    except Exception as e:
        print(f"Updater: Критическая ошибка в скрипте обновления: {e}")
        # input("нажмите энтер")
        send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, "Ошибка в скрипте обновления.")
        sys.exit(1)
    finally:
        pass
        # # Удаляем временный скрипт обновления
        # updater_script_path = sys.argv[0]  # Путь к этому скрипту
        # print("Updater: Удаление временного скрипта обновления.")
        # try:
        #     # Добавляем небольшую задержку перед удалением самого себя
        #     time.sleep(1)
        #     os.remove(updater_script_path)
        # except OSError as e:
        #     print(f"Updater: Ошибка удаления скрипта обновления {updater_script_path}: {e}")

    print("Updater: Скрипт обновления завершен.")
    send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, "Обновление успешно выполнено.")
    sys.exit(0) # Скрипт завершился успешно

main()