import csv
import os
import re
import traceback
import asyncio
from PIL import Image, ImageGrab
from rapidfuzz import fuzz, process
from nick_matcher import find_matches
from chrome_lens_py import LensAPI

# Импорт из наших модулей
from output import print_found_players_table, print_manual_players_table
from utils import safe_float, safe_int, safe_elo, get_color_icon
from analyzer import analyze_team
from compare import compare_two_teams, collect_team_players

import sys

def get_app_dir():
    """
    Возвращает папку, где лежит .exe (в EXE-режиме)
    или где лежит .py (в режиме разработки).
    """
    if getattr(sys, 'frozen', False):
        # Запущено как EXE — папка с .exe
        return os.path.dirname(sys.executable)
    else:
        # Запущено как .py — папка со скриптом
        return os.path.dirname(os.path.abspath(__file__))
def get_resource_path(filename):
    """Путь к встроенному ресурсу (.csv, .wav, .png) — read-only."""
    if getattr(sys, 'frozen', False):
        candidates = [
            os.path.join(sys._MEIPASS, filename),
            os.path.join(os.path.dirname(sys.executable), filename),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)        




# ---------- ГЛОБАЛЬНЫЙ БУФЕР КОМАНД ----------
team_buffer = []   # хранит последние две группы игроков (списки словарей)

# ---------- СТОП-СЛОВА ----------
STOP_WORDS = {
    'after', 'before', 'the', 'and', 'for', 'with', 'without', 'from', 'into',
    'новь', 'и', 'в', 'на', 'с', 'по', 'к', 'у', 'за', 'из', 'от', 'до',
    'live', 'psn', 'xbox', 'pc', 'ru', 'en', 'de', 'fr', 'vs', 'team', 'game',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
    'я', 'ты', 'он', 'она', 'мы', 'вы', 'они', 'командир',
    'вопбопбопка', 'вопбопропка', 'опбопропка', 'вопбоп', 'бопбоп',
    'eta', 'аеа', 'ae', 'командир',
    'oy', 'fey', 'ie', '63', 'гз', 'вн'
}

# ---------- ФИКСИРОВАННЫЕ ПОРОГИ (по умолчанию) ----------
DEFAULT_LIMITS = {
    'kd':     {'yellow': 1.21, 'orange': 1.64, 'red': 2.0, 'purple': 2.948},
    'wr':     {'yellow': 51,   'orange': 58,   'red': 65,   'purple': 76},

    # --- ОБЩИЕ ЗНАЧЕНИЯ (пересчитанные) ---
    'hs':     {'yellow': 600,  'orange': 1000,  'red': 2000, 'purple': 6000},
    'cap':    {'yellow': 100,  'orange': 300,   'red': 500,  'purple': 700},
    'veh':    {'yellow': 200,  'orange': 600,   'red': 1500, 'purple': 2500},
    'built':  {'yellow': 300,  'orange': 600,   'red': 1000, 'purple': 2000},
    'apc':    {'yellow': 40,   'orange': 200,   'red': 600,  'purple': 1000},

    # --- ELO: индивидуальный (для ячеек таблицы) и суммарный по команде (для радара) ---
    'elo':      {'yellow': 713,  'orange': 944,  'red': 1316, 'purple': 1672},
    'elo_team': {'yellow': 4000, 'orange': 6000, 'red': 9000, 'purple': 14000},
}

# Папка, где лежит main.py — чтобы пути работали у любого пользователя
BASE_DIR = get_app_dir()

CSV_FILE = get_resource_path("enlisted_players_full.csv")
LIMITS_FILE = get_resource_path("limits.csv")
CRASH_LOG = os.path.join(BASE_DIR, "crash_log.txt")

MAX_PLAYERS = 10

# Поля, которые реально читаются из CSV в коде.
# Всё остальное выкидывается при загрузке для экономии памяти (~40%).
KEEP_FIELDS = {
    # основные
    'name', 'rank', 'elo', 'matches', 'win_percent',
    # метрики
    'kd', 'headshots', 'vehicles', 'captures', 'built', 'apc_spawns',
    # читаются в analyzer.dedupe_players
    'kills', 'score',
}


# ---------- КОМПАКТНОЕ ХРАНЕНИЕ ИГРОКА ----------
class Player:
    """
    Лёгкая замена dict на 687k записей.
    __slots__ экономит ~70-100 МБ (нет внутреннего хэш-словаря на каждый объект).
    Полностью совместим с p.get(), p['field'], p['field'] = v, 'field' in p,
    p.items(), p.keys(), p.values(), dict(p), len(p), for k in p.
    """
    __slots__ = (
        # --- поля из CSV ---
        'name', 'rank', 'elo', 'matches', 'win_percent',
        'kd', 'headshots', 'vehicles', 'captures', 'built', 'apc_spawns',
        'kills', 'score',
        # --- служебные, добавляются в analyzer.py / compare.py ---
        '_weight', '_conf', '_bot',
    )

    # дефолты для служебных полей (если не переданы при создании)
    _DEFAULTS = {
        '_weight': 1.0,
        '_conf': 'low',
        '_bot': False,
    }

    def __init__(self, **kw):
        for k in self.__slots__:
            if k in kw:
                setattr(self, k, kw[k])
            else:
                setattr(self, k, self._DEFAULTS.get(k, None))

    # --- чтение как у dict ---
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __contains__(self, key):
        return key in self.__slots__

    def keys(self):
        return self.__slots__

    def values(self):
        return tuple(getattr(self, k) for k in self.__slots__)

    def items(self):
        return tuple((k, getattr(self, k)) for k in self.__slots__)

    def __iter__(self):
        return iter(self.__slots__)

    def __len__(self):
        return len(self.__slots__)

    def __repr__(self):
        head = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__slots__[:3])
        return f"Player({head}, ...)"


# ---------- КОНВЕРТЕРЫ ТИПОВ ----------
# Какие поля CSV конвертим в int / float при загрузке.
# Это экономит ~100-150 МБ, потому что числа в Python занимают
# 28 байт (int) или 24 байта (float), а строки-цифры — ~55 байт.
_INT_FIELDS   = {'rank', 'elo', 'matches', 'win_percent',
                 'headshots', 'vehicles', 'captures', 'built', 'apc_spawns',
                 'kills', 'score'}
_FLOAT_FIELDS = {'kd'}


def _to_int(v):
    if v is None:
        return None
    v = str(v).strip()
    if v in ('', '—', '-', '---'):
        return None
    try:
        return int(float(v))   # на случай "1758.0"
    except (ValueError, TypeError):
        return None


def _to_float(v):
    if v is None:
        return None
    v = str(v).strip()
    if v in ('', '—', '-', '---'):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------- НОРМАЛИЗАЦИЯ ----------
from nick_matcher import normalize_ocr_word


# ---------- ЗАГРУЗКА БАЗЫ ----------
def load_players_dict(csv_path):
    players = {}
    nicknames = []
    if not os.path.exists(csv_path):
        print(f"❌ Файл {csv_path} не найден!")
        return None, None

    # какие колонки реально есть в CSV (с учётом BOM и пробелов)
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [fn.strip().lower() for fn in reader.fieldnames]
        available = set(reader.fieldnames)

        # предупреждаем, если в CSV нет нужных полей
        missing = KEEP_FIELDS - available
        if missing:
            print(f"⚠️ В CSV нет полей {sorted(missing)} — они будут отсутствовать у игроков")

        # пересечение KEEP_FIELDS с реальными колонками CSV
        wanted = KEEP_FIELDS & available

        for row in reader:
            row = {(k or '').strip().lower(): v for k, v in row.items()}
            name = (row.get('name') or '').strip()
            if not name:
                continue

            # конвертим типы прямо при загрузке
            kw = {'name': name}
            for k in wanted:
                if k == 'name':
                    continue
                v = row.get(k, '')
                if k in _INT_FIELDS:
                    kw[k] = _to_int(v)
                elif k in _FLOAT_FIELDS:
                    kw[k] = _to_float(v)
                else:
                    kw[k] = v

            players[name] = Player(**kw)
            nicknames.append(name)

    print(f"✅ Загружено {len(nicknames)} ников, полей на игрока: {len(wanted)}/{len(available)}")

    # замер памяти (если установлен psutil)
    try:
        import psutil
        rss = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        print(f"💾 RSS после загрузки базы: {rss:.1f} МБ")
    except ImportError:
        pass

    return players, nicknames


# ---------- ЛИМИТЫ ИЗ ФАЙЛА ----------
def load_limits(limits_file="limits.csv"):
    if not os.path.exists(limits_file):
        return None
    try:
        limits = {}
        with open(limits_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                metric = row['metric'].strip()
                limits[metric] = {
                    'yellow': float(row['yellow']),
                    'orange': float(row['orange']),
                    'red':    float(row['red']),
                    'purple': float(row['purple'])
                }
        return limits
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {limits_file}: {e}")
        return None


# ---------- OCR  ----------
def get_ocr_texts_lens(img):
    """
    Распознаёт текст 
    Возвращает список строк (для совместимости со старым кодом).
    """
    lens = LensAPI()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(lens.process_image(img))
        loop.close()
        if isinstance(result, dict):
            text = result.get('ocr_text', '')
            if text:
                return [text]   # оборачиваем в список, как раньше
    except Exception as e:
        print(f"⚠️ Ошибка Oracle: {e}")
    return []


# ---------- РУЧНОЙ ПОИСК ----------
def manual_search(players, nicknames, limits):
    global team_buffer

    print("\n📝 Ручной ввод ников (до 10 штук).")
    print("   Вводите ники по одному, каждый с новой строки.")
    print("   Для завершения введите пустую строку или 'done'.")
    print("   Можно также ввести несколько ников через запятую.\n")

    raw_inputs = []
    count = 0
    while count < MAX_PLAYERS:
        line = input(f"Ник #{count+1} (или пустая строка для завершения): ").strip()
        if line.lower() in ('', 'done', 'exit', 'quit'):
            break
        parts = [p.strip() for p in line.split(',') if p.strip()]
        for p in parts:
            if count >= MAX_PLAYERS:
                print(f"⚠️ Достигнут лимит {MAX_PLAYERS} ников. Остальные игнорируются.")
                break
            raw_inputs.append(p)
            count += 1

    if not raw_inputs:
        print("❌ Ники не введены.")
        return

    found_players = print_manual_players_table(
        raw_inputs=raw_inputs,
        players=players,
        nicknames=nicknames,
        limits=limits,
        normalize_ocr_word=normalize_ocr_word,
        process=process,
        fuzz=fuzz,
        get_color_icon=get_color_icon,
        safe_float=safe_float,
        safe_int=safe_int,
        safe_elo=safe_elo
    )

    if found_players:
        team_buffer.append(found_players)
        if len(team_buffer) > 2:
            team_buffer.pop(0)

    if len(found_players) >= 2:
        analyze_team(found_players, limits)
    elif len(found_players) == 1:
        print("\n💡 Для анализа команды нужно минимум 2 игрока.")


# ---------- ГЛАВНЫЙ ЦИКЛ ----------
def main():
    global team_buffer

    try:
        players, nicknames = load_players_dict(CSV_FILE)
        if not players:
            input("Нажмите Enter для выхода...")
            return

        limits = load_limits(LIMITS_FILE)
        if limits is None:
            limits = DEFAULT_LIMITS
            print("⚠️ Файл limits.csv не найден. Использую встроенные лимиты.")
        else:
            print("✅ Загружены ручные лимиты из limits.csv")

        print("\n🔄 Программа запущена в циклическом режиме.")
        print("   Команды:")
        print("     Enter      — сканировать скриншот из буфера (Oracle)")
        print("     m (manual) — ручной ввод ников (до 10)")
        print("     c          — сравнить две последние команды")
        print("     exit       — выход\n")

        while True:
            user_input = input("Введите команду: ").strip().lower()

            if user_input in ('exit', 'выход', 'quit', 'q'):
                print("👋 Выход...")
                break
            elif user_input in ('m', 'manual', 'text'):
                manual_search(players, nicknames, limits)
                continue
            elif user_input == 'c':
                if len(team_buffer) >= 2:
                    compare_two_teams(team_buffer[-2], team_buffer[-1],
                                      players, nicknames, limits,
                                      normalize_ocr_word, process, fuzz,
                                      get_color_icon, safe_float, safe_int, safe_elo)
                elif len(team_buffer) == 1:
                    print("\n⚠️ Есть только одна команда. Введите вторую:")
                    team2 = collect_team_players("КОМАНДА B", players, nicknames, limits,
                                                 normalize_ocr_word, process, fuzz,
                                                 get_color_icon, safe_float, safe_int, safe_elo,
                                                 MAX_PLAYERS)
                    if team2:
                        compare_two_teams(team_buffer[0], team2,
                                          players, nicknames, limits,
                                          normalize_ocr_word, process, fuzz,
                                          get_color_icon, safe_float, safe_int, safe_elo)
                    else:
                        print("❌ Вторая команда не введена. Отмена.")
                else:
                    print("❌ Нет данных для сравнения. Сначала найдите хотя бы одну команду (через Enter или m).")
                continue
            elif user_input != '':
                print("⚠️ Неизвестная команда. Используйте Enter для скана, m, c, exit.")
                continue

            # ------ СКАНИРОВАНИЕ СКРИНШОТА (Enter) ------
            print("📸 Копируйте скриншот в буфер (Print Screen или Win+Shift+S -> Ctrl+C)")
            print("   Нажмите Enter, когда скриншот скопирован...")
            input("   (или нажмите Ctrl+C для отмены)")

            img = ImageGrab.grabclipboard()
            if img is None:
                print("❌ В буфере обмена нет изображения.\n")
                continue

            all_matches = {}

            # ЕДИНСТВЕННЫЙ ПРОХОД – GOOGLE LENS
            print("🔍 Распознавание через Oracle...")
            texts = get_ocr_texts_lens(img)
            ordered_matches = []       # список в порядке строк
            seen_nicks = set()         # для устранения дублей

            for raw_text in texts:
                if not raw_text:
                    continue
                print("Сырой текст от Lens:", repr(raw_text))
                matches = find_matches(raw_text, nicknames, players)   # уже упорядочено
                for nick, data, score in matches:
                    if nick not in seen_nicks:
                        seen_nicks.add(nick)
                        ordered_matches.append((nick, data, score))

            # Обрезаем до MAX_PLAYERS
            ordered_matches = ordered_matches[:MAX_PLAYERS]

            # Преобразуем в формат, который ожидает print_found_players_table
            matches_for_table = [(nick, (score, data)) for nick, data, score in ordered_matches]

            if not matches_for_table:
                print("⚠️ Ничего не найдено. Попробуйте другой скриншот или введите ники вручную (команда m).")
                print("\n" + "-" * 50 + "\n")
                continue

            print_found_players_table(
                sorted_matches=matches_for_table,
                limits=limits,
                get_color_icon=get_color_icon,
                safe_float=safe_float,
                safe_int=safe_int,
                safe_elo=safe_elo,
                max_players=MAX_PLAYERS
            )

            # Сохраняем в буфер и анализируем
            if ordered_matches:
                players_data = [data for _, data, _ in ordered_matches]
                team_buffer.append(players_data)
                if len(team_buffer) > 2:
                    team_buffer.pop(0)
                analyze_team(players_data, limits)

            print("\n" + "-" * 50 + "\n")

    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем.")
    except Exception as e:
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА:")
        traceback.print_exc()
        with open(CRASH_LOG, "a", encoding="utf-8") as f: 
            from datetime import datetime
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Критическая ошибка в main\n")
            f.write(traceback.format_exc())
            f.write("-" * 80 + "\n")
    finally:
        input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()