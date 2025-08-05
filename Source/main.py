import os, time, datetime, random, sys, filecmp
import pathlib, tempfile, shutil, subprocess, psutil, requests, threading, pystray
from ping3 import ping
from PIL import Image, ImageDraw
from packaging.version import parse as parse_version # Для надежного сравнения версий
from rclone_python import rclone,utils

VERSION = __version__ = "1.5.2"
GITHUB_OWNER, GITHUB_REPO = "grigorusha", "ArchiveMonitoring"
APP_FILENAME, ZIP_FILENAME, APP_UPDATER = "ArchiveMonitoring.exe", "ArchiveMonitoring.zip", "ArchiveMonitoringUpdater.exe"
fl_update = True

message_info = ""
app_running = new_day = True
tray_icon = pict_icon = None
CHECK_INTERVAL = 10  # Интервал проверки в секундах

firma_name, backup_folder, remote_folder, telegram_bot, telegram_bot_token, telegram_bot_users, telegram_bot_users_work = "", "", "", "", "", [], []
min_empty_space, review_period, depth_folder, time_start = 10, 5, 3, ""
net_server, net_folder, net_folder_user, net_folder_pass = "", "", "", ""

def init_config():
    conf = """
        BackupFolder = "D:\\YandexDisk\\Save"

        MinEmptySpaceInGB = 10
        ReviewPeriodInDay = 7 
    """.strip('\n')

    return conf
def close_spalsh_screen():
    try:  # pyinstaller spalsh screen
        import pyi_splash
        pyi_splash.close()
    except:
        pass

def make_icon():
    global pict_icon
    icon_file = os.path.join(os.path.abspath(os.curdir), "ArchiveMonitoring.ico")
    if os.path.isfile(icon_file):
        # Создаем иконки заранее
        pict_icon = create_icon(icon_file)
    else:
        pict_icon = create_icon_ini( (0,200,0) )

def is_number(s):
    try:
        float(s) # for int, long and float
    except:
        return False
    return True

def typeof(your_var):
    if (isinstance(your_var, bool)):
        return 'bool'
    elif (isinstance(your_var, int)):
        return 'int'
    elif (isinstance(your_var, float)):
        return 'float'
    elif (isinstance(your_var, list)) or (isinstance(your_var, tuple)):
        return 'list'
    elif (isinstance(your_var, dict)):
        return 'dict'
    elif (isinstance(your_var, str)):
        return 'str'
    else:
        return "type is unknown"

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

def create_icon(photo_path):
    # Загружаем оригинальное изображение
    original_image = Image.open(photo_path)
    image = original_image.copy()  # Создаем копию для работы
    image.thumbnail((48, 48))  # Уменьшаем изображение для начального отображения
    return image

def create_icon_ini(color):
    """Создает иконку с кружком указанного цвета"""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((5, 5, 60, 60), fill=color)
    return image

def read_config():
    global firma_name, backup_folder, remote_folder, net_server, net_folder, net_folder_user, net_folder_pass, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, telegram_bot_users, time_start, fl_update

    firma_name, backup_folder, remote_folder, telegram_bot, telegram_bot_token, telegram_bot_users = "", "", "", "", "", []
    min_empty_space, review_period, depth_folder, time_start = 10, 5, 3, ""
    net_server, net_folder, net_folder_user,net_folder_pass = "", "", "", ""
    fl_update = True

    dir = os.path.dirname(os.path.abspath(sys.executable)) if run_as_exe_app(APP_FILENAME) else os.path.dirname(__file__)
    filename = os.path.join(dir,"config.ini")
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
        elif command == "NetServer".lower():
            net_server = params.replace('"', '')
        elif command == "NetFolder".lower():
            net_folder = params.replace('"', '')
        elif command == "NetFolderUser".lower():
            net_folder_user = params.replace('"', '')
        elif command == "NetFolderPass".lower():
            net_folder_pass = params.replace('"', '')
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
        elif command == "MinEmptySpaceInGB".lower():
            min_empty_space = int(params)
        elif command == "ReviewPeriodInDay".lower():
            review_period = int(params)
        elif command == "DepthFolderFind".lower():
            depth_folder = int(params)
        elif command == "Time".lower():
            time_start = str(params)
        elif command == "Update".lower():
            update_str = str(params).lower()
            if update_str=="1" or update_str=="yes":
                fl_update = True
            elif update_str=="0" or update_str=="no":
                fl_update = False

    return


