import os, time, datetime, random, sys
import pathlib, shutil, requests, tempfile

from rclone_python import rclone
# from rich.progress import (Progress,TextColumn,BarColumn,TaskProgressColumn,TransferSpeedColumn)

message_info = ""

def init_config():
    conf = """
        BackupFolder = "D:\\YandexDisk\\Save"

        MinEmptySpaceInGB = 10
        ReviewPeriodInDay = 7 
    """.strip('\n')

    return conf


def read_config():
    firma_name, backup_folder, remote_folder, telegram_bot, telegram_bot_token, telegram_bot_users = "", "", "", "", "", []
    min_empty_space, review_period, depth_folder = 10, 5, 3

    dir = os.path.abspath(os.curdir)
    filename = dir + "\\config.ini"
    if os.path.isfile(filename):
        with open(filename, mode='r') as f:
            lines = f.readlines()
    else:
        conf = init_config()
        lines = conf.split("\n")

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
        elif command == "BackupFolder".lower():
            backup_folder = params.replace('"', '')
            backup_folder = backup_folder.replace('/', '\\')
            if backup_folder[-1] != '\\': backup_folder += '\\'
        elif command == "RemoteFolder".lower():
            remote_folder = params.replace('"', '')
        elif command == "TelegramBot".lower():
            telegram_bot = params.replace('"', '')
        elif command == "TelegramBotToken".lower():
            telegram_bot_token = params.replace('"', '')
        elif command == "TelegramBotUsers".lower():
            telegram_bot_users = params.replace('"', '')
            bot_users = telegram_bot_users.split(";")

            telegram_bot_users = []
            for b_user in bot_users:
                telegram_bot_users.append(b_user.split(","))

        elif command == "MinEmptySpaceInGB".lower():
            min_empty_space = int(params)
        elif command == "ReviewPeriodInDay".lower():
            review_period = int(params)
        elif command == "DepthFolderFind".lower():
            depth_folder = int(params)

    return firma_name, backup_folder, remote_folder, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, telegram_bot_users


def read_dir(path):
    file_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.zip') or file.endswith('.rar') or file.endswith('.7z'):
                full_path = os.path.join(root, file)
                time_obj = time.strptime(time.ctime(os.path.getctime(full_path)))
                time_stamp = time.strftime("%d.%m.%Y", time_obj)
                date_obj = datetime.datetime(time_obj.tm_year, time_obj.tm_mon, time_obj.tm_mday)
                file_list.append([file, time_stamp, full_path, date_obj])
    file_list.sort(key=lambda fl: fl[3], reverse=True)
    return file_list


def print_error(msg):
    global message_info
    message_info += "\n<b>ОШИБКА</b>: " + msg

    msg = msg.replace("<b>", "").replace("</b>", "")
    print("\nОШИБКА: " + msg)


def print_info(msg):
    global message_info
    message_info += msg + "\n"

    msg = msg.replace("<b>", "").replace("</b>", "")
    print(msg)


def test_read_write(backup_folder):
    # проверим существует ли папка с архивами
    if not os.path.isdir(backup_folder):
        print_error("Папка с архивами не найдена")
        return False
    print_info("<b>Локальная папка с архивами найдена</b>: " + backup_folder)

    # проверим есть ли доступ по чтению и записи
    random.seed()
    rand = str(random.randint(1000, 9999))
    filename = backup_folder + "__test_file_" + rand + ".txt"
    test_str = "Test read/write"
    try:
        with open(filename, mode='w') as f:
            f.write(test_str)
    except:
        print_error("Не могу записать в папку с архивами: " + ValueError)
        return False

    try:
        with open(filename, mode='r') as f:
            lines = f.readlines()
            if test_str != lines[0]:
                print_error("Считываются некорректные данные из папки с архивами: " + ValueError)
                return False
    except:
        print_error("Не прочитать данные из файлов с архивами: " + ValueError)
        return False

    try:
        os.remove(filename)
    except:
        print_error("Не могу удалять файлы из папки с архивами: " + ValueError)
        return False

    print_info(" + есть доступ по чтению и записи")
    return True


def check_new_archives(file_list, review_period):
    current_date = datetime.datetime.now()  # текущая дата
    old_date = current_date - datetime.timedelta(days=review_period)  # минус столько дней
    old_date = datetime.datetime.combine(old_date, datetime.time.min)  # сдвинем на начало дня

    file_new = []
    for file_arc in file_list:
        if file_arc[3] > old_date:
            if len(file_new) < 3:
                file_new.append(file_arc[0])
            else:
                break
    if len(file_new) > 0:
        file_str = ""
        for nn, ff in enumerate(file_new):
            file_str += ff
            if nn + 1 < len(file_new): file_str += ", "
        print_info(" + найдены свежие архивы: " + file_str)
        return True

    print_error("В папке с архивами за " + str(review_period) + " дней нет новых файлов")
    return False


