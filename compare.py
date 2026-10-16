# compare.py
# ИЗМЕНЕНО:
#   - Флаг DEBUG: включает подробный лог расчётов в консоль.
#   - compute_role синхронизирован с compute_roles (пороги из limits).
#   - Развёрнутый вывод финального score.

from utils import safe_float, safe_int, safe_elo, player_confidence, weighted_mean, confidence_emoji
from output import print_manual_players_table, render_table
from analyzer import (
    detect_zadrots, compute_roles,
    detect_strong_team, detect_weak_team, detect_bot_team
)

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

# ИЗМЕНЕНО: флаг отладки — показывать расчёты в консоль
DEBUG = True

COMPARE_METRICS = [
    ('kd', 'K/D'),
    ('win_percent', 'Винрейт %'),
    ('headshots', 'Хедшоты'),
    ('captures', 'Захваты'),
    ('vehicles', 'Техника'),
    ('built', 'Постройки'),
    ('apc_spawns', 'БТР'),
    ('elo', 'ELO')
]

FINAL_WEIGHTS = {
    'elo':         2.5,
    'kd':          2.5,
    'win_percent': 2.0,
    'captures':    2.5,
    'vehicles':    1.3,
    'apc_spawns':  1.9,
    'built':       1.3,
    'headshots':   2.3,
}

METRIC_RANGES = {
    'kd':          (0.3, 3.5),
    'win_percent': (30, 95),
    'headshots':   (0, 5000),       # было 2000, стало 5000
    'captures':    (0, 1000),       # было 200, стало 1000
    'vehicles':    (0, 5000),       # было 1888, стало 5000
    'built':       (0, 5000),       # было 2000, стало 5000
    'apc_spawns':  (0, 3000),       # было 600, стало 3000
    'elo':         (200, 2600),
}

ROLE_BONUS = {
    'engineer': 0.1,
    'vehicle':  0.05,
    'infantry': 0.25,
    'support':  0.1,
}

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def get_strength_grade(wins, total):
    if wins >= total - 1:
        return "сокрушительно"
    elif wins >= total * 0.75:
        return "сильно"
    elif wins >= total * 0.5:
        return "заметно"
    elif wins >= total * 0.25:
        return "немного"
    return "примерно"


def top3_avg(team, key):
    vals = sorted([safe_float(p.get(key, 0)) for p in team], reverse=True)
    if not vals:
        return 0
    return sum(vals[:3]) / min(3, len(vals))


def stability_factor(player):
    m = safe_int(player.get('matches', 0))
    if m < 10:    return 0.5
    if m < 50:    return 0.8
    if m < 200:   return 1.0
    if m < 500:   return 1.1
    return 1.2


def normalize(key, val, team_size=None, is_sum_elo=False):
    if key == 'elo' and is_sum_elo and team_size:
        lo = 200 * team_size
        hi = 2600 * team_size
        val = max(lo, min(val, hi))
        return (val - lo) / (hi - lo) if hi > lo else 0

    lo, hi = METRIC_RANGES.get(key, (0, 1))
    val = max(lo, min(val, hi))
    if hi <= lo:
        return 0
    return (val - lo) / (hi - lo)


def count_elite_players(team, limits):
    elite_names = []
    for p in team:
        purple_count = 0
        checks = [
            ('kd', safe_float(p.get('kd', 0))),
            ('wr', safe_float(p.get('win_percent', 0))),
            ('elo', safe_elo(p.get('elo', 0))),
            ('hs', safe_float(p.get('headshots', 0))),
            ('cap', safe_float(p.get('captures', 0))),
            ('veh', safe_float(p.get('vehicles', 0))),
            ('built', safe_float(p.get('built', 0))),
        ]
        for key, val in checks:
            if key in limits and val >= limits[key]['purple']:
                purple_count += 1
        if purple_count >= 3:
            elite_names.append(p.get('name', '?'))
    return len(elite_names), elite_names