def get_latest_release_info(owner, repo, zip_filename, app_filename):
    # Получает информацию о последнем релизе и URL для скачивания файла.
    # Возвращает кортеж (latest_version_tag, download_url) или (None, None) в случае ошибки.
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    try:
        response = requests.get(api_url, timeout=10) # Добавляем таймаут
        response.raise_for_status() # Вызовет исключение для плохих статусов (4xx или 5xx)
        release_info = response.json()

        latest_tag = release_info.get("tag_name")
        assets = release_info.get("assets", [])

        download_app_url = download_zip_url = None
        for asset in assets:
            if asset.get("name") == app_filename:
                download_app_url = asset.get("browser_download_url")
            if asset.get("name") == zip_filename:
                download_zip_url = asset.get("browser_download_url")

        if not latest_tag or not download_zip_url:
            # print(f"Не удалось найти информацию о последнем релизе или файле '{app_filename}'.")
            return None, None, None

        # print(f"Найдена последняя версия: {latest_tag}")
        return latest_tag, download_zip_url, download_app_url

    except requests.exceptions.RequestException as e:
        # print(f"Ошибка при проверке обновлений: {e}")
        return None, None, None
    except Exception as e:
        # print(f"Неожиданная ошибка при получении информации о релизе: {e}")
        return None, None, None

def download_file(url, destination_path):
    # Скачивает файл по URL в указанное место. Возвращает True при успехе, False при неудаче.
    try:
        # Скачиваем файл потоково, чтобы не держать весь файл в памяти
        with requests.get(url, stream=True, timeout=60) as r: # Таймаут на скачивание
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            with open(destination_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): # Читаем по 8KB
                    f.write(chunk)
                    downloaded_size += len(chunk)
            return True
    except requests.exceptions.RequestException as e:
        # print(f"Ошибка при скачивании файла: {e}")
        # Удаляем недокачанный или поврежденный файл, если он есть
        if os.path.exists(destination_path):
            os.remove(destination_path)
        return False
    except Exception as e:
        # print(f"Неожиданная ошибка при скачивании: {e}")
        if os.path.exists(destination_path):
            os.remove(destination_path)
        return False


def extract_file_from_zip_to_same_dir(zip_file_path, files_to_extract):
    import zipfile
    from pathlib import Path

    # Распаковывает заданный файл из ZIP-архива в ту же папку, где находится архив.
    zip_path_obj = Path(zip_file_path)

    # 1. Проверяем существование ZIP-файла
    if not zip_path_obj.is_file():
        # print(f"Ошибка: ZIP-файл '{zip_file_path}' не найден или не является файлом.")
        return None

    # 2. Определяем целевую директорию для распаковки (папка, где лежит ZIP)
    destination_dir = zip_path_obj.parent

    # 3. Формируем ожидаемый путь к распакованному файлу
    # Важно: zipfile.extract() сохраняет внутреннюю структуру папок, поэтому мы просто присоединяем имя файла, которое может включать подпапки.

    try:
        # Открываем ZIP-архив в режиме чтения
        with zipfile.ZipFile(zip_path_obj, 'r') as zip_arch:
            extracted_files = []
            # 4. Проверяем, существует ли файл внутри архива
            # zipfile.namelist() возвращает список всех элементов (файлов и папок) внутри архива, включая их пути относительно корня архива.
            for file_to_extract_name in files_to_extract:
                extracted_file_full_path = destination_dir / file_to_extract_name
                if file_to_extract_name not in zip_arch.namelist():
                    # print(f"Ошибка: Файл '{file_to_extract_name}' не найден в архиве '{zip_file_path}'.")
                    # print(f"Доступные файлы в архиве: {zip_arch.namelist()}")
                    return None

                # 5. Распаковываем файл
                # print(f"Распаковываем '{file_to_extract_name}' из '{zip_path_obj.name}' в '{destination_dir}'...")
                zip_arch.extract(file_to_extract_name, path=destination_dir)
                extracted_files.append(extracted_file_full_path)

            # print(f"Файл успешно распакован: '{extracted_file_full_path}'")
            return extracted_files
    except Exception as e:
        # print(f"Произошла непредвиденная ошибка при распаковке: {e}")
        return None