def check_disk_space(backup_folder, min_empty_space):
    gb = 10 ** 9

    try:
        drive = pathlib.PurePath(backup_folder).drive
        total_b, used_b, free_b = shutil.disk_usage(drive)
        total_gb, used_gb, free_gb = round(total_b / gb, 2), round(used_b / gb, 2), round(free_b / gb, 2)
    except:
        print_error("Не могу проверить размер свободного места на диске с архивами: " + ValueError)
        return False

    if free_gb < min_empty_space:
        print_error("На диске с архивами мало свободного места: " + str(free_gb) + " гб")
        return False

    print_info(" + на диске с архивами свободного места: " + str(free_gb) + " гб")
    return True


def check_new_archives_rclone(remote_folder, review_period, depth_folder):
    current_date = datetime.datetime.now()  # текущая дата
    old_date = current_date - datetime.timedelta(days=review_period)  # минус столько дней
    old_date = datetime.datetime.combine(old_date, datetime.time.min)  # сдвинем на начало дня

    file_new = []
    remote_file_list = rclone.ls(remote_folder, files_only=True, max_depth=depth_folder)
    remote_file_list = sorted(remote_file_list, key=lambda d: d['ModTime'], reverse=True)
    for file_arc in remote_file_list:
        mod_time = file_arc["ModTime"]
        if mod_time.find(".") >= 0:
            mod_time = file_arc["ModTime"].partition('.')[0]
        elif mod_time.find("+") >= 0:
            mod_time = file_arc["ModTime"].partition('+')[0]
        file_data = time.strptime(mod_time, "%Y-%m-%dT%H:%M:%S")
        file_data = datetime.datetime(file_data.tm_year, file_data.tm_mon, file_data.tm_mday)

        if file_data >= old_date:
            if len(file_new) < 3:
                file_new.append(file_arc["Name"])
            else:
                break
    if len(file_new) > 0:
        file_str = ""
        for nn, ff in enumerate(file_new):
            file_str += ff
            if nn + 1 < len(file_new): file_str += ", "
        print_info(" + в облаке найдены свежие архивы: " + file_str)
    else:
        print_error("В облаке за " + str(review_period) + " дней нет новых файлов")

    return remote_file_list


def check_skipped_archives_rclone(file_list, remote_file_list, review_period):
    current_date = datetime.datetime.now()  # текущая дата
    old_date = current_date - datetime.timedelta(days=review_period)  # минус столько дней
    old_date = datetime.datetime.combine(old_date, datetime.time.min)  # сдвинем на начало дня

    remove_ext = False
    for file_arc_remote in remote_file_list:
        mod_time = file_arc_remote["ModTime"]
        if mod_time.find(".") >= 0:
            mod_time = file_arc_remote["ModTime"].partition('.')[0]
        elif mod_time.find("+") >= 0:
            mod_time = file_arc_remote["ModTime"].partition('+')[0]
        file_data = time.strptime(mod_time, "%Y-%m-%dT%H:%M:%S")
        file_data = datetime.datetime(file_data.tm_year, file_data.tm_mon, file_data.tm_mday)
        if file_data < old_date: continue

        file_name_remote = file_arc_remote["Name"]
        for nn, file_arc in enumerate(file_list):
            if file_arc[3] < old_date: continue

            file_name = file_arc[0]
            file_name_remote_name, file_name_remote_ext = os.path.splitext(file_name_remote)
            file_name_name, file_name_ext = os.path.splitext(file_name)
            if file_name_remote == file_name or file_name_remote_name == file_name_name or file_name_remote == file_name_name:
                file_list.pop(nn)
                if file_name_remote != file_name:
                    remove_ext = True
                break
        if len(file_list) == 0: break

    skipped_file_list = []
    if len(file_list) > 0:
        file_str, count = "", 0
        for nn, file_arc in enumerate(file_list):
            if file_arc[3] < old_date: continue
            file_str += file_arc[0]
            count += 1
            if nn + 1 < len(file_list): file_str += ", "
            skipped_file_list.append(file_arc)
        if file_str != "":
            print_error("В облаке за " + str(review_period) + " дней не загруженно " + str(
                count) + " архивов. Список пропущенных архивов: " + file_str)
        else:
            print_info(" + В облаке за " + str(review_period) + " дней загружены все архивы")
    else:
        print_info(" + В облаке за " + str(review_period) + " дней загружены все архивы")
    return skipped_file_list, remove_ext

