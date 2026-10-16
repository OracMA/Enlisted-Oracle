from wcwidth import wcswidth
import traceback
from datetime import datetime
from fuzzy_search import search_nick

def log_error(message):
    try:
        with open("crash_log.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
            f.write(traceback.format_exc())
            f.write("-" * 80 + "\n")
    except Exception:
        print(f"⚠️ Ошибка логирования: {message}")
        traceback.print_exc()


# ---------------------------------------------------------
# ЦВЕТОВАЯ ЛЕГЕНДА
# ---------------------------------------------------------
def print_color_legend():
    """Выводит краткую легенду цветов."""
    print("\n📌 Цвета: 🟢🐑 слабый | 🟡🥚 ниже среднего | 🟠⚔️ средний | 🔴💀 сильный | 🟣👑 элита")


# ---------------------------------------------------------
# РЕНДЕРЕР ТАБЛИЦ
# ---------------------------------------------------------
def render_table(headers, rows):
    if not headers or not rows:
        return

    col_widths = []
    for col in range(len(headers)):
        max_width = wcswidth(str(headers[col]))
        for row in rows:
            if col < len(row):
                max_width = max(max_width, wcswidth(str(row[col])))
        col_widths.append(max_width)

    def fmt_row(row):
        parts = []
        for i, cell in enumerate(row[:len(headers)]):
            cell_str = str(cell)
            pad = col_widths[i] - wcswidth(cell_str)
            parts.append(cell_str + " " * pad)
        for i in range(len(row), len(headers)):
            parts.append(" " * col_widths[i])
        return "  ".join(parts).rstrip()

    total_width = sum(col_widths) + 2 * (len(col_widths) - 1)
    print("=" * total_width)
    print(fmt_row(headers))
    print("-" * total_width)
    for row in rows:
        print(fmt_row(row))
    print("=" * total_width)


# ---------------------------------------------------------
# ОБЁРТКИ
# ---------------------------------------------------------
def print_found_players_table(sorted_matches, limits, get_color_icon, safe_float, safe_int, safe_elo, max_players):
    try:
        headers = [
            "Ник🐑🟢🟡🟠🔴🟣👑",
            "Матчи",
            "Хедшоты",
            "Захваты",
            "БТР",
            "K/D",
            "WR",
            "ELO",
            "Техника",
            "Построек",
            "Статус"
        ]
        rows = []
        for nick, (score, data) in sorted_matches[:max_players]:
            kd = safe_float(data.get('kd', 0))
            wr = safe_float(data.get('win_percent', 0))
            elo = safe_elo(data.get('elo', 0))
            vehicles = safe_int(data.get('vehicles', 0))
            built = safe_int(data.get('built', 0))
            matches = safe_int(data.get('matches', 0))
            headshots = safe_int(data.get('headshots', 0))
            captures = safe_int(data.get('captures', 0))
            apc = safe_int(data.get('apc_spawns', 0))

            color_kd, icon_kd = get_color_icon(kd, 'kd', limits)
            color_wr, icon_wr = get_color_icon(wr, 'wr', limits)
            color_elo, icon_elo = get_color_icon(elo, 'elo', limits)
            color_hs, icon_hs = get_color_icon(headshots, 'hs', limits)
            color_cap, icon_cap = get_color_icon(captures, 'cap', limits)
            color_veh, icon_veh = get_color_icon(vehicles, 'veh', limits)
            color_built, icon_built = get_color_icon(built, 'built', limits)
            color_apc, icon_apc = get_color_icon(apc, 'apc', limits)

            rows.append([
                nick,
                matches,
                f"{color_hs}{icon_hs}{headshots}",
                f"{color_cap}{icon_cap}{captures}",
                f"{color_apc}{icon_apc}{apc}",
                f"{color_kd}{icon_kd}{kd:.2f}",
                f"{color_wr}{icon_wr}{wr:.1f}%",
                f"{color_elo}{icon_elo}{elo:.0f}",
                f"{color_veh}{icon_veh}{vehicles}",
                f"{color_built}{icon_built}{built}",
                f"{score:.1f}%"   # <-- ИСПРАВЛЕНО: один знак после запятой
            ])

        print(f"\n✅ Найдено {len(sorted_matches)} игроков (показаны первые {max_players}):")
        print_color_legend()
        render_table(headers, rows)

    except Exception as e:
        log_error(f"Ошибка в print_found_players_table: {e}")
        raise


def print_manual_players_table(raw_inputs, players, nicknames, limits,
                               normalize_ocr_word, process, fuzz,
                               get_color_icon, safe_float, safe_int, safe_elo):
    try:
        headers = [
            "Ник🐑🟢🟡🟠🔴🟣👑",
            "Матчи",
            "Хедшоты",
            "Захваты",
            "БТР",
            "K/D",
            "WR",
            "ELO",
            "Техника",
            "Построек",
            "Статус"
        ]
        rows = []
        found_players = []

        nick_to_norm = {n: normalize_ocr_word(n) for n in nicknames}
        norm_to_nick = {norm: name for name, norm in nick_to_norm.items()}

        for raw_nick in raw_inputs:
            norm_raw = normalize_ocr_word(raw_nick)

            if norm_raw in norm_to_nick:
                original_name = norm_to_nick[norm_raw]
                player = players[original_name]
                status = "✅ Точно"
            else:
                matched_norm, score = search_nick(norm_raw, list(norm_to_nick.keys()), threshold=70)
                if matched_norm and matched_norm in norm_to_nick:
                    original_name = norm_to_nick[matched_norm]
                    player = players[original_name]
                    status = f"* {score:.1f}%"   # <-- ИСПРАВЛЕНО: один знак после запятой
                else:
                    player = None
                    status = "❌ Не найден"

            if player and status != "❌ Не найден":
                found_players.append(player)

                kd = safe_float(player.get('kd', 0))
                wr = safe_float(player.get('win_percent', 0))
                elo = safe_elo(player.get('elo', 0))
                vehicles = safe_int(player.get('vehicles', 0))
                built = safe_int(player.get('built', 0))
                matches = safe_int(player.get('matches', 0))
                headshots = safe_int(player.get('headshots', 0))
                captures = safe_int(player.get('captures', 0))
                apc = safe_int(player.get('apc_spawns', 0))
                nick = player.get('name', '')

                color_kd, icon_kd = get_color_icon(kd, 'kd', limits)
                color_wr, icon_wr = get_color_icon(wr, 'wr', limits)
                color_elo, icon_elo = get_color_icon(elo, 'elo', limits)
                color_hs, icon_hs = get_color_icon(headshots, 'hs', limits)
                color_cap, icon_cap = get_color_icon(captures, 'cap', limits)
                color_veh, icon_veh = get_color_icon(vehicles, 'veh', limits)
                color_built, icon_built = get_color_icon(built, 'built', limits)
                color_apc, icon_apc = get_color_icon(apc, 'apc', limits)

                display_nick = f"{nick}*" if status.startswith("*") else nick

                rows.append([
                    display_nick,
                    matches,
                    f"{color_hs}{icon_hs}{headshots}",
                    f"{color_cap}{icon_cap}{captures}",
                    f"{color_apc}{icon_apc}{apc}",
                    f"{color_kd}{icon_kd}{kd:.2f}",
                    f"{color_wr}{icon_wr}{wr:.1f}%",
                    f"{color_elo}{icon_elo}{elo:.0f}",
                    f"{color_veh}{icon_veh}{vehicles}",
                    f"{color_built}{icon_built}{built}",
                    status
                ])
            else:
                rows.append([
                    raw_nick,
                    "—", "—", "—", "—",
                    "—", "—", "—", "—",
                    "—", "—",
                    "❌ Не найден"
                ])

        print_color_legend()
        render_table(headers, rows)
        return found_players

    except Exception as e:
        log_error(f"Ошибка в print_manual_players_table: {e}")
        raise