def run_as_exe_app(APP_FILENAME):
    # проверим среду исполнения: если отладка (python.exe), то ложь, если автономное приложение, то истина
    current_app_path = sys.executable  # Путь к текущему исполняемому файлу (.exe)
    return os.path.basename(current_app_path).lower()==APP_FILENAME.lower()

def get_file_size(url):
    try:
        response = requests.head(url, allow_redirects=True)
        if response.status_code == 200:
            size = response.headers.get('Content-Length')
            if size:
                return int(size)  # Размер в байтах
            else:
                return None  # Заголовок Content-Length отсутствует
        else:
            return None  # Ошибка запроса
    except requests.RequestException as e:
        print(f"Ошибка: {e}")
        return None

def update_and_restart(download_zip_url, download_app_url=None):
    # если найдена новая версия, то скачиваем Zip. если версия текущая и найден Exe, то обновляем только его.

    # Скачивает новую версию, запускает скрипт обновления и завершает текущее приложение.
    current_app_path = sys.executable # Путь к текущему исполняемому файлу (.exe)

    # сначала надо проверить среду исполнения: если отладка (python.exe), то стоп, если автономное приложение, то старт
    if not run_as_exe_app(APP_FILENAME):
        print("Обновление возможно только в автономном режиме")
        return

    # Создаем временную папку для скачанного файла и скрипта обновления
    # Используем tempfile.TemporaryDirectory для автоматической очистки
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # print(f"Используется временная директория: {tmpdir}")
            parent_directory = os.path.dirname(current_app_path)
            app_updater_path = os.path.join(parent_directory, APP_UPDATER)

            if download_zip_url:
                start_after_update_flag = "yes"
                # 1.1 Скачиваем новую версию - ZIP
                downloaded_zip_path = os.path.join(tmpdir, ZIP_FILENAME)
                if download_file(download_zip_url, downloaded_zip_path):
                    extracted_files = extract_file_from_zip_to_same_dir(downloaded_zip_path, [APP_FILENAME, APP_UPDATER])
                    if not extracted_files: return
                    downloaded_app_path,downloaded_upd_path = extracted_files
                    if not downloaded_app_path: return
                else:
                    # print("Обновление отменено из-за ошибки скачивания.")
                    return
            elif download_app_url:
                start_after_update_flag = "no"
                # 1.2 Скачиваем апдейт - EXE
                downloaded_app_path = os.path.join(tmpdir, APP_FILENAME)
                downloaded_upd_path = ""

                url_file_size = get_file_size(download_app_url)
                file_size = os.path.getsize(current_app_path)
                if url_file_size: # получилось получить размер заранее
                    if url_file_size==file_size:
                        # print("Обновление отменено из-за совпадения размера файлов.")
                        return

                if not download_file(download_app_url, downloaded_app_path):
                    # print("Обновление отменено из-за ошибки скачивания.")
                    return

                if filecmp.cmp(current_app_path, downloaded_app_path, shallow=False):
                    # print("Обновление отменено из-за совпадения содержимого файлов.")
                    return

            else: return
            print("Обновление успешно скачано. Попробуем обновить приложение...")

            # 2. Подготавливаем файлы для обновления
            # Перемещаем скачанный файл основного приложения в дирректорию старого. тк временная папка удалится при запуске обновления
            downloaded_app_path_new = current_app_path + ".copy"
            shutil.move(downloaded_app_path, downloaded_app_path_new)

            # Обновим Updater
            if downloaded_upd_path:
                check_and_kill_process(APP_UPDATER)
                shutil.move(downloaded_upd_path, app_updater_path)

            # 3. Запускаем скрипт обновления как отдельный процесс
            # print("Запуск скрипта обновления...")
            try:
                # Запускаем скрипт с помощью интерпретатора, который запустил текущее приложение
                # Передаем пути к старому и новому файлам в качестве аргументов
                subprocess.Popen([app_updater_path, current_app_path, downloaded_app_path_new, start_after_update_flag],
                                 creationflags=0) # subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP Отключает процесс от родительского (окна консоли) на Windows
                print("Скрипт обновления запущен. Текущее приложение завершается.")
            except Exception as e:
                print(f"Ошибка при запуске скрипта обновления: {e}")
                # Если запуск скрипта обновления не удался, не завершаем приложение
                # print("Не удалось запустить скрипт обновления. Обновление не выполнено.")
                # Очистка временных файлов (хотя TemporaryDirectory должна это сделать)
                if os.path.exists(downloaded_app_path): os.remove(downloaded_app_path)

            # 4. Завершаем текущее приложение
            sys.exit(0)

    except Exception as e:
        pass
        # print(f"Ошибка при работе с временной директорией: {e}")
        # print("Обновление не выполнено.")

