import datetime
import json
import logging
import os
import random
import sys
import threading
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from maxgram import Bot

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from maxgram.keyboards import InlineKeyboard
except ImportError:
    InlineKeyboard = None

try:
    from fipi_parser import update_tasks_database
except ImportError:
    update_tasks_database = None

BASE_DIR = Path(__file__).parent
TASKS_FILE = BASE_DIR / "tasks.json"
USERS_FILE = BASE_DIR / "users.json"
LOG_FILE = BASE_DIR / "maxingo.log"

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "Токен бота не найден! Укажите BOT_TOKEN в файле .env (см. образец в .env.example) "
        "или в переменных окружения."
    )

TASKS_PER_DAY = 5
SEND_HOUR = 9
SEND_MINUTE = 0
NIGHT_CHECK_HOUR = 23
NIGHT_CHECK_MINUTE = 55

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    force=True,
)
logger = logging.getLogger("MaxingoBot")

bot = Bot(BOT_TOKEN)
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
data_lock = threading.RLock()


def make_keyboard(rows):
    """Преобразует список кнопок в объект клавиатуры или структуру вложения"""
    if not rows:
        return None
    if InlineKeyboard is not None:
        try:
            return InlineKeyboard(*rows)
        except Exception as e:
            logger.error(f"Ошибка создания клавиатуры InlineKeyboard: {e}")
    buttons = []
    for row in rows:
        b_row = []
        for btn in row:
            b_dict = {"text": str(btn.get("text", ""))}
            cb = btn.get("callback") or btn.get("callback_data") or btn.get("payload")
            if cb is not None:
                b_dict["type"] = "callback"
                b_dict["payload"] = str(cb)
            elif "url" in btn:
                b_dict["type"] = "link"
                b_dict["url"] = str(btn["url"])
            b_row.append(b_dict)
        if b_row:
            buttons.append(b_row)
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}


def safe_reply(context, text: str, keyboard=None):
    """Безопасный ответ: отправляет сообщение с клавиатурой, логируя ошибки"""
    try:
        kb = make_keyboard(keyboard) if keyboard is not None else None
        return context.reply(text, keyboard=kb)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}", exc_info=True)


def safe_reply_callback(context, text: str, keyboard=None, is_current: bool = False):
    """Безопасный ответ на callback-запрос с возможностью редактирования или отправки нового сообщения"""
    kb = make_keyboard(keyboard) if keyboard is not None else None
    try:
        if hasattr(context, "reply_callback"):
            return context.reply_callback(text, keyboard=kb, is_current=is_current)
    except Exception as e:
        logger.warning(f"Ошибка reply_callback, используем safe_reply: {e}")
    return safe_reply(context, text, keyboard=kb)


def load_json(filepath: Path, default=None):
    """Чтение данных из JSON файла с блокировкой потока"""
    if default is None:
        default = {}
    with data_lock:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default


def save_json(filepath: Path, data) -> bool:
    """Атомарная запись данных в JSON файл"""
    with data_lock:
        try:
            tmp = filepath.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(filepath)
            return True
        except Exception as e:
            logger.error(f"Ошибка записи в {filepath}: {e}")
            return False


def get_topics_map() -> dict:
    """Получение структуры тем и заданий"""
    data = load_json(TASKS_FILE, {"topics": {}})
    return data.get("topics", {})


def get_tasks_by_topic(topic_name: str = None) -> list:
    """Получение списка заданий по теме (или всех)"""
    topics = get_topics_map()
    if topic_name and topic_name in topics:
        return topics[topic_name]
    all_tasks = []
    for task_list in topics.values():
        all_tasks.extend(task_list)
    return all_tasks


def get_task_by_id(task_id: str) -> dict:
    """Поиск задачи по ID"""
    for t in get_tasks_by_topic():
        if str(t.get("id")) == str(task_id):
            return t
    return None


def ensure_user(user_id, chat_id=None, username=None) -> dict:
    """Авторизация и создание профиля пользователя"""
    with data_lock:
        users = load_json(USERS_FILE, {})
        uid = str(user_id)
        today = datetime.date.today().isoformat()
        changed = False

        if uid not in users:
            users[uid] = {
                "username": username or "Ученик",
                "chat_id": chat_id,
                "streak": 0,
                "max_streak": 0,
                "last_date": None,
                "today_solved": 0,
                "solved_tasks": [],
                "mistakes": [],
                "selected_topic": None,
                "active_task_id": None,
                "daily_date": today,
            }
            changed = True
        else:
            u = users[uid]
            if username and u.get("username") in ("Ученик", None) and username != "Ученик":
                u["username"] = username
                changed = True
            if u.get("daily_date") != today:
                yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                if u.get("last_date") not in (today, yesterday):
                    u["streak"] = 0
                u["today_solved"] = 0
                u["active_task_id"] = None
                u["daily_date"] = today
                changed = True
            if chat_id and u.get("chat_id") != chat_id:
                u["chat_id"] = chat_id
                changed = True

        if changed:
            save_json(USERS_FILE, users)
        return users[uid]