def get_telegram_bot_users(telegram_bot, telegram_bot_token):
    # получить ИД чата
    url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    data = requests.get(url).json()
    user_set = []
    for chat_msg in data['result']:
        if chat_msg.get('message') != None:
            chat_id = str(chat_msg['message']['chat']['id'])
            chat_user = chat_msg['message']['chat'].get('username')
            if chat_user == None:
                chat_user = chat_msg['message']['chat'].get('first_name')
            if chat_user == None:
                chat_user = chat_msg['message']['chat'].get('last_name')
            if chat_user == None:
                chat_user = "NoName"

            fl_user = False
            for _, ch_id in user_set:
                if chat_id == ch_id:
                    fl_user = True
                    break
            if not fl_user:
                user_set.append([chat_user, chat_id])
    return user_set


def send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, message):
    if telegram_bot == "" or telegram_bot_token == "":
        print("Не заданы настройки для Бота в Телеграм")
        return
    elif len(telegram_bot_users) == 0:
        print("Не настроен список пользователей Телеграм для рассылки")
        return

    if firma_name != "":
        firma_msg = "Отчет о резеревном копировании в: <b>" + firma_name + "</b>\n\n"
    else:
        firma_msg = "Отчет о резеревном копировании\n\n"
    if message.find("ОШИБКА") >= 0:
        firma_msg = "<b>ОШИБКИ!</b> " + firma_msg
    message = firma_msg + message

    print("")
    # отправить сообщение в чат
    print("Отправляем сообщения в Телеграм")
    for chat_user, chat_id in telegram_bot_users:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=HTML"
        data = requests.get(url).json()
        print(" + сообщение - " + chat_user + ": " + str(data['ok']))
    return


def debug_start(telegram_bot, telegram_bot_token):
    # получить Имя чата
    url = f"https://api.telegram.org/bot{telegram_bot_token}/getMyName"
    data = requests.get(url).json()
    telegram_bot_name = data['result']['name']

    # получить ИД чатов
    user_set = get_telegram_bot_users(telegram_bot, telegram_bot_token)
    print("\nПользователи бота: " + telegram_bot_name)
    for chat_user, chat_id in user_set:
        print("  Пользователь: " + chat_user + ", чат ид: " + chat_id)
    if len(user_set) == 0:
        print("  Пользователи не найдены")


def check_cmd_param():
    param_str = "userlist,checkmenu,sendfile,userinfo"
    param_mas = param_str.split(",")

    for param in os.environ:
        param = param.lower()
        if param_mas.count(param) > 0:
            return param
    arg_param = sys.argv[1:]
    if len(arg_param) > 0:
        param = arg_param[0].lower()
        if param_mas.count(param) > 0:
            return param
    return ""


def get_telegram_command_messages(telegram_command, telegram_bot, telegram_bot_token, telegram_bot_users):
    user_messages = []

    # получить сообщения с запросами
    url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    data = requests.get(url).json()
    for chat_msg in data['result']:
        for message_id in ['message', 'edited_message']:
            if chat_msg.get(message_id) == None: continue
            if chat_msg[message_id].get('text') == None: continue
            if chat_msg[message_id].get('forward_date') != None: continue
            msg_text = str(chat_msg[message_id]['text']).strip().lower()
            if msg_text[0] != "/": continue

            if telegram_command != msg_text: continue  # пропускаем левые команды

            chat_id = str(chat_msg[message_id]['from']['id'])
            chat_user = str(chat_msg[message_id]['from']['username'])

            fl_usr = False
            for usr in telegram_bot_users:
                if usr[1] != chat_id: continue
                fl_usr = True
                break
            if not fl_usr: break  # пропускаем левых пользователей

            msg_id = chat_msg[message_id]['message_id']
            msg_date = chat_msg[message_id]['date']
            if chat_msg[message_id].get('edit_date') != None:
                msg_date = chat_msg[message_id]['edit_date']

            fl_msg = False
            for msg in user_messages:
                if msg[1] != chat_id: continue
                if msg_id == msg[3] and msg_date > msg[4]:  # отредактированное сообщение
                    msg[2], msg[4] = msg_text, msg_date
                    fl_msg = True
                elif msg_text == msg[2] and (msg_id > msg[3] or msg_date > msg[4]):  # более поздняя такая же команда
                    msg[3], msg[4] = msg_id, msg_date
                    fl_msg = True

            if not fl_msg:
                user_messages.append([chat_user, chat_id, msg_text, msg_id, msg_date])
    return user_messages