def check_update():
    if not fl_update: return

    # Проверяет наличие новой версии и запускает процесс обновления при необходимости.
    for _ in range(5):
        latest_tag, download_zip_url, download_app_url = get_latest_release_info(GITHUB_OWNER, GITHUB_REPO, ZIP_FILENAME, APP_FILENAME)
        if latest_tag and download_zip_url:
            break
        time.sleep(3) # иногда сайт отвечает не с первого раза

    if latest_tag and (download_zip_url or download_app_url):
        version_tag = latest_tag.replace(GITHUB_REPO.lower() + ".", "").lstrip('.').lstrip('v')
        try:
            # Сравниваем версии
            current_v = parse_version(VERSION)
            latest_v = parse_version(version_tag) # Удаляем 'v' если есть в теге
            if latest_v > current_v and download_zip_url:
                print("Проверка обновления: Найдена новая версия "+version_tag+". Ваша версия: "+VERSION)
                update_and_restart(download_zip_url)
                # Важно: если update_and_restart успешно запустит скрипт и вызовет sys.exit(0), код ниже в этой функции выполняться не будет.
            elif latest_v == current_v and download_app_url:
                print("Проверка обновления: Найден апдейт для вашей версии: "+VERSION)
                update_and_restart("",download_app_url)
                # Важно: если update_and_restart успешно запустит скрипт и вызовет sys.exit(0), код ниже в этой функции выполняться не будет.
            else:
                pass
                # print("Проверка обновления: ваша версия новее ...")
        except Exception as e:
            print(f"Проверка обновления: ошибка при запуске обновления: {e}")
    else:
        print("Проверка обновления: не удалось проверить обновления.")

def read_dir(path):
    file_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.zip') or file.endswith('.rar') or file.endswith('.7z'):
                full_path = os.path.join(root, file)
                time_obj = time.strptime(time.ctime(os.path.getmtime(full_path)))
                time_stamp = time.strftime("%d.%m.%Y", time_obj)
                date_obj = datetime.datetime(time_obj.tm_year, time_obj.tm_mon, time_obj.tm_mday)

                file_name = file
                file_name = file_name.replace(time_stamp, "").strip()
                file_name = os.path.splitext(file_name)[0].strip()

                file_list_dict = dict(file_name=file, path=full_path, date_time=date_obj, date=time_stamp, name=file_name, check=False)
                file_list.append(file_list_dict) # ([file, time_stamp, full_path, date_obj, file_name])
    file_list.sort(key=lambda item: item['date_time'], reverse=True) # file_list.sort(key=lambda fl: fl[3], reverse=True)
    return file_list

def print_error(msg):
    global message_info
    message_info += "\n<b>ОШИБКА</b>: " + msg + "\n"

    msg = msg.replace("<b>", "").replace("</b>", "")
    msg = msg.replace("<i>", "").replace("</i>", "")
    print("\nОШИБКА: " + msg)

def print_info(msg):
    global message_info
    message_info += msg + "\n"

    msg = msg.replace("<b>", "").replace("</b>", "")
    msg = msg.replace("<i>", "").replace("</i>", "")
    print(msg)

