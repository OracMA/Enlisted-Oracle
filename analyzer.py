# analyzer.py
from utils import safe_float, safe_int, safe_elo, player_confidence, weighted_mean, confidence_emoji
import math
from collections import defaultdict
import numpy as np

# ---------- КОНФИГУРАЦИЯ ----------
MIN_MATCHES_CONFIDENCE = 10
LOW_CONFIDENCE_MATCHES = 5

DEFAULT_WEIGHTS = {
    'captures': 1.5,
    'kd': 1.0,
    'win_percent': 1.2,
    'headshots': 0.8,
    'vehicles': 1.0,
    'built': 1.0,
    'apc_spawns': 0.9,
    'elo': 1.4
}

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def player_confidence(matches: int):
    if matches <= 0:
        return 0.1, "very_low"
    if matches < LOW_CONFIDENCE_MATCHES:
        return 0.2, "very_low"
    if matches < MIN_MATCHES_CONFIDENCE:
        return 0.5, "low"
    w = min(1.0, math.sqrt(matches) / 10.0)
    return w, "high"

def weighted_mean(values, weights):
    total_w = sum(weights) or 1.0
    return sum(v * w for v, w in zip(values, weights)) / total_w

def median_iqr(values):
    if not values:
        return 0.0, 0.0
    med = np.median(values)
    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    return med, iqr

def detect_outliers(values):
    if len(values) < 4:
        return []
    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    lower = q25 - 1.5 * iqr
    upper = q75 + 1.5 * iqr
    return [i for i, v in enumerate(values) if v < lower or v > upper]

def normalize_name(name: str) -> str:
    return name.strip().lower()

def dedupe_players(players_data):
    groups = defaultdict(list)
    for p in players_data:
        groups[normalize_name(p.get('name', ''))].append(p)
    merged = []
    for name, items in groups.items():
        if len(items) == 1:
            merged.append(items[0])
            continue
        total_matches = sum(safe_int(i.get('matches', 0)) for i in items) or 1
        agg = {'name': items[0].get('name')}
        for key in ['kd', 'win_percent', 'headshots', 'captures', 'vehicles', 'built', 'apc_spawns', 'elo', 'kills', 'score']:
            vals = [safe_float(i.get(key, 0)) for i in items]
            matches = [safe_int(i.get('matches', 0)) or 1 for i in items]
            agg[key] = sum(v * m for v, m in zip(vals, matches)) / sum(matches)
        agg['matches'] = total_matches
        merged.append(agg)
    return merged

def is_bot_like(player):
    matches = safe_int(player.get('matches', 0))
    kd = safe_float(player.get('kd', 0))
    if matches > 10000 and kd < 0.1:
        return True
    name = player.get('name', '')
    if len(name) > 30 and name.count('_') > 5:
        return True
    return False

def confidence_emoji(conf: str) -> str:
    return {"very_low": "⚠️", "low": "⚠️", "high": "✅"}.get(conf, "❓")

# ---------- КАТЕГОРИЗАЦИЯ ----------
def categorize(value, metric, limits):
    lim = limits[metric]
    if value >= lim['purple']:
        return 'purple'
    elif value >= lim['red']:
        return 'red'
    elif value >= lim['orange']:
        return 'orange'
    elif value >= lim['yellow']:
        return 'yellow'
    else:
        return 'green'

# ---------- НОВЫЕ ГРУППЫ ИГРОКОВ ----------
def is_elite(player, limits):
    """ЭЛИТА: ≥3 из 5: KD≥1.8, WR≥65%, ELO≥1800, Хедшоты≥300, Захваты≥40."""
    kd = safe_float(player.get('kd', 0))
    wr = safe_float(player.get('win_percent', 0))
    elo = safe_elo(player.get('elo', 0))
    hs = safe_float(player.get('headshots', 0))
    cap = safe_float(player.get('captures', 0))
    conditions = sum([
        kd >= 1.8,
        wr >= 65,
        elo >= 1800,
        hs >= 300,
        cap >= 40
    ])
    return conditions >= 3

def is_stable(player, limits):
    """СТАБИЛЬНЫЙ: KD 0.9–1.3, WR 40–55%, ELO 900–1400, Техника 10–40, Постройки 10–60, Захваты 10–25."""
    kd = safe_float(player.get('kd', 0))
    wr = safe_float(player.get('win_percent', 0))
    elo = safe_elo(player.get('elo', 0))
    veh = safe_float(player.get('vehicles', 0))
    built = safe_float(player.get('built', 0))
    cap = safe_float(player.get('captures', 0))
    return all([
        0.9 <= kd <= 1.3,
        40 <= wr <= 55,
        900 <= elo <= 1400,
        10 <= veh <= 40,
        10 <= built <= 60,
        10 <= cap <= 25
    ])

def is_picky(player, limits):
    """ПИКОВЫЙ: ровно один параметр >= red, остальные < red."""
    params = {
        'kd': safe_float(player.get('kd', 0)),
        'wr': safe_float(player.get('win_percent', 0)),
        'elo': safe_elo(player.get('elo', 0)),
        'hs': safe_float(player.get('headshots', 0)),
        'cap': safe_float(player.get('captures', 0)),
        'veh': safe_float(player.get('vehicles', 0)),
        'built': safe_float(player.get('built', 0))
    }
    red_count = sum(1 for key, val in params.items() if val >= limits[key]['red'])
    return red_count == 1

def is_weak(player, limits):
    """СЛАБЫЙ: KD ≤ 0.8, WR ≤ 45%, ELO ≤ 900, Техника ≤ 10, Постройки ≤ 10, Захваты ≤ 10."""
    kd = safe_float(player.get('kd', 0))
    wr = safe_float(player.get('win_percent', 0))
    elo = safe_elo(player.get('elo', 0))
    veh = safe_float(player.get('vehicles', 0))
    built = safe_float(player.get('built', 0))
    cap = safe_float(player.get('captures', 0))
    return all([
        kd <= 0.8,
        wr <= 45,
        elo <= 900,
        veh <= 10,
        built <= 10,
        cap <= 10
    ])

def classify_player(player, limits):
    """Возвращает группу игрока: 'elite', 'stable', 'picky', 'weak', 'other'."""
    if is_elite(player, limits):
        return 'elite'
    if is_stable(player, limits):
        return 'stable'
    if is_picky(player, limits):
        return 'picky'
    if is_weak(player, limits):
        return 'weak'
    return 'other'

# ---------- РАСЧЁТЫ КОМАНДЫ ----------
def count_high_elo_players(players_data, threshold=2000):
    return sum(1 for p in players_data if safe_elo(p.get('elo', 0)) >= threshold)

def detect_zadrots(players_data, limits):
    zadrots = []
    for p in players_data:
        kd = safe_float(p.get('kd', 0))
        hs = safe_float(p.get('headshots', 0))
        cap = safe_float(p.get('captures', 0))
        if kd >= limits['kd']['red'] and hs >= limits['hs']['red'] and cap >= limits['cap']['red']:
            zadrots.append(p)
    return zadrots

def compute_roles(players_data, limits=None):
    """
    Считает роли. Игрок может попасть сразу в НЕСКОЛЬКО ролей,
    но каждая роль считается только при ФИОЛЕТОВОМ пороге.
    """
    roles = {'engineer': 0, 'vehicle': 0, 'infantry': 0, 'support': 0}

    # Пороги уровня purple
    if limits:
        eng_thr = limits['built']['purple']    # 450
        veh_thr = limits['veh']['purple']      # 400
        cap_thr = limits['cap']['purple']      # 70
        apc_thr = limits['apc']['purple']      # 80
    else:
        eng_thr, veh_thr, cap_thr, apc_thr = 450, 400, 70, 80

    for p in players_data:
        if safe_int(p.get('built', 0))      >= eng_thr:
            roles['engineer'] += 1
        if safe_int(p.get('vehicles', 0))   >= veh_thr:
            roles['vehicle'] += 1
        if safe_int(p.get('captures', 0))   >= cap_thr:
            roles['infantry'] += 1
        if safe_int(p.get('apc_spawns', 0)) >= apc_thr:
            roles['support'] += 1
    return roles

def detect_bot_team(avg_stats, players_data, low_conf_ratio, roles, limits):
    strong_exists = False
    for p in players_data:
        kd = safe_float(p.get('kd', 0))
        wr = safe_float(p.get('win_percent', 0))
        cap = safe_float(p.get('captures', 0))
        if kd >= limits['kd']['red'] or wr >= limits['wr']['red'] or cap >= limits['cap']['red']:
            strong_exists = True
            break
    high_players = sum(1 for p in players_data if safe_elo(p.get('elo', 0)) >= 1500 and safe_float(p.get('kd', 0)) >= 1.5)
    if strong_exists or avg_stats.get('win_percent', 0) > 55 or high_players >= 3:
        return False, []
    conditions = 0
    reasons = []
    if avg_stats.get('elo', 0) < 700:
        conditions += 1
        reasons.append("Средний ELO < 700")
    if avg_stats.get('kd', 0) < 1.0 and avg_stats.get('win_percent', 0) < 45 and avg_stats.get('captures', 0) < 15:
        conditions += 1
        reasons.append("80% игроков зелёные (низкие показатели)")
    if avg_stats.get('apc_spawns', 0) < 10:
        conditions += 1
        reasons.append("Низкая мобильность (APC < 10)")
    if avg_stats.get('vehicles', 0) < 50:
        conditions += 1
        reasons.append("Низкая техника (veh < 50)")
    if avg_stats.get('captures', 0) < 20:
        conditions += 1
        reasons.append("Низкие захваты (captures < 20)")
    if low_conf_ratio >= 0.3:
        conditions += 1
        reasons.append("≥30% игроков имеют <10 матчей")
    if sum(roles.values()) < 2:
        conditions += 1
        reasons.append("Нет ролей (инженер/техник/штурмовик/саппорт)")
    if conditions >= 2:
        return True, reasons
    return False, []

def detect_strong_team(zadrots, avg_stats, roles, players_data, limits):
    strong = False
    reasons = []
    if len(zadrots) >= 2:
        strong = True
        reasons.append(f"💀 {len(zadrots)} задрота(ов)")
    if any(safe_int(p.get('apc_spawns', 0)) >= 150 for p in players_data):
        strong = True
        reasons.append("APC-монстр")
    if sum(1 for p in players_data if safe_int(p.get('vehicles', 0)) >= 150) >= 2:
        strong = True
        reasons.append(f"≥2 сильных по технике (veh ≥ 150)")
    if any(safe_int(p.get('built', 0)) >= 200 for p in players_data):
        strong = True
        reasons.append("Инженер (built ≥ 200)")
    if avg_stats.get('elo', 0) >= 1500:
        strong = True
        reasons.append(f"Высокий ELO ({avg_stats['elo']:.0f})")
    high_elo_count = count_high_elo_players(players_data, 2000)
    if high_elo_count >= 2:
        strong = True
        reasons.append(f"💎 {high_elo_count} игрока с ELO ≥ 2000")
    return strong, reasons

def detect_weak_team(avg_stats, players_data, low_conf_ratio, roles):
    weak = False
    reasons = []
    if avg_stats.get('elo', 0) < 700:
        weak = True
        reasons.append("Низкий ELO (< 700)")
    if avg_stats.get('kd', 0) < 1.0 and avg_stats.get('win_percent', 0) < 45 and avg_stats.get('captures', 0) < 15:
        weak = True
        reasons.append("Большинство игроков имеют низкие показатели")
    if avg_stats.get('apc_spawns', 0) < 10:
        weak = True
        reasons.append("Низкая мобильность (APC < 10)")
    if avg_stats.get('captures', 0) < 20:
        weak = True
        reasons.append("Низкие захваты (captures < 20)")
    if sum(roles.values()) < 2:
        weak = True
        reasons.append("Нет выраженных ролей")
    if low_conf_ratio >= 0.3:
        weak = True
        reasons.append("≥30% игроков с малым числом матчей")
    return weak, reasons

# ---------- ОСНОВНАЯ ФУНКЦИЯ АНАЛИЗА КОМАНДЫ ----------
def analyze_team(players_data, limits):
    if not players_data:
        print("❌ Нет данных для анализа команды.")
        return

    # Дедупликация
    players_data = dedupe_players(players_data)
    n = len(players_data)

    # Добавляем веса и доверие
    for p in players_data:
        matches = safe_int(p.get('matches', 0))
        w, conf = player_confidence(matches)
        p['_weight'] = w
        p['_conf'] = conf
        p['_bot'] = is_bot_like(p)

    # Собираем взвешенные средние
    metrics = ['kd', 'win_percent', 'headshots', 'captures', 'vehicles', 'built', 'apc_spawns', 'elo']
    avg_stats = {}
    for key in metrics:
        vals = [safe_float(p.get(key, 0)) for p in players_data]
        weights = [p['_weight'] for p in players_data]
        avg_stats[key] = weighted_mean(vals, weights)

    # Выбросы
    outlier_flags = {}
    for key in metrics:
        vals = [safe_float(p.get(key, 0)) for p in players_data]
        outliers = detect_outliers(vals)
        outlier_flags[key] = outliers

    low_conf_count = sum(1 for p in players_data if p['_conf'] != 'high')
    low_conf_ratio = low_conf_count / n if n > 0 else 0

    # ---- КАТЕГОРИЗАЦИЯ ----
    def collect_categories(metric, key):
        cats = {"green": [], "yellow": [], "orange": [], "red": [], "purple": []}
        for p in players_data:
            val = safe_float(p.get(key, 0))
            cat = categorize(val, metric, limits)
            cats[cat].append((p.get('name'), val))
        return cats

    kd_cats = collect_categories('kd', 'kd')
    wr_cats = collect_categories('wr', 'win_percent')
    hs_cats = collect_categories('hs', 'headshots')
    cap_cats = collect_categories('cap', 'captures')
    veh_cats = collect_categories('veh', 'vehicles')
    built_cats = collect_categories('built', 'built')
    apc_cats = collect_categories('apc', 'apc_spawns')

    # ---- РАСЧЁТЫ ----
    zadrots = detect_zadrots(players_data, limits)
    roles = compute_roles(players_data, limits)
    bot_team, bot_reasons = detect_bot_team(avg_stats, players_data, low_conf_ratio, roles, limits)
    strong_team, strong_reasons = detect_strong_team(zadrots, avg_stats, roles, players_data, limits)
    weak_team, weak_reasons = detect_weak_team(avg_stats, players_data, low_conf_ratio, roles)

    # ---- ГРУППЫ ИГРОКОВ ----
    group_counts = {'elite': 0, 'stable': 0, 'picky': 0, 'weak': 0, 'other': 0}
    for p in players_data:
        group = classify_player(p, limits)
        group_counts[group] += 1

    # ---- ВЫВОД ----
    print("\n📌 АНАЛИЗ КОМАНДЫ (общий портрет):")
    print(f"   KD:      {avg_stats['kd']:.2f}")
    print(f"   WR:      {avg_stats['win_percent']:.1f}%")
    print(f"   Хедшоты: {avg_stats['headshots']:.1f}")
    print(f"   Захваты: {avg_stats['captures']:.2f}")
    print(f"   Техника: {avg_stats['vehicles']:.1f}")
    print(f"   Постройки: {avg_stats['built']:.1f}")
    print(f"   БТР:     {avg_stats['apc_spawns']:.1f}")
    print(f"   ELO:     {avg_stats['elo']:.0f}")

    # ---- ДОВЕРИЕ ----
    if low_conf_ratio == 0:
        conf_msg = "✅ Высокая доверенность (все игроки ≥10 матчей)"
    elif low_conf_ratio >= 0.3:
        conf_msg = f"⚠️ Низкая доверенность: {low_conf_count} игрок(ов) имеют <10 матчей"
    else:
        conf_msg = f"⚠️ Средняя доверенность: {low_conf_count} игрок(ов) имеют <10 матчей"
    print(f"\n🔒 Доверие к данным: {conf_msg}")

    # ---- ВЫБРОСЫ ----
    print("\n📊 Выбросы (по правилу 1.5*IQR):")
    found_outlier = False
    for key, idxs in outlier_flags.items():
        if idxs:
            names = [players_data[i]['name'] for i in idxs]
            print(f"   • {key.upper()}: {', '.join(names)}")
            found_outlier = True
    if not found_outlier:
        print("   ✅ Выбросов не обнаружено.")

    # ---- РОЛИ ----
    print("\n🎯 Роли в команде:")
    print(f"   Инженеры: {roles['engineer']} (built > 100)")
    print(f"   Техники:  {roles['vehicle']} (vehicles > 100)")
    print(f"   Штурмовики: {roles['infantry']} (captures > 20)")
    print(f"   Саппорты: {roles['support']} (apc_spawns > 50)")

    # ---- ГРУППЫ ИГРОКОВ ----
    print("\n👥 ГРУППЫ ИГРОКОВ:")
    print(f"   Элита:     {group_counts.get('elite', 0)}")
    print(f"   Стабильные: {group_counts.get('stable', 0)}")
    print(f"   Пиковые:   {group_counts.get('picky', 0)}")
    print(f"   Слабые:    {group_counts.get('weak', 0)}")
    print(f"   Прочие:    {group_counts.get('other', 0)}")

    # ---- ЗАДРОТЫ ----
    if zadrots:
        zadrot_names = ", ".join(p['name'] for p in zadrots)
        print(f"\n💀 ЗАДРОТЫ (универсалы): {zadrot_names}")
    else:
        print("\n💀 Задротов не обнаружено.")

    # ---- БОТОКАТКА ----
    if bot_team:
        print("\n🤖 BOT TEAM DETECTED — команда играет как ботики:")
        for reason in bot_reasons:
            print(f"   • {reason}")

    # ---- СИЛЬНАЯ / СЛАБАЯ КОМАНДА ----
    if strong_team:
        print(f"\n⭐ Сильная команда — {', '.join(strong_reasons)}")
    if weak_team:
        print(f"\n👶 Слабая команда — {', '.join(weak_reasons)}")

    # ---- КОМБИНИРОВАННЫЕ ВЕРДИКТЫ ----
    def combined_verdict(title, cats):
        print(f"\n🔽 {title} — комбинированный вердикт:")
        purples = cats["purple"]
        reds = cats["red"]
        oranges = cats["orange"]
        yellows = cats["yellow"]
        greens = cats["green"]

        verdicts = []
        if len(purples) >= 5:
            verdicts.append("🃏 Доставайте вазелин — элита доминирует.")
        elif len(purples) >= 4:
            verdicts.append("🃏 Четыре элиты — критическая угроза.")
        elif len(purples) >= 3:
            verdicts.append("🃏 Три элиты — параметр полностью доминирует.")
        elif len(purples) >= 2:
            verdicts.append("🃏 Две элиты — серьёзная угроза.")
        elif len(purples) >= 1:
            name, val = purples[0]
            verdicts.append(f"🃏 Элита — {name} ({val})")

        if len(reds) >= 5:
            verdicts.append("🔥 Полкоманды потеют — опасно.")
        elif len(reds) >= 4:
            verdicts.append("🔥 Четыре потеющих — критическая угроза.")
        elif len(reds) >= 3:
            verdicts.append("🔥 Треть команды — потеющие.")
        elif len(reds) >= 2:
            verdicts.append("🔥 Два потеющих.")
        elif len(reds) >= 1:
            name, val = reds[0]
            verdicts.append(f"🔥 Потеющий — {name} ({val})")

        if len(oranges) >= 4:
            verdicts.append("🟠 Команда делает что-то.")
        elif len(oranges) >= 3:
            verdicts.append("🟠 Команда выше среднего.")

        if len(yellows) >= 4:
            verdicts.append("🟡 Команда делает мало.")
        elif len(yellows) >= 3:
            verdicts.append("🟡 Команда делает понемногу.")

        if len(greens) >= 4:
            verdicts.append("🥒 Полкоманды — овощи.")
        elif len(greens) >= n * 0.6:
            verdicts.append("🥒 Параметр критически слабый.")

        if not verdicts:
            verdicts.append("🙂 Параметр слабый — угрозы нет.")

        for v in verdicts:
            print("   " + v)

    print("\n🔻 Комбинированные вердикты (по категориям):")
    combined_verdict("KD (стрельба)", kd_cats)
    combined_verdict("WR (винрейт)", wr_cats)
    combined_verdict("Меткость (хедшоты)", hs_cats)
    combined_verdict("Захваты", cap_cats)
    combined_verdict("Техника", veh_cats)
    combined_verdict("Инженерка", built_cats)
    combined_verdict("БТР", apc_cats)

    # ---- КЛЮЧЕВЫЕ ИГРОКИ ----
    top_kd = max(players_data, key=lambda p: safe_float(p.get('kd', 0)))
    top_wr = max(players_data, key=lambda p: safe_float(p.get('win_percent', 0)))
    top_elo = max(players_data, key=lambda p: safe_elo(p.get('elo', 0)))
    top_cap = max(players_data, key=lambda p: safe_int(p.get('captures', 0)))
    top_veh = max(players_data, key=lambda p: safe_int(p.get('vehicles', 0)))

    print("\n🏆 Ключевые игроки:")
    print(f"   • Топ KD:  {top_kd['name']} ({safe_float(top_kd.get('kd')):.2f})")
    print(f"   • Топ WR:  {top_wr['name']} ({safe_float(top_wr.get('win_percent')):.1f}%)")
    print(f"   • Топ ELO: {top_elo['name']} ({safe_elo(top_elo.get('elo')):.0f})")
    print(f"   • Топ захватов: {top_cap['name']} ({safe_int(top_cap.get('captures', 0))})")
    print(f"   • Топ техники: {top_veh['name']} ({safe_int(top_veh.get('vehicles', 0))})")

    # ---- РЕКОМЕНДАЦИИ ----
    recs = []
    if avg_stats.get('captures', 0) < 2.0:
        recs.append("Дави по точкам — мало захватов.")
    if avg_stats.get('built', 0) < 5.0:
        recs.append("Инженерка слабая — возьмите инженера.")
    if avg_stats.get('vehicles', 0) < 10:
        recs.append("Мало техники — используй броню для давления.")
    if avg_stats.get('win_percent', 0) < 48:
        recs.append("Играй по цели — винрейт низкий.")
    if avg_stats.get('kd', 0) < 1.0:
        recs.append("Низкий K/D — избегайте лобовых дуэлей.")
    if recs:
        print("\n💡 Рекомендации:")
        for rec in recs:
            print(f"   • {rec}")

    # ---- ФИНАЛЬНЫЙ ВЕРДИКТ ----
    color_score = {'green':0, 'yellow':1, 'orange':2, 'red':3, 'purple':4}
    total_weighted_color = 0.0
    total_weight = 0.0
    for p in players_data:
        w = p['_weight']
        kd_val = safe_float(p.get('kd', 0))
        kd_cat = categorize(kd_val, 'kd', limits)
        wr_val = safe_float(p.get('win_percent', 0))
        wr_cat = categorize(wr_val, 'wr', limits)
        cap_val = safe_float(p.get('captures', 0))
        cap_cat = categorize(cap_val, 'cap', limits)
        avg_color = (color_score[kd_cat] + color_score[wr_cat] + color_score[cap_cat]) / 3.0
        total_weighted_color += avg_color * w
        total_weight += w

    if total_weight == 0:
        total_weight = 1.0
    team_color_score = total_weighted_color / total_weight

    if team_color_score <= 0.8:
        base_verdict = "🔴 Команда слабая (преобладают низкие показатели). Используйте агрессивную тактику."
        rofl = "Вас ждёт хардкорная боль. Запаситесь терпением."
    elif team_color_score <= 1.8:
        base_verdict = "🟡 Команда нестабильная (средние показатели). Бой может быть непредсказуемым."
        rofl = "ХЗ вообще."
    elif team_color_score <= 2.8:
        base_verdict = "🟠 Команда среднего уровня. Шансы 50/50."
        rofl = "Крути рулетку."
    else:
        base_verdict = "🟢 Команда сильная (высокие показатели). Ожидайте сложный бой."
        rofl = "Поздравляю, вы попали в ад. Доставайте вазелин."

    print("\n📌 ОБЩИЙ ВЕРДИКТ КОМАНДЫ:")
    print(f"   {base_verdict}")
    print(f"   {rofl}")

    # Дополнительные сообщения
    if zadrots:
        zadrot_names = ", ".join(p['name'] for p in zadrots)
        if len(zadrots) >= 2:
            print(f"   💀💀 Внимание — обнаружены задроты ({zadrot_names}). Критическая угроза.")
        else:
            print(f"   💀 Обнаружен задрот — {zadrot_names}.")

    if strong_team:
        print(f"   ⭐ Сильная команда — {', '.join(strong_reasons)}")
    if weak_team:
        print(f"   👶 Слабая команда — {', '.join(weak_reasons)}")
    if bot_team:
        print(f"   🤖 BOT TEAM DETECTED — играйте агрессивно, это боты.")

    if avg_stats.get('captures', 0) >= 34:
        print("   🚩 Команда захватывает точки — играйте на удержание.")
    if avg_stats.get('elo', 0) >= 1500:
        print("   🤝 Команда играет слаженно — высокая координация.")
    if low_conf_ratio >= 0.3:
        print("   ⚠️ Данные ненадёжны — много игроков с малым количеством матчей.")

    print()