def check_menu_command(telegram_command, telegram_bot, telegram_bot_token, telegram_bot_users):
    app_folder = os.getenv('LOCALAPPDATA') + '\\ArchiveMonitoring'
    if not os.path.isdir(app_folder):
        try:
            os.mkdir(app_folder)
        except:
            return
        if not os.path.isdir(app_folder):
            return
    app_ini = app_folder + '\\' + 'menu_state.ini'

    # прочитаем состояние
    user_command_pred = []
    if os.path.isfile(app_ini):
        with open(app_ini, encoding='utf-8', mode='r') as f:
            lines = f.readlines()
            for nom, stroka in enumerate(lines):
                stroka = stroka.replace('\n', '')
                stroka = stroka.strip()
                if stroka == "": continue
                str_ini = stroka.split(",", 5)
                if len(str_ini) != 5: continue
                str_ini[3], str_ini[4] = int(str_ini[3]), int(str_ini[4])
                user_command_pred.append(str_ini)

    user_command = get_telegram_command_messages(telegram_command, telegram_bot, telegram_bot_token, telegram_bot_users)

    tg_users = []
    if len(user_command) > 0:
        # chat_user,chat_id,msg_text,msg_id,msg_date
        for usr_com in user_command:
            if usr_com[2] != telegram_command: continue
            fl_new = True
            for usr_com_pr in user_command_pred:
                if usr_com_pr[2] != telegram_command: continue
                if usr_com[1] == usr_com_pr[1]:
                    if usr_com[3] > usr_com_pr[3] or usr_com[4] > usr_com_pr[4]:
                        usr_com_pr[3], usr_com_pr[4] = usr_com[3], usr_com[4]
                        tg_users.append([usr_com[0], usr_com[1]])
                        fl_new = False
                    elif usr_com[3] <= usr_com_pr[3] or usr_com[4] <= usr_com_pr[4]:
                        fl_new = False
            if fl_new:
                tg_users.append([usr_com[0], usr_com[1]])
                user_command_pred.append(usr_com)

        # сохраним состояние
        with open(app_ini, encoding='utf-8', mode='w') as f:
            for chat_user, chat_id, msg_text, msg_id, msg_date in user_command_pred:
                f.write(
                    chat_user + "," + str(chat_id) + "," + msg_text + "," + str(msg_id) + "," + str(msg_date) + "\n")
    return tg_users


def send_file(telegram_bot_token, telegram_bot_users):
    def send_photo(chat_id, file_opened):
        api_url = f"https://api.telegram.org/bot{telegram_bot_token}/"
        method = "sendPhoto"
        params = {'chat_id': chat_id}
        files = {'photo': file_opened}
        resp = requests.post(api_url + method, params, files=files)

    def send_document(chat_id, file_opened):
        api_url = f"https://api.telegram.org/bot{telegram_bot_token}/"
        method = "sendDocument"
        params = {'chat_id': chat_id}
        files = {'document': file_opened}
        resp = requests.post(api_url + method, params, files=files)

    send_photo(telegram_bot_users[0][1], open("D:\\1.JPG", 'rb'))
    send_document(telegram_bot_users[0][1], open("D:\\1.pdf", 'rb'))

    return


def show_user_info(telegram_bot, telegram_bot_token, telegram_bot_users):
    message = ""
    # получить пересланные сообщения
    url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    data = requests.get(url).json()
    for chat_msg in data['result']:
        for message_id in ['message', 'edited_message']:
            if chat_msg.get(message_id) == None: continue
            if chat_msg[message_id].get('forward_date') == None or chat_msg[message_id].get(
                'forward_origin') == None: continue

            chat_id = str(chat_msg[message_id]['from']['id'])
            fl_usr = False
            for usr in telegram_bot_users:
                if usr[1] != chat_id: continue
                fl_usr = True
                break
            if not fl_usr: break  # пропускаем левых пользователей
            msg = ""

            forw_msg = chat_msg[message_id]['forward_origin']
            if forw_msg.get('sender_user') != None:
                forw_msg = forw_msg['sender_user']
                if forw_msg.get("username") != None:
                    msg += "  User name: " + forw_msg["username"] + "\n"
                if forw_msg.get("first_name") != None:
                    msg += "  First name: " + forw_msg["first_name"] + "\n"
                if forw_msg.get("last_name") != None:
                    msg += "  Last name: " + forw_msg["last_name"] + "\n"
            elif forw_msg.get('sender_user_name') != None:
                msg += "  Hidden user name: " + forw_msg["sender_user_name"] + "\n"
            if msg != "":
                message += msg + "\n"

    if message != "":
        message = "Пересланы сообщения от пользователей:\n" + message
        print(message)

        # отправить сообщение в чат
        print("Отправляем сообщения в Телеграм")
        for chat_user, chat_id in telegram_bot_users:
            url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=HTML"
            data = requests.get(url).json()
            print(" + сообщение - " + chat_user + ": " + str(data['ok']))

    return