def test_read_write(backup_folder):
    if backup_folder[-1]!="\\": backup_folder+="\\"

    # проверим существует ли папка с архивами
    if not os.path.isdir(backup_folder):
        print_error("Папка с архивами не найдена")
        return False
    if backup_folder[0:2]=="\\\\":
        print_info("<b>Сетевая папка с архивами найдена</b>: " + backup_folder)
    else:
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
        if file_arc["date_time"] > old_date:
            if len(file_new) < 3:
                file_new.append(file_arc["file_name"])
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
        file_date = time.strptime(mod_time, "%Y-%m-%dT%H:%M:%S")
        file_date = datetime.datetime(file_date.tm_year, file_date.tm_mon, file_date.tm_mday)

        time_stamp = mod_time[8:10]+"."+mod_time[5:7]+"."+mod_time[:4]

        file_name = file_arc["Name"]
        file_name = file_name.replace(time_stamp, "").strip()
        file_name = os.path.splitext(file_name)[0].strip()

        file_name_dict = {"form":file_name, "date":time_stamp, "datetime":file_date, "in_period":(file_date >= old_date), "check":False}
        file_arc.update(file_name_dict)

        if file_date >= old_date:
            if len(file_new) < 3:
                file_new.append(file_arc["Name"])

    if review_period==1:
        if len(file_new)==0:
            print_error("В облаке за вчерашний день нет новых файлов")
    elif len(file_new) > 0:
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

    remove_ext = False # есть архивы без расширения (яндекс)

    for file_arc_remote in remote_file_list:
        mod_time = file_arc_remote["ModTime"]
        if mod_time.find(".") >= 0:
            mod_time = file_arc_remote["ModTime"].partition('.')[0]
        elif mod_time.find("+") >= 0:
            mod_time = file_arc_remote["ModTime"].partition('+')[0]
        file_date = time.strptime(mod_time, "%Y-%m-%dT%H:%M:%S")
        file_date = datetime.datetime(file_date.tm_year, file_date.tm_mon, file_date.tm_mday)
        if file_date < old_date: continue

        file_name_remote = file_arc_remote["Name"]
        for nn, file_arc in enumerate(file_list):
            if file_arc["date_time"] < old_date: continue

            file_name = file_arc["file_name"]
            file_name_remote_name, file_name_remote_ext = os.path.splitext(file_name_remote)
            file_name_name, file_name_ext = os.path.splitext(file_name)
            if file_name_remote == file_name or file_name_remote_name == file_name_name or file_name_remote == file_name_name:
                if file_name_remote != file_name: remove_ext = True
                file_arc["check"] = file_arc_remote["check"] = True
                break

    for nn, file_arc in enumerate(file_list):
        if file_arc["date_time"] < old_date: continue
        if file_arc["check"]: continue

        for file_arc_remote in remote_file_list:
            if file_arc["name"] == file_arc_remote["form"] and file_arc["date_time"] < file_arc_remote["datetime"]:
                file_arc["check"] = file_arc_remote["check"] = True # в облаке есть более свежий файл
                break

    skipped_file_list = []
    if len(file_list) > 0:
        file_str, count = "", 0
        for nn, file_arc in enumerate(file_list):
            if file_arc["date_time"] < old_date: continue
            if file_arc["check"]: continue

            file_str += file_arc["file_name"]
            count += 1
            if nn + 1 < len(file_list): file_str += ", "
            skipped_file_list.append(file_arc)

        if file_str != "":
            print_error("В облаке за " + str(review_period) + " дней не загруженно " + str(
                count) + " архивов. Список пропущенных архивов: " + file_str)
        else:
            print_info(" + В облаке за " + str(review_period) + " дней загружены все архивы")
    else:
        pass
        # print_info(" + В облаке за " + str(review_period) + " нет загруженых архивов")

    # remove_ext - есть архивы без расширения (яндекс)
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
        firma_msg = "Отчет о резеревном копировании в: <b>" + firma_name + "</b>\n"
    else:
        firma_msg = "Отчет о резеревном копировании\n"
    if message.find("ОШИБКА") >= 0:
        firma_msg = "<b>ОШИБКИ!</b> " + firma_msg
    firma_msg += " <i>(версия сервиса уведомлений:"+VERSION+")</i>\n\n"
    message = firma_msg + message

    print("")
    # отправить сообщение в чат
    print("Отправляем сообщения в Телеграм")
    for chat_user, chat_id in telegram_bot_users:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=HTML"
        data = requests.get(url).json()
        print(" + сообщение - " + chat_user + ": " + str(data['ok']))
    return