def update_user(user_id, updates: dict) -> dict:
    """Обновление данных профиля пользователя"""
    with data_lock:
        users = load_json(USERS_FILE, {})
        uid = str(user_id)
        if uid not in users:
            ensure_user(user_id)
            users = load_json(USERS_FILE, {})
        users[uid].update(updates)
        save_json(USERS_FILE, users)
        return users[uid]


def get_val(obj, *paths, default=None):
    """Безопасное извлечение значения из объекта по списку возможных путей"""
    for path in paths:
        curr = obj
        found = True
        for key in path:
            if isinstance(curr, dict) and key in curr:
                curr = curr[key]
            elif hasattr(curr, key):
                curr = getattr(curr, key)
            else:
                found = False
                break
        if found and curr is not None:
            return curr
    return default


def extract_user(context):
    """Извлечение user_id, chat_id и username из любого контекста (сообщение, callback, bot_started)"""
    user_id = get_val(
        context,
        ("user", "user_id"),
        ("message", "sender", "user_id"),
        ("sender", "user_id"),
        ("callback", "user", "user_id"),
        ("update", "user", "user_id"),
        ("update", "callback", "user", "user_id"),
        ("update", "message", "sender", "user_id"),
        ("message", "from", "id"),
    )
    chat_id = get_val(
        context,
        ("chat_id",),
        ("update", "chat_id"),
        ("message", "recipient", "chat_id"),
        ("recipient", "chat_id"),
        ("message", "chat_id"),
        ("update", "message", "recipient", "chat_id"),
        ("update", "message", "chat_id"),
        default=user_id,
    )
    username = get_val(
        context,
        ("user", "name"),
        ("user", "username"),
        ("message", "sender", "name"),
        ("sender", "name"),
        ("callback", "user", "name"),
        ("update", "user", "name"),
        ("update", "callback", "user", "name"),
        ("message", "from", "first_name"),
        default="Ученик",
    )
    return user_id, chat_id, username


def normalize_answer(text: str) -> str:
    """Нормализация ответа для проверки"""
    return str(text).strip().lower().replace("ё", "е").replace(",", ".").rstrip(".")


def is_correct(user_ans: str, right_ans: str) -> bool:
    """Сверка ответа пользователя с правильным ответом"""
    norm_u = normalize_answer(user_ans)
    return any(norm_u == normalize_answer(v) for v in str(right_ans).split("|") if v)


def main_menu_kb(user_id):
    """Генерация кнопок главного меню"""
    u = ensure_user(user_id)
    topic = u.get("selected_topic") or "Все темы"
    mistakes_cnt = len(u.get("mistakes", []))

    kb = [
        [{"text": "📚 Получить задачу ФИПИ", "callback": "menu:next_task", "callback_data": "menu:next_task"}],
        [{"text": f"📂 Тема: {topic}", "callback": "menu:topics", "callback_data": "menu:topics"}],
    ]
    if mistakes_cnt > 0:
        kb.append([{"text": f"🛠 Работа над ошибками ({mistakes_cnt})", "callback": "menu:mistakes", "callback_data": "menu:mistakes"}])
    kb.append([{"text": "🔥 Мой огонёк и прогресс", "callback": "menu:stats", "callback_data": "menu:stats"}])
    return kb


def task_kb(task: dict):
    """Генерация клавиатуры для задачи"""
    kb = []
    row = []
    for opt in task.get("options", []):
        opt_s = str(opt)
        payload = f"ans:{task['id']}:{opt_s[:30]}"
        row.append({"text": opt_s, "callback": payload, "callback_data": payload})
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([{"text": "⏭ Пропустить", "callback": "menu:next_task", "callback_data": "menu:next_task"}])
    kb.append([{"text": "🏠 В меню", "callback": "menu:main", "callback_data": "menu:main"}])
    return kb


def send_task_to_user(user_id, context, mistake_mode: bool = False):
    """Отправка задачи пользователю"""
    u = ensure_user(user_id)
    if mistake_mode:
        mistakes = u.get("mistakes", [])
        if not mistakes:
            safe_reply(context, "✅ Ошибок нет!", keyboard=main_menu_kb(user_id))
            return
        task = get_task_by_id(mistakes[0])
    else:
        pool = get_tasks_by_topic(u.get("selected_topic"))
        if not pool:
            safe_reply(context, "⚠️ База пуста. Запустите fipi_parser.py!")
            return
        solved = set(u.get("solved_tasks", []))
        unsolved = [t for t in pool if t.get("id") not in solved]
        task = random.choice(unsolved if unsolved else pool)

    if not task:
        safe_reply(context, "⚠️ Ошибка загрузки задачи.", keyboard=main_menu_kb(user_id))
        return

    update_user(user_id, {"active_task_id": task["id"]})
    mode = "🛠 РАБОТА НАД ОШИБКАМИ" if mistake_mode else f"📝 ЗАДАНИЕ ФИПИ #{task.get('fipi_id', '')}"
    img_links = "\n".join(task.get("images", []))
    img_block = f"\n🖼 Иллюстрация: {img_links}\n" if img_links else ""

    text = f"{mode}\n📂 Тема: {task.get('topic', 'Общая')}\n\n{task.get('question', '')}\n{img_block}\n✍️ Напиши ответ в чат или выбери кнопку:"
    safe_reply(context, text, keyboard=task_kb(task))


def check_user_answer(user_id, context, answer_text: str, task_id: str):
    """Проверка ответа пользователя"""
    task = get_task_by_id(task_id)
    if not task:
        update_user(user_id, {"active_task_id": None})
        safe_reply(context, "Задача не найдена.", keyboard=main_menu_kb(user_id))
        return

    u = ensure_user(user_id)
    solved_tasks = list(u.get("solved_tasks", []))
    mistakes = list(u.get("mistakes", []))
    right_answer = task.get("answer", "")

    is_right = is_correct(answer_text, right_answer) if right_answer else len(answer_text.strip()) > 0

    if is_right:
        if task_id not in solved_tasks:
            solved_tasks.append(task_id)
        if task_id in mistakes:
            mistakes.remove(task_id)

        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        last_date = u.get("last_date")
        streak = u.get("streak", 0)

        if last_date != today:
            streak = (streak + 1) if last_date == yesterday else 1
            last_date = today

        today_solved = u.get("today_solved", 0) + 1
        update_user(user_id, {
            "streak": streak,
            "last_date": last_date,
            "today_solved": today_solved,
            "solved_tasks": solved_tasks,
            "mistakes": mistakes,
            "active_task_id": None,
        })
        safe_reply(context, f"✅ Верно!\n🔥 Огонёк: {streak} дн.\n📊 Решено сегодня: {today_solved}", keyboard=main_menu_kb(user_id))
    else:
        if task_id not in mistakes:
            mistakes.append(task_id)
            update_user(user_id, {"mistakes": mistakes})
        safe_reply(context, f"❌ Неверно.\nЗадание в списке ошибок ({len(mistakes)}).", keyboard=task_kb(task))


@bot.command("start")
@bot.on("bot_started")
def handle_start(context):
    user_id, chat_id, username = extract_user(context)
    logger.info(f"handle_start вызван: user_id={user_id}, chat_id={chat_id}, username={username}")
    if user_id is None:
        logger.warning(f"Не удалось определить user_id в handle_start: {context.update}")
        return
    ensure_user(user_id, chat_id, username)
    safe_reply(context, f"Привет, {username}! Выбери действие:", keyboard=main_menu_kb(user_id))


@bot.command("menu")
def handle_menu(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    safe_reply(context, "🏠 Главное меню:", keyboard=main_menu_kb(user_id))


@bot.command("task", "tasks", "next")
def handle_task(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    send_task_to_user(user_id, context, mistake_mode=False)


@bot.command("topics", "topic")
def handle_topics(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    topics_list = list(get_topics_map().keys())
    kb = [[{"text": "🌐 Все темы", "callback": "set_topic:ALL", "callback_data": "set_topic:ALL"}]]
    for idx, t_name in enumerate(topics_list):
        kb.append([{"text": f"📂 {t_name}", "callback": f"set_topic:{idx}", "callback_data": f"set_topic:{idx}"}])
    safe_reply(context, "Выбери тему:", keyboard=kb)


@bot.command("stats", "streak")
def handle_stats(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    u = ensure_user(user_id, chat_id, username)
    text = f"🔥 Огонёк: {u.get('streak', 0)} дн.\n✅ Решено задач: {len(u.get('solved_tasks', []))}\n⚠️ Ошибок: {len(u.get('mistakes', []))}"
    safe_reply(context, text, keyboard=main_menu_kb(user_id))


@bot.command("mistakes")
def handle_mistakes(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    send_task_to_user(user_id, context, mistake_mode=True)


@bot.command("help", "info")
def handle_help(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    help_text = (
        "🤖 Бот подготовки к ОГЭ по материалам ФИПИ\n\n"
        "Доступные команды:\n"
        "/start — Запустить бота и открыть главное меню\n"
        "/menu — Главное меню\n"
        "/task — Получить задачу\n"
        "/topics — Выбрать тему\n"
        "/mistakes — Работа над ошибками\n"
        "/stats — Прогресс и серия дней (огонёк)\n"
        "/help — Эта справка\n\n"
        "Решай хотя бы 1 задачу каждый день, чтобы поддерживать огонёк! 🔥"
    )
    safe_reply(context, help_text, keyboard=main_menu_kb(user_id))


@bot.command("__fallback__")
def handle_unknown_command(context):
    user_id, chat_id, username = extract_user(context)
    if user_id is None:
        return
    ensure_user(user_id, chat_id, username)
    safe_reply(context, "Команда не распознана. Используй кнопки меню или /help:", keyboard=main_menu_kb(user_id))


@bot.on("message_created")
def on_message(context):
    user_id, chat_id, username = extract_user(context)
    text = get_val(context, ("message", "body", "text"), ("message", "text"))
    if not text or user_id is None or str(text).strip().startswith("/"):
        return

    clean_text = str(text).strip().lower()
    if clean_text in ("старт", "start", "начать", "меню", "menu"):
        handle_start(context)
        return

    u = ensure_user(user_id, chat_id, username)
    if u.get("active_task_id"):
        check_user_answer(user_id, context, str(text).strip(), u["active_task_id"])
    else:
        safe_reply(context, "Выбери действие в меню:", keyboard=main_menu_kb(user_id))


@bot.on("message_callback")
def on_callback(context):
    cb = get_val(context, ("payload",), ("callback", "payload"), ("callback_query", "data"))
    user_id, chat_id, username = extract_user(context)
    if not cb or user_id is None:
        return
    ensure_user(user_id, chat_id, username)

    cb_str = str(cb)
    if cb_str.startswith("ans:"):
        _, t_id, ans = cb_str.split(":", 2)
        check_user_answer(user_id, context, ans, t_id)
    elif cb_str == "menu:next_task":
        send_task_to_user(user_id, context, mistake_mode=False)
    elif cb_str == "menu:mistakes":
        send_task_to_user(user_id, context, mistake_mode=True)
    elif cb_str == "menu:topics":
        topics_list = list(get_topics_map().keys())
        kb = [[{"text": "🌐 Все темы", "callback": "set_topic:ALL", "callback_data": "set_topic:ALL"}]]
        for idx, t_name in enumerate(topics_list):
            kb.append([{"text": f"📂 {t_name}", "callback": f"set_topic:{idx}", "callback_data": f"set_topic:{idx}"}])
        safe_reply(context, "Выбери тему:", keyboard=kb)
    elif cb_str.startswith("set_topic:"):
        arg = cb_str.split(":", 1)[1]
        topics_list = list(get_topics_map().keys())
        chosen = None if arg == "ALL" else (topics_list[int(arg)] if int(arg) < len(topics_list) else None)
        update_user(user_id, {"selected_topic": chosen, "active_task_id": None})
        safe_reply_callback(context, f"✅ Выбрана тема: {chosen or 'Все темы'}", keyboard=main_menu_kb(user_id))
    elif cb_str == "menu:stats":
        u = ensure_user(user_id)
        text = f"🔥 Огонёк: {u.get('streak', 0)} дн.\n✅ Решено задач: {len(u.get('solved_tasks', []))}\n⚠️ Ошибок: {len(u.get('mistakes', []))}"
        safe_reply_callback(context, text, keyboard=main_menu_kb(user_id))
    elif cb_str == "menu:main":
        safe_reply_callback(context, "🏠 Главное меню:", keyboard=main_menu_kb(user_id))


def nightly_streak_check():
    """Ежедневная ночная проверка активности пользователей"""
    with data_lock:
        users = load_json(USERS_FILE, {})
        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        for uid, u in users.items():
            if u.get("today_solved", 0) >= 1:
                if u.get("last_date") == yesterday:
                    u["streak"] = u.get("streak", 0) + 1
                elif u.get("last_date") != today:
                    u["streak"] = 1
                u["last_date"] = today
            else:
                u["streak"] = 0
            u["today_solved"] = 0
            u["active_task_id"] = None
        save_json(USERS_FILE, users)


if __name__ == "__main__":
    if not USERS_FILE.exists():
        save_json(USERS_FILE, {})

    scheduler.add_job(nightly_streak_check, "cron", hour=NIGHT_CHECK_HOUR, minute=NIGHT_CHECK_MINUTE)
    scheduler.start()
    try:
        bot.run()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