def test_rclone(remote_folder, min_empty_space):
    gb = 10 ** 9

    if not rclone.is_installed():
        print_error("Не установлен RClone.\n  Добавьте путь к программе в переменную окружения PATH")
        return False
    print_info("\n<b>Найден установленный RClone</b>")

    remote_path = remote_folder.split(":")
    if len(remote_path) <= 1:
        print_error("Не корректный формат записи подключения к облаку для RClone")
        return False

    remote_connection = remote_path[0]
    if not rclone.check_remote_existing(remote_connection):
        print_error("Не настроена в конфигурации RClone подключение к облаку")
        return False
    print_info(" + успешное подключение к облаку: " + remote_connection)

    space_list = rclone.about(remote_connection)
    empty_space = space_list.get("free")
    if empty_space == None:
        print_error("Не могу проверить размер свободного места в облаке: " + remote_connection)
        return False

    free_gb = round(empty_space / gb, 2)
    if free_gb < min_empty_space:
        print_error("На диске в облаке мало свободного места: " + str(free_gb) + " гб")

    print_info(" + в облаке свободного места: " + str(free_gb) + " гб")

    return True

def send_skipped_files(skipped_file_list, backup_folder, remote_folder, review_period, remove_ext):
    if len(skipped_file_list)==0: return
    maxage = "max-age "+str(review_period)+"d"
    backup_folder = backup_folder[:-1] if backup_folder[-1]=="\\" else backup_folder # уберем слэш в конце

    print("")
    print("отправим в облако пропущенные файлы")

    tmp_folder = tempfile.mkdtemp()

    for file_path in skipped_file_list:
        src_file = file_path[2]
        dst_file = src_file.replace(backup_folder,tmp_folder)
        if remove_ext:
            dst_file = os.path.splitext(dst_file)[0]

        src_file0= src_file.replace(backup_folder,"")[1:]
        if src_file0.rfind("\\")>=0:
            src_file0 = src_file0.replace(file_path[0],"")
            tmp_folder0 = tmp_folder+"\\"+src_file0
            if not os.path.exists(tmp_folder0):
                os.makedirs(tmp_folder0)

        shutil.copyfile(src_file, dst_file)

    # pbar = Progress(TextColumn("[progress.description]{task.description}"),BarColumn(),TaskProgressColumn(),TransferSpeedColumn())
    rclone.copy(tmp_folder, remote_folder, ignore_existing=False, show_progress=True) # , args=['--' + maxage]

    shutil.rmtree(tmp_folder)

def main():
    global message_info
    firma_name, backup_folder, remote_folder, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, telegram_bot_users = read_config()

    param = check_cmd_param()
    if param == "userlist":
        debug_start(telegram_bot, telegram_bot_token)
        return
    elif param == "checkmenu":
        show_user_info(telegram_bot, telegram_bot_token, telegram_bot_users)  # пасхалка
        telegram_bot_users = check_menu_command("/status", telegram_bot, telegram_bot_token, telegram_bot_users)
        if len(telegram_bot_users) == 0: return

    print("\nЗапуск анализатора...\n")
    #########################################################################################
    # работаем с папкой на Диске

    # проверим существует ли папка с архивами, есть ли доступ по чтению и записи
    test_read_write(backup_folder)

    # проверим свободное место на диске
    check_disk_space(backup_folder, min_empty_space)

    # проверим список архивов, создаются ли новые архивы за указанный контрольный период
    file_list = read_dir(backup_folder)
    check_new_archives(file_list, review_period)

    #########################################################################################
    # работаем с RClone
    skipped_file_list, remove_ext = [], False

    # проверим установлен ли rclone, настроено ли подключение и есть ли свободное место в облаке
    if test_rclone(remote_folder, min_empty_space):
        # проверим копируются ли в облако новые архивы за указанный контрольный период
        remote_list = check_new_archives_rclone(remote_folder, review_period, depth_folder)

        # сопоставим последние архивы на диске с теми что загружены в облако - есть ли пропущенные
        skipped_file_list, remove_ext = check_skipped_archives_rclone(file_list, remote_list, review_period)

    #########################################################################################
    # работаем с Telegram

    # отправим сообщение боту в Телеграм
    send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users, message_info)

    # отправим в облако пропущенные файлы
    send_skipped_files(skipped_file_list, backup_folder, remote_folder, review_period, remove_ext)

    # print(message_info)
    return

main()