def user_list(telegram_bot, telegram_bot_token):
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
    param_str = "userlist,systray"
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

def type_remote(remote_name):
    command = "config show " + remote_name
    stdout, _ = utils.run_rclone_cmd(command)

    process_out = stdout.split('\n')
    for str_out in process_out:
        str_out = str_out.lower()
        if str_out.find("type = ")==0:
            str_out = str_out.replace("type = ","")
            return str_out
    return ""

def test_rclone(remote_folder, min_empty_space):
    gb = 10 ** 9

    if not rclone.is_installed():
        print_error("Не установлен RClone.\n  Добавьте путь к программе в переменную окружения PATH")
        return False
    ver = rclone.version()
    print_info("\n<b>Найден установленный RClone</b> (" + ver + ")")

    remote_path = remote_folder.split(":")
    if len(remote_path) <= 1:
        print_error("Не корректный формат записи подключения к облаку для RClone")
        return False

    remote_connection = remote_path[0]
    if not remote_connection.endswith(":"): remote_connection = f"{remote_connection}:"

    remote_list = rclone.get_remotes()
    if len(remote_list)==0:
        print_error("Список конфигураций RClone пуст...")
        return False
    remote_list = ', '.join(str(x).replace(':','') for x in remote_list)
    print_info(" + Загружен список всех конфигураций RClone: (<i>" + remote_list + "</i>)")

    if not rclone.check_remote_existing(remote_connection):
        print_error("Не настроена в конфигурации RClone подключение к облаку: " + remote_connection)
        return False
    typ = type_remote(remote_connection)
    print_info(" + успешное подключение к облаку: " + remote_connection + " (тип - "+typ+")")

    try:
        space_list = rclone.about(remote_connection)
        empty_space = space_list.get("free")
        total_space = space_list.get("total")
        if empty_space == None or total_space == None:
            print_error("Не могу проверить размер свободного места в облаке: " + remote_connection)
            return False
    except:
        print_error("Ошибка получения информации об облаке (возможно блокировка пользователя или окончание подписки): " + remote_connection)
        return False

    free_gb, total_gb = int(round(empty_space / gb, 0)),int(round(total_space / gb, 0))
    percent = int(round(100*(total_gb-free_gb)/total_gb,0))
    if free_gb < min_empty_space:
        print_error("На диске в облаке мало свободного места: " + str(free_gb) + " гб (занято "+str(percent)+"%), всего места: " + str(total_gb) + " гб")
    print_info(" + в облаке свободного места: " + str(free_gb) + " гб (занято "+str(percent)+"%), всего места: " + str(total_gb) + " гб")

    return True

def send_skipped_files(skipped_file_list, backup_folder, remote_folder, review_period, remove_ext):
    if len(skipped_file_list)==0: return

    from rich.progress import (Progress, TextColumn, BarColumn, TaskProgressColumn, TransferSpeedColumn, TimeRemainingColumn,TimeElapsedColumn,SpinnerColumn)
    pbar = Progress(TextColumn("[progress.description]{task.description}"),BarColumn(),TaskProgressColumn(), TimeElapsedColumn(),TimeRemainingColumn(), TransferSpeedColumn(), SpinnerColumn() )
    # https://rich.readthedocs.io/en/stable/progress.html#columns

    # maxage = "max-age "+str(review_period)+"d"

    print("")
    print("отправим в облако пропущенные файлы")

    if remote_folder.lower().find("yandex")>=0:
        print("  работаем с облаком Yandex: скопируем файлы во временную папку и удалим расширения")

    backup_folder = backup_folder[:-1] if backup_folder[-1] == "\\" else backup_folder  # уберем слэш в конце
    tmp_folder = tempfile.mkdtemp()

    for file_path in skipped_file_list:
        src_file = file_path["path"]
        dst_file = src_file.replace(backup_folder, tmp_folder)
        if remove_ext:
            dst_file = os.path.splitext(dst_file)[0]

        src_file0 = src_file.replace(backup_folder, "")[1:]
        if src_file0.rfind("\\") >= 0:
            src_file0 = src_file0.replace(file_path[0], "")
            tmp_folder0 = tmp_folder + "\\" + src_file0
            if not os.path.exists(tmp_folder0):
                os.makedirs(tmp_folder0)

        try:
            shutil.copyfile(src_file, dst_file)
            file_path["path"] = dst_file
        except:
            print(" ... не получается скопировать файл. ошибка диска: "+dst_file)
            file_path["path"] = ""

    for file_path in skipped_file_list:
        src_file = file_path["path"]
        if src_file:
            rclone.copy(src_file, remote_folder, ignore_existing=False, show_progress=True, pbar=pbar) # , args=['--' + maxage]
    # rclone.copy(tmp_folder, remote_folder, ignore_existing=False, args=['--' + maxage], show_progress=True, pbar=pbar) # , args=['--' + maxage], show_progress=True

    shutil.rmtree(tmp_folder)

def test_net_server(net_server, net_folder, net_folder_user,net_folder_pass, min_empty_space, review_period):
    if net_server=="" or net_folder=="": return False

    # пропингуем сервер
    # response = os.system(f"ping -n 1 {net_server}")
    ping_res = ping(net_server, timeout=15)
    if typeof(ping_res)=="bool":
        if ping_res == False:
            print_error("Сетевое хранилище недоступно: "+net_server+"\n  Проверьте подключение к сети ("+str(ping_res)+")")
            return False
    elif not is_number(ping_res):
        if ping_res == False or ping_res == None:
            print_error("Сетевое хранилище недоступно: "+net_server+"\n  Проверьте подключение к сети ("+str(ping_res)+")")
            return False
    print_info("\n<b>Найдено сетевое хранилище: </b>"+net_server)

    # Подключимся к сетевому рессурсу
    mount_command = "net use "+net_folder+" /user:"+net_folder_user+" "+net_folder_pass+">nul"
    os.system(mount_command)

    # проверим существует ли папка с архивами, есть ли доступ по чтению и записи
    test_read_write(net_folder)

    # проверим свободное место на диске
    check_disk_space(net_folder, min_empty_space)

    # проверим список архивов, создаются ли новые архивы за указанный контрольный период
    file_list = read_dir(net_folder)
    check_new_archives(file_list, review_period)

    # Отключимся от сетевого рессурса
    unmount_command = "net use * /del /y"+">nul"
    os.system(unmount_command)

    return True

def show_about(icon_item, item):
    """Показывает информацию о программе"""
    import tkinter as tk
    from tkinter import messagebox

    def show_and_destroy():
        # Создаем временное окно
        temp_root = tk.Tk()
        temp_root.withdraw()

        # Показываем сообщение
        messagebox.showinfo("О программе",f"Монитор архивов 1С\n\nОтслеживает команды в Телеграм боте" )

        # Закрываем временное окно
        temp_root.destroy()

    # Запускаем в отдельном потоке, чтобы не блокировать иконку в трее
    about_thread = threading.Thread(target=show_and_destroy)
    about_thread.start()

def exit_application(icon_item, item):
    """Завершает работу программы"""
    global app_running, tray_icon
    app_running = False
    tray_icon.stop()

def send_report(icon_item, item):
    """Отправляем отчет"""
    global telegram_bot_users_work
    send_to_telegram(telegram_bot_users_work)

def setup_tray_icon():
    """Настраивает иконку в трее"""
    global tray_icon

    # Создаем меню
    menu = (
        pystray.MenuItem("О программе", show_about),
        pystray.MenuItem("Послать отчет", send_report),
        pystray.MenuItem("Выход", exit_application)
    )

    if pict_icon != None:
        # Создаем иконку в трее
        tray_icon = pystray.Icon(
            "file_monitor",
            icon=pict_icon,
            title="Монитор архивов 1С",
            menu=menu)
    else:
        tray_icon = pystray.Icon(
            "file_monitor",
            title="Монитор архивов 1С",
            menu=menu)

    # Запускаем мониторинг в отдельном потоке
    monitor_thread = threading.Thread(target=bot_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Запускаем иконку
    tray_icon.run()

def check_time(time_start):
    global new_day
    """
    Проверяет текущее время и сравнивает его с заданным временем time_start "18:30".
    """
    current_time = datetime.datetime.now().strftime("%H:%M") # Получаем текущее время в формате "ЧЧ:ММ"
    if current_time == "00:00" : new_day = True

    return current_time == time_start

def bot_monitor():
    """Функция мониторинга сообщений в Боте"""
    global app_running, message_info, new_day
    global firma_name, backup_folder, remote_folder, net_server, net_folder, net_folder_user, net_folder_pass, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, telegram_bot_users, telegram_bot_users_work, time_start

    telegram_bot_users_work = telegram_bot_users.copy()
    while app_running:
        message_info = ""

        # show_user_info(telegram_bot, telegram_bot_token, telegram_bot_users)  # пасхалка
        telegram_bot_users = check_menu_command("/status", telegram_bot, telegram_bot_token, telegram_bot_users_work)
        if len(telegram_bot_users) != 0:
            send_to_telegram(telegram_bot_users)
        if check_time(time_start):
            if new_day:
                send_to_telegram(telegram_bot_users_work)
                new_day = False

        # Ждем перед следующей проверкой
        time.sleep(CHECK_INTERVAL)


def send_to_telegram(telegram_bot_users_work = [], copy_file = False):
    global firma_name, backup_folder, remote_folder, net_server, net_folder, net_folder_user, net_folder_pass, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, time_start

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
    # работаем с Synology

    # проверим доступен ли сервер по сети, есть ли доступ по записи и есть ли свободное место в папке
    # проверим список архивов, создаются ли новые архивы за указанный контрольный период
    test_net_server(net_server, net_folder, net_folder_user,net_folder_pass, min_empty_space, review_period)

    #########################################################################################
    # работаем с RClone
    skipped_file_list, remove_ext = [], False

    # проверим установлен ли rclone, настроено ли подключение и есть ли свободное место в облаке
    if test_rclone(remote_folder, min_empty_space):
        # проверим есть ли в облаке архивы за вчерашний день
        check_new_archives_rclone(remote_folder, 1, depth_folder)

        # проверим копируются ли в облако новые архивы за указанный контрольный период
        remote_list = check_new_archives_rclone(remote_folder, review_period, depth_folder)

        # сопоставим последние архивы на диске с теми что загружены в облако - есть ли пропущенные
        skipped_file_list, remove_ext = check_skipped_archives_rclone(file_list, remote_list, review_period)

    #########################################################################################
    # работаем с Telegram

    # отправим сообщение боту в Телеграм
    send_message_to_telegram_bot(firma_name, telegram_bot, telegram_bot_token, telegram_bot_users_work, message_info)

    if copy_file:
        # сначала надо проверить среду исполнения: если отладка (python.exe), то пропускаем, если автономное приложение, то старт
        if run_as_exe_app(APP_FILENAME):
            # отправим в облако пропущенные файлы
            send_skipped_files(skipped_file_list, backup_folder, remote_folder, review_period, remove_ext)

    return

def main():
    global message_info
    global firma_name, backup_folder, remote_folder, net_server, net_folder, net_folder_user, net_folder_pass, min_empty_space, review_period, depth_folder, telegram_bot, telegram_bot_token, telegram_bot_users, time_start
    close_spalsh_screen()

    read_config()
    check_update()

    param = check_cmd_param()
    if param == "userlist":
        user_list(telegram_bot, telegram_bot_token)
        return
    elif param == "systray":
        make_icon()
        setup_tray_icon()
    else:
        send_to_telegram(telegram_bot_users, True)

main()
