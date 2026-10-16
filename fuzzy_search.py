# fuzzy_search.py
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler
import jellyfish

def find_best_match(norm_raw, norm_list, threshold=70):
    """
    Улучшенный fuzzy-поиск по нормализованным строкам.
    norm_raw – нормализованный входной ник
    norm_list – список нормализованных ников из базы
    """
    best_match = None
    best_score = 0

    for candidate in norm_list:
        # 1. Базовые метрики
        score_lev = fuzz.ratio(norm_raw, candidate)
        score_jw = JaroWinkler.similarity(norm_raw, candidate) * 100

        # 2. Комбинированный скор
        score = (score_lev * 0.5 + score_jw * 0.5)

        # 3. Фильтр по длине
        if abs(len(norm_raw) - len(candidate)) > 3:
            score *= 0.8

        # 4. Бонус за совпадение 4 символов в центре
        if len(norm_raw) >= 6 and len(candidate) >= 6:
            mid_raw = norm_raw[len(norm_raw)//2 - 2 : len(norm_raw)//2 + 2]
            mid_cand = candidate[len(candidate)//2 - 2 : len(candidate)//2 + 2]
            if mid_raw == mid_cand:
                score += 10

        # 5. Фонетический поиск (Metaphone)
        try:
            if jellyfish.metaphone(norm_raw) == jellyfish.metaphone(candidate):
                score += 10
        except Exception:
            pass

        # 6. Сравнение с порогом
        if score >= threshold and score > best_score:
            best_score = score
            best_match = candidate

    return best_match, best_score


def search_nick(norm_raw, norm_list, threshold=70):
    """
    norm_raw – нормализованный входной ник
    norm_list – список нормализованных ников из базы
    Возвращает (лучший_нормализованный_ник, оценка)
    """
    if norm_raw in norm_list:
        return norm_raw, 100

    return find_best_match(norm_raw, norm_list, threshold)