def team_power_bonus(team, limits, zadrots):
    bonus = 0.0
    if len(zadrots) >= 3:
        bonus += 0.6
    elif len(zadrots) == 2:
        bonus += 0.3
    elif len(zadrots) == 1:
        bonus += 0.2

    n_elite, _ = count_elite_players(team, limits)
    if n_elite >= 5:
        bonus += 0.67
    elif n_elite >= 4:
        bonus += 0.4
    elif n_elite >= 3:
        bonus += 0.3
    elif n_elite == 2:
        bonus += 0.2
    elif n_elite == 1:
        bonus += 0.1

    return bonus


def detect_smurf(player, limits):
    matches = safe_int(player.get('matches', 0))
    if matches >= 20:
        return False
    kd = safe_float(player.get('kd', 0))
    hs = safe_float(player.get('headshots', 0))
    wr = safe_float(player.get('win_percent', 0))
    return (
        kd >= limits['kd']['orange'] and
        hs >= limits['hs']['orange'] and
        wr >= limits['wr']['orange']
    )


def detect_bot_player(player, limits):
    matches = safe_int(player.get('matches', 0))
    if matches >= 20:
        return False
    elo = safe_float(player.get('elo', 0))
    if elo >= 700:
        return False
    kd = safe_float(player.get('kd', 0))
    hs = safe_float(player.get('headshots', 0))
    cap = safe_float(player.get('captures', 0))
    return (
        kd < limits['kd']['yellow'] and
        hs < limits['hs']['yellow'] and
        cap < limits['cap']['yellow']
    )


def compute_role(p, limits=None):
    """Возвращает ОДНУ главную роль игрока по ФИОЛЕТОВЫМ порогам."""
    if limits:
        veh_thr = limits['veh']['purple']      # ← было 'orange'
        eng_thr = limits['built']['purple']    # ← было 'orange'
        cap_thr = limits['cap']['purple']      # ← было 'orange'
        apc_thr = limits['apc']['purple']      # ← было 'orange'
    else:
        veh_thr, eng_thr, cap_thr, apc_thr = 400, 450, 70, 80

    # Приоритет: vehicle > engineer > infantry > support
    if safe_int(p.get('vehicles', 0))   >= veh_thr:
        return 'vehicle'
    if safe_int(p.get('built', 0))      >= eng_thr:
        return 'engineer'
    if safe_int(p.get('captures', 0))   >= cap_thr:
        return 'infantry'
    if safe_int(p.get('apc_spawns', 0)) >= apc_thr:
        return 'support'
    return 'infantry'                       # «прочие» — тоже infantry


def calc_weighted_avg_with_role_weights(team, key, limits=None):
    """Веса: фиолетовые роли получают небольшой бонус. Все остальные — ×1.0."""
    vals = [safe_float(p.get(key, 0)) for p in team]
    weights = []
    for p in team:
        base = p.get('_weight', 1.0)
        role = compute_role(p, limits)

        # Проверяем, попал ли игрок хоть в одну фиолетовую роль
        veh = safe_int(p.get('vehicles', 0))
        eng = safe_int(p.get('built', 0))
        cap = safe_int(p.get('captures', 0))
        apc = safe_int(p.get('apc_spawns', 0))

        is_elite = (
            veh >= (limits['veh']['purple']     if limits else 400) or
            eng >= (limits['built']['purple']   if limits else 450) or
            cap >= (limits['cap']['purple']     if limits else 70)  or
            apc >= (limits['apc']['purple']     if limits else 80)
        )

        if not is_elite:
            w = base * 1.0        # ← обычные игроки — БЕЗ штрафа
        elif role == 'vehicle':
            w = base * 1.06       # ← было 1.2, теперь мягче
        elif role == 'engineer':
            w = base * 1.05       # ← было 1.1, теперь мягче
        elif role == 'infantry':
            w = base * 1.03
        elif role == 'support':
            w = base * 1.03
        else:
            w = base * 1.0

        weights.append(w)
    return weighted_mean(vals, weights)

def calc_capped_avg(team, key, limits=None, cap_ratio=0.25):
    """
    Считает средневзвешенное значение метрики, но не даёт ни одному игроку
    влиять на результат больше, чем cap_ratio от общей суммы.
    По умолчанию — 25%.
    """
    if not team:
        return 0.0

    vals = [safe_float(p.get(key, 0)) for p in team]
    weights = []
    for p in team:
        base = p.get('_weight', 1.0)
        role = compute_role(p, limits)
        if role == 'vehicle':
            w = base * 1.2
        elif role == 'engineer':
            w = base * 1.1
        elif role in ('assault', 'support'):
            w = base * 1.05
        else:
            w = base * 1.0
        weights.append(w)

    # Взвешенные значения
    weighted_vals = [v * w for v, w in zip(vals, weights)]
    total = sum(weighted_vals)

    if total == 0:
        return 0.0

    # Максимально допустимый вклад одного игрока
    max_contribution = total * cap_ratio

    # Обрезаем всё, что выше порога
    capped_vals = [min(wv, max_contribution) for wv in weighted_vals]

    # Возвращаем среднее
    return sum(capped_vals) / len(capped_vals)


# ------------------------------------------------------------
# MANUAL INPUT
# ------------------------------------------------------------

def collect_team_players(team_name, players, nicknames, limits,
                         normalize_ocr_word, process, fuzz,
                         get_color_icon, safe_float, safe_int, safe_elo,
                         max_players=10):

    print(f"\n📝 Ввод ников для {team_name} (до {max_players} штук).")
    print("   Вводите ники по одному, каждый с новой строки.")
    print("   Для завершения введите пустую строку или 'done'.\n")

    raw_inputs = []
    while len(raw_inputs) < max_players:
        line = input(f"Ник #{len(raw_inputs)+1}: ").strip()
        if line.lower() in ('', 'done'):
            break
        raw_inputs.extend([p.strip() for p in line.split(',') if p.strip()])

    if not raw_inputs:
        print("❌ Ники не введены.")
        return []

    return print_manual_players_table(
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


# ------------------------------------------------------------
# MAIN COMPARISON
# ------------------------------------------------------------

def compare_two_teams(team_a, team_b, players, nicknames, limits,
                      normalize_ocr_word, process, fuzz,
                      get_color_icon, safe_float, safe_int, safe_elo):

    if not team_a or not team_b:
        print("❌ Нет данных для сравнения.")
        return

    print("\n" + "=" * 80)
    print("📊 СРАВНЕНИЕ ДВУХ КОМАНД")
    print("=" * 80)

    # ------------------------------------------------------------
    # ENRICH
    # ------------------------------------------------------------
    def set_attr(p, key, value):
        if isinstance(p, dict):
            p[key] = value
        else:
            try:
                setattr(p, key, value)
            except AttributeError:
                pass

    def get_attr(p, key, default=0):
        if isinstance(p, dict):
            return p.get(key, default)
        return getattr(p, key, default)

    def enrich(team):
        for p in team:
            matches = safe_int(get_attr(p, 'matches', 0))
            w, conf = player_confidence(matches)
            stab = stability_factor(p)
            set_attr(p, '_weight', w * stab)
            set_attr(p, '_conf', conf)
        return team

    team_a = enrich(team_a)
    team_b = enrich(team_b)

    # ------------------------------------------------------------
    # WEIGHTED AVERAGES
    # ------------------------------------------------------------
    avg_a = {k: calc_capped_avg(team_a, k, limits, cap_ratio=0.25) for k, _ in COMPARE_METRICS}
    avg_b = {k: calc_capped_avg(team_b, k, limits, cap_ratio=0.25) for k, _ in COMPARE_METRICS}

    sum_elo_a = sum(safe_elo(get_attr(p, 'elo', 0)) for p in team_a)
    sum_elo_b = sum(safe_elo(get_attr(p, 'elo', 0)) for p in team_b)
    avg_elo_a = sum_elo_a / len(team_a) if team_a else 0
    avg_elo_b = sum_elo_b / len(team_b) if team_b else 0

    # ------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------
    def conf_stats(team):
        total = len(team)
        high = sum(1 for p in team if get_attr(p, '_conf', 'low') == 'high')
        return high, total - high, total

    high_a, low_a, total_a = conf_stats(team_a)
    high_b, low_b, total_b = conf_stats(team_b)

    # ------------------------------------------------------------
    # ROLES / ZADROTS / SMURFS / BOTS
    # ------------------------------------------------------------
    roles_a = compute_roles(team_a, limits)
    roles_b = compute_roles(team_b, limits)

    zadrots_a = detect_zadrots(team_a, limits)
    zadrots_b = detect_zadrots(team_b, limits)

    smurfs_a = [p for p in team_a if detect_smurf(p, limits)]
    smurfs_b = [p for p in team_b if detect_smurf(p, limits)]

    bots_a = [p for p in team_a if detect_bot_player(p, limits)]
    bots_b = [p for p in team_b if detect_bot_player(p, limits)]

    bonus_a = team_power_bonus(team_a, limits, zadrots_a)
    bonus_b = team_power_bonus(team_b, limits, zadrots_b)

    # ------------------------------------------------------------
    # STRONG / WEAK / BOT TEAMS
    # ------------------------------------------------------------
    def avg_stats(team):
        return {
            k: weighted_mean([safe_float(p.get(k, 0)) for p in team],
                             [p['_weight'] for p in team])
            for k, _ in COMPARE_METRICS
        }

    stats_a = avg_stats(team_a)
    stats_b = avg_stats(team_b)

    low_ratio_a = (len(team_a) - high_a) / len(team_a) if team_a else 0
    low_ratio_b = (len(team_b) - high_b) / len(team_b) if team_b else 0

    strong_a, strong_reasons_a = detect_strong_team(zadrots_a, stats_a, roles_a, team_a, limits)
    strong_b, strong_reasons_b = detect_strong_team(zadrots_b, stats_b, roles_b, team_b, limits)

    weak_a, weak_reasons_a = detect_weak_team(stats_a, team_a, low_ratio_a, roles_a)
    weak_b, weak_reasons_b = detect_weak_team(stats_b, team_b, low_ratio_b, roles_b)

    bot_a, bot_reasons_a = detect_bot_team(stats_a, team_a, low_ratio_a, roles_a, limits)
    bot_b, bot_reasons_b = detect_bot_team(stats_b, team_b, low_ratio_b, roles_b, limits)

    # ------------------------------------------------------------
    # TABLE
    # ------------------------------------------------------------
    headers = ["Параметр", "Команда A", "Команда B", "Разница", "Сильнее"]
    rows = []

    for key, label in COMPARE_METRICS:
        a = avg_a[key]
        b = avg_b[key]
        diff = a - b
        stronger = "🟢 Команда A" if diff > 0.01 else "🔴 Команда B" if diff < -0.01 else "⚖️ Равно"
        fmt = "{:.2f}" if key in ('kd', 'elo') else "{:.1f}"
        pct = f"({(a/b - 1) * 100:+.1f}%)" if b != 0 else ""
        rows.append([label, fmt.format(a), fmt.format(b), f"{diff:+.1f} {pct}", stronger])

    elo_avg_diff = avg_elo_a - avg_elo_b
    if elo_avg_diff > 0:
        stronger_avg_elo = "🟢 Команда A"
    elif elo_avg_diff < 0:
        stronger_avg_elo = "🔴 Команда B"
    else:
        stronger_avg_elo = "⚖️ Равно"
    rows.append([
        "Средний ELO",
        f"{avg_elo_a:.0f}",
        f"{avg_elo_b:.0f}",
        f"{elo_avg_diff:+.0f}",
        stronger_avg_elo
    ])

    elo_diff = sum_elo_a - sum_elo_b
    if elo_diff > 0:
        stronger_elo = "🟢 Команда A"
    elif elo_diff < 0:
        stronger_elo = "🔴 Команда B"
    else:
        stronger_elo = "⚖️ Равно"
    rows.append([
        "Суммарный ELO",
        f"{sum_elo_a:.0f}",
        f"{sum_elo_b:.0f}",
        f"{elo_diff:+.0f}",
        stronger_elo
    ])

    print("\n📋 СРАВНИТЕЛЬНАЯ ТАБЛИЦА:")
    render_table(headers, rows)

    # ------------------------------------------------------------
    # ROLES
    # ------------------------------------------------------------
    print("\n🎯 РОЛИ:")
    print(f"   Команда A: инженеры {roles_a['engineer']}, техника {roles_a['vehicle']}, штурм {roles_a['infantry']}, саппорт {roles_a['support']}")
    print(f"   Команда B: инженеры {roles_b['engineer']}, техника {roles_b['vehicle']}, штурм {roles_b['infantry']}, саппорт {roles_b['support']}")

    # ------------------------------------------------------------
    # FLAGS
    # ------------------------------------------------------------
    print("\n🏴‍☠️ КОМАНДНЫЕ ФЛАГИ:")
    if strong_a: print(f"   ⭐ A сильная: {', '.join(strong_reasons_a)}")
    if strong_b: print(f"   ⭐ B сильная: {', '.join(strong_reasons_b)}")
    if weak_a:   print(f"   👶 A слабая: {', '.join(weak_reasons_a)}")
    if weak_b:   print(f"   👶 B слабая: {', '.join(weak_reasons_b)}")
    if bot_a:    print(f"   🥒 A ботокатка: {', '.join(bot_reasons_a)}")
    if bot_b:    print(f"   🥒 B ботокатка: {', '.join(bot_reasons_b)}")

    # ------------------------------------------------------------
    # STRUCTURED OUTPUT
    # ------------------------------------------------------------
    print("\n📌 СТРУКТУРНЫЙ ВЫВОД:")
    recs = []

    if avg_a['vehicles'] > avg_b['vehicles']:
        recs.append("Команда A сильнее в технике → давить бронёй.")
    elif avg_b['vehicles'] > avg_a['vehicles']:
        recs.append("Команда B сильнее в технике → давить бронёй.")

    if avg_a['built'] > avg_b['built']:
        recs.append("Команда A лучше строит → уничтожать точки сбора.")
    elif avg_b['built'] > avg_a['built']:
        recs.append("Команда B лучше строит → уничтожать точки сбора.")

    if avg_a['captures'] > avg_b['captures']:
        recs.append("Команда A сильнее в захватах → играть на удержание.")
    elif avg_b['captures'] > avg_a['captures']:
        recs.append("Команда B сильнее в захватах → играть на удержание.")

    if abs(elo_diff) > 200:
        if elo_diff > 0:
            recs.append(f"Команда A значительно выше по суммарному ELO (+{elo_diff:.0f}) → играйте осторожнее.")
        else:
            recs.append(f"Команда B значительно выше по суммарному ELO ({elo_diff:+.0f}) → играйте осторожнее.")

    if zadrots_a:
        recs.append("В команде A есть задроты → избегать дуэлей.")
    if zadrots_b:
        recs.append("В команде B есть задроты → избегать дуэлей.")

    for r in recs:
        print("   • " + r)

    # ------------------------------------------------------------
    # VERDICT
    # ------------------------------------------------------------
    a_wins = sum(1 for k, _ in COMPARE_METRICS if avg_a[k] > avg_b[k] + 0.01)
    b_wins = sum(1 for k, _ in COMPARE_METRICS if avg_b[k] > avg_a[k] + 0.01)

    if a_wins > b_wins:
        grade = get_strength_grade(a_wins, len(COMPARE_METRICS))
        print(f"\n📌 ОБЩИЙ ВЕРДИКТ: 🟢 Команда A {grade} сильнее.")
    elif b_wins > a_wins:
        grade = get_strength_grade(b_wins, len(COMPARE_METRICS))
        print(f"\n📌 ОБЩИЙ ВЕРДИКТ: 🔴 Команда B {grade} сильнее.")
    else:
        print("\n📌 ОБЩИЙ ВЕРДИКТ: 🟡 Команды равны.")

    # ------------------------------------------------------------
    # SUPER VERDICT
    # ------------------------------------------------------------
    print("\n📌 СУПЕР‑ВЕРДИКТ:")
    if strong_a: print(f"   ⭐ A сильная — {', '.join(strong_reasons_a)}")
    if strong_b: print(f"   ⭐ B сильная — {', '.join(strong_reasons_b)}")
    if weak_a:   print(f"   👶 A слабая — {', '.join(weak_reasons_a)}")
    if weak_b:   print(f"   👶 B слабая — {', '.join(weak_reasons_b)}")
    if bot_a:    print(f"   🥒 A ботокатка — {', '.join(bot_reasons_a)}")
    if bot_b:    print(f"   🥒 B ботокатка — {', '.join(bot_reasons_b)}")
    if zadrots_a: print(f"   💀 Задроты A: {', '.join(p['name'] for p in zadrots_a)}")
    if zadrots_b: print(f"   💀 Задроты B: {', '.join(p['name'] for p in zadrots_b)}")
    if smurfs_a: print(f"   🧙 Смурфы A: {', '.join(p['name'] for p in smurfs_a)}")
    if smurfs_b: print(f"   🧙 Смурфы B: {', '.join(p['name'] for p in smurfs_b)}")
    if bots_a:   print(f"   🤖 Боты A: {', '.join(p['name'] for p in bots_a)}")
    if bots_b:   print(f"   🤖 Боты B: {', '.join(p['name'] for p in bots_b)}")

    # ------------------------------------------------------------
    # FINAL SCORE
    # ИЗМЕНЕНО: расширенный вывод расчёта (если DEBUG=True)
    # ------------------------------------------------------------
    def score(avg, sum_elo, team_size, roles, bonus, team, team_label="A"):
        total = 0.0

        if DEBUG:
            print(f"\n{'='*60}")
            print(f"🔍 РАСЧЁТ SCORE КОМАНДЫ {team_label}")
            print(f"{'='*60}")
            print(f"Размер команды: {team_size}")

        # Метрики (кроме ELO)
        if DEBUG: print(f"\n📊 МЕТРИКИ (кроме ELO):")
        if DEBUG: print(f"  {'метрика':<12} {'знач.':>10} {'норм.':>8} {'вес':>6} {'вклад':>8}")
        if DEBUG: print(f"  {'-'*12} {'-'*10} {'-'*8} {'-'*6} {'-'*8}")

        for k, w in FINAL_WEIGHTS.items():
            if k == 'elo':
                continue
            norm_val = normalize(k, avg[k])
            contrib = norm_val * w
            total += contrib
            if DEBUG:
                print(f"  {k:<12} {avg[k]:>10.2f} {norm_val:>8.3f} {w:>6.2f} {contrib:>8.3f}")

        if DEBUG: print(f"  {'-'*12} {'-'*10} {'-'*8} {'-'*6} {'-'*8}")
        if DEBUG: print(f"  {'Итого метрик':<12} {'':>10} {'':>8} {'':>6} {total:>8.3f}")

        # ELO
        # ELO — суммарный
        elo_norm = normalize('elo', sum_elo, team_size, is_sum_elo=True)
        elo_contrib = elo_norm * FINAL_WEIGHTS['elo']
        total += elo_contrib

        # ELO — средний (с тем же весом)
        avg_elo_val = sum_elo / team_size if team_size > 0 else 0
        avg_elo_norm = normalize('elo', avg_elo_val)
        avg_elo_contrib = avg_elo_norm * FINAL_WEIGHTS['elo']
        total += avg_elo_contrib

        if DEBUG:
            print(f"\n🎯 ELO (суммарный):")
            print(f"  Сумма ELO: {sum_elo:.0f}")
            print(f"  Диапазон: [{200*team_size} .. {2600*team_size}]")
            print(f"  Норм: {elo_norm:.3f}")
            print(f"  Вес: {FINAL_WEIGHTS['elo']}")
            print(f"  Вклад: {elo_contrib:+.3f}")

            print(f"\n🎯 ELO (средний):")
            print(f"  Средний ELO: {avg_elo_val:.0f}")
            print(f"  Диапазон: [200 .. 2600]")
            print(f"  Норм: {avg_elo_norm:.3f}")
            print(f"  Вес: {FINAL_WEIGHTS['elo']}")
            print(f"  Вклад: {avg_elo_contrib:+.3f}")

        # Роли
        if DEBUG: print(f"\n🎭 РОЛИ:")
        role_total = 0.0
        for role_key, cnt in roles.items():
            b = ROLE_BONUS.get(role_key, 0) * cnt
            role_total += b
            if DEBUG and cnt > 0:
                print(f"  {role_key:<10} × {cnt} × {ROLE_BONUS.get(role_key, 0)} = {b:+.3f}")
        total += role_total
        if DEBUG: print(f"  Итого ролей: {role_total:+.3f}")

        # Задроты/элиты
        if DEBUG:
            print(f"\n💀 ЗАДРОТЫ/ЭЛИТЫ:")
            print(f"  Бонус: {bonus:+.3f}")
        total += bonus

        # Топ-3
        top3_kd = top3_avg(team, 'kd')
        top3_elo = top3_avg(team, 'elo')
        top3_kd_norm = normalize('kd', top3_kd)
        top3_elo_norm = normalize('elo', top3_elo)
        top3_kd_contrib = top3_kd_norm * 0.9
        top3_elo_contrib = top3_elo_norm * 0.9
        total += top3_kd_contrib + top3_elo_contrib
        if DEBUG:
            print(f"\n⭐ ТОП-3:")
            print(f"  KD топ-3: {top3_kd:.2f} → норм {top3_kd_norm:.3f} × 0.9 = {top3_kd_contrib:+.3f}")
            print(f"  ELO топ-3: {top3_elo:.0f} → норм {top3_elo_norm:.3f} × 0.9 = {top3_elo_contrib:+.3f}")

        if DEBUG:
            print(f"\n{'='*60}")
            print(f"🎯 ИТОГОВЫЙ SCORE КОМАНДЫ {team_label}: {total:.3f}")
            print(f"{'='*60}")

        return total

    score_a = score(avg_a, sum_elo_a, len(team_a), roles_a, bonus_a, team_a, "A")
    score_b = score(avg_b, sum_elo_b, len(team_b), roles_b, bonus_b, team_b, "B")

    if score_a > score_b:
        diff = ((score_a - score_b) / score_b) * 100 if score_b != 0 else 100
        print(f"\n ФИНАЛЬНАЯ ОЦЕНКА:  Команда A сильнее на {diff:.1f}%")
    elif score_b > score_a:
        diff = ((score_b - score_a) / score_a) * 100 if score_a != 0 else 100
        print(f"\n ФИНАЛЬНАЯ ОЦЕНКА:  Команда B сильнее на {diff:.1f}%")
    else:
        print("\n ФИНАЛЬНАЯ ОЦЕНКА:  Команды равны (0%)")

    if DEBUG:
        print(f"\n📊 СВОДКА:")
        print(f"  Score A = {score_a:.3f}")
        print(f"  Score B = {score_b:.3f}")
        print(f"  Разница = {score_a - score_b:+.3f}")

    print("=" * 80)