import re

# ---------- ПОЛНАЯ ТРАНСЛИТЕРАЦИЯ КИРИЛЛИЦЫ ----------
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
    'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'u', 'й': 'u', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'h', 'о': 'o', 'п': 'n', 'р': 'p',
    'с': 'c', 'т': 't', 'у': 'y', 'ф': 'f', 'х': 'x', 'ц': 'c',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
    # украинские и редкие
    'ѵ': 'v', 'і': 'i', 'ї': 'i', 'є': 'e', 'ґ': 'g',
}


def normalize_ocr_word(word):
    """
    Приводит ник к единому виду:
    - нижний регистр
    - удаляет суффиксы @psn, @live, @xbox и т.п.
    - удаляет спецсимволы (точки, скобки, восклицательные и т.д.)
    - транслитерирует кириллицу в латиницу
    - схлопывает множественные подчёркивания/дефисы
    """
    word = word.lower()

    # Убираем платформенные суффиксы
    word = re.sub(r'@(psn|live|xbox|pc|ru|en|de|fr)$', '', word)

    # Убираем спецсимволы, оставляем: a-z, 0-9, _, -, пробелы (их уберём позже)
    word = re.sub(r'[.\-\[\](){}<>!@#$%^&*+=|\\:;\"\'`~,]', '', word)

    # Транслитерация кириллицы → латиница
    for cyr, lat in CYR_TO_LAT.items():
        word = word.replace(cyr, lat)

    # Схлопываем множественные подчёркивания/дефисы
    word = re.sub(r'_{2,}', '_', word)
    word = re.sub(r'-{2,}', '-', word)

    # Убираем _ и - в начале и конце
    word = re.sub(r'^[_-]+', '', word)
    word = re.sub(r'[_-]+$', '', word)

    return word


def extract_lines(text):
    """Разбивает текст на непустые строки."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def clean_decorators(line):
    """Удаляет декоративные III, VVV, |||, --- в начале и конце строки."""
    patterns = [
        r'^III\s*', r'\s*III$',
        r'^VVV\s*', r'\s*VVV$',
        r'^[|\-]{3,}\s*', r'\s*[|\-]{3,}$',
    ]
    for pat in patterns:
        line = re.sub(pat, '', line)
    return line.strip()


def find_matches(text, nicknames, players, min_nick_len=4, debug=False):
    """
    Ищет ники в тексте от OCR.
    text — сырой текст от Google Lens
    nicknames — список ников из базы
    players — словарь {nick: data}
    min_nick_len — минимальная длина ника для поиска по подстроке (защита от -h-, u-)
    """
    lines = extract_lines(text)
    if not lines:
        return []

    # Подготовка: нормализованные ники
    nick_to_norm = {n: normalize_ocr_word(n) for n in nicknames}
    norm_to_nick = {norm: name for name, norm in nick_to_norm.items()}

    if debug:
        print("\n=== find_matches ===")
        print(f"Получен текст (repr): {repr(text)}")
        print(f"Строки после разбивки: {lines}")

    seen_nicks = set()
    ordered_result = []

    for line in lines:
        if debug:
            print(f"\n--- Обработка строки: '{line}' ---")

        cleaned = clean_decorators(line)
        if debug:
            print(f"После очистки декораторов: '{cleaned}'")

        if not cleaned:
            continue

        line_norm = normalize_ocr_word(cleaned).replace(' ', '')
        if debug:
            print(f"Нормализованная строка: '{line_norm}'")

        best_nick = None
        best_score = 0

        # Поиск по подстроке (с защитой от коротких ников)
        for norm_nick, original_nick in norm_to_nick.items():
            if len(norm_nick) < min_nick_len:
                continue  # слишком короткий — пропускаем

            if norm_nick in line_norm:
                # Штраф за длину: ник должен занимать хотя бы 40% строки
                len_ratio = len(norm_nick) / len(line_norm) if line_norm else 0
                if len_ratio < 0.4:
                    continue

                score = 100 + len(norm_nick)
                if debug:
                    print(f"  Найдена подстрока '{norm_nick}' -> {original_nick}, балл {score}")
                if score > best_score:
                    best_score = score
                    best_nick = original_nick

        if best_nick:
            if debug:
                print(f"Выбран лучший: {best_nick} с баллом {best_score}")
            if best_nick not in seen_nicks:
                seen_nicks.add(best_nick)
                ordered_result.append((best_nick, players[best_nick], best_score))
        else:
            if debug:
                print("Подстрок не найдено.")

    if debug:
        print(f"Итоговый результат: {[(x[0], x[2]) for x in ordered_result]}")

    return ordered_result