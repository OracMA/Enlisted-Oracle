# lang.py — полный словарь локализации для Enlisted Oracle
# Все ключи внутри LANG_RU и LANG_EN. Никаких дубликатов и «висячих» строк.

LANG_RU = {
    # --- Кнопки ---
    "btn_scan":         "📸 Сканировать",
    "btn_manual":       "✏️ Ручной ввод",
    "btn_compare":      "⚖️ Сравнить",
    "btn_clear":        "🧹 Очистить команды",
    "btn_log_show":     "📋 Показать лог",
    "btn_log_hide":     "✖ Скрыть лог",
    "btn_sound_on":     "🔊",
    "btn_sound_off":    "🔇",
    "btn_copy":         "📋 Скопировать в буфер",
    "btn_copy_done":    "✅ Готово",
    "btn_copy_reset":   "📋 Скопировать в буфер",
    "btn_copy_hint":    "✅ Скопировано в буфер",
    "btn_copy_tooltip": "Скопировать скриншот для вставки в Discord",

    # --- Заголовки команд ---
    "team_a": "Команда A",
    "team_b": "Команда B",

    # --- Заголовки таблицы сравнения ---
    "compare_title": "📊 Сравнение команд",
    "cmp_param":     "Параметр",
    "cmp_team_a":    "Ком. A",
    "cmp_team_b":    "Ком. B",
    "cmp_diff":      "Разница",
    "cmp_stronger":  "Сильнее",

    # --- Столбцы PlayersTable ---
    "col_nick":      "Ник",
    "col_matches":   "Матчи",
    "col_headshots": "Хедшоты",
    "col_captures":  "Захваты",
    "col_apc":       "БТР",
    "col_kd":        "K/D",
    "col_wr":        "WR",
    "col_elo":       "ELO",
    "col_veh":       "Техника",
    "col_built":     "Построек",

    # --- Подсказка цветов ---
    "color_hint": (
        "📌 Цвета: "
        "<span style='color:#44ff44;'>🟢 слабый</span> | "
        "<span style='color:#ffd60a;'>🟡 ниже среднего</span> | "
        "<span style='color:#ff9f1c;'>🔶⚔️ средний</span> | "
        "<span style='color:#ff4444;'>🟥💀 сильный</span> | "
        "<span style='color:#c77dff;'>🟣👑 элита</span>"
    ),

    # --- Инфо-строка ---
    "teams_in_buffer_0": "Команд в буфере: 0",
    "teams_in_buffer_1": "Команда 1 (заполнена) | Команда 2 (пусто)",
    "teams_in_buffer_2": "Команда 1 (заполнена) | Команда 2 (заполнена)",
    "status_ready":      "Готово",

    # --- Статусы ---
    "status_scan":              "Распознавание",
    "status_compare":           "Сравнение",
    "status_team_added":        "Команда {0} добавлена",
    "status_no_image":          "Нет изображения",
    "status_cancelled":         "Отменено",
    "status_error":             "Ошибка",
    "status_compare_done":      "Сравнение завершено",
    "status_copy_ready":        "✅ Скриншот в буфере",
    "status_no_copy_data":      "Нет данных для копирования",
    "status_not_enough_teams":  "Недостаточно команд",

    # --- Лог ---
    "log_welcome":         "Добро пожаловать в Enlisted Oracle.",
    "log_scan_start":      "📸 Копируйте скриншот в буфер...",
    "log_ocr":             "🔍 OCR через Oracle...",
    "log_no_image":        "❌ В буфере нет изображения.",
    "log_nothing_found":   "⚠️ Ничего не найдено.",
    "log_found_players":   "✅ Найдено {0} игроков.",
    "log_compare":         "⚖️ Сравнение команд...",
    "log_compare_done":    "✅ Сравнение выведено в таблицу ниже.",
    "log_compare_error":   "❌ Ошибка сравнения: {0}",
    "log_buffer_cleared":  "🧹 Буфер команд очищен.",
    "log_sound_on":        "🔊 Звук включён.",
    "log_sound_off":       "🔇 Звук выключен.",
    "log_copy_done":       "📋 Скриншот скопирован — вставь в Discord (Ctrl+V)!",
    "log_copy_error":      "❌ Ошибка: {0}",
    "log_no_copy_data":    "⚠️ Сначала сделайте сравнение команд.",
    "log_need_two_teams":  "⚠️ Нужно минимум две команды.",
    "log_manual_cancel":   "❌ Ручной ввод отменён или не найдено игроков.",
    "log_manual_error":    "❌ Ошибка ручного ввода: {0}",
    "log_manual_added":    "✅ Команда {0} добавлена (ручной ввод).",
    "copy_hint_error":     "❌ Ошибка",

    # --- Диалог лога ---
    "dlg_log_title": "Подтверждение",
    "dlg_log_text":  "Дальше бога нет.",
    "dlg_yes":       "Да",
    "dlg_no":        "Нет",
    "dlg_close":     "Закрыть",

     # --- Диалог доната ---
    "dlg_donation_title":      "заглушка",
    "dlg_donation_header":     "заглушка",
    "dlg_donation_text":       "заглушка",
    "dlg_donation_requisites": "заглушка",
    "dlg_donation_card":       "заглушка",
    "dlg_donation_boosty":     "заглушка",
    "dlg_donation_tg":         "заглушка",

    # --- Диалог ручного ввода ---
    "manual_title":       "Ручной ввод ников",
    "manual_placeholder": "Введите ник и нажмите Добавить",
    "manual_add":         "Добавить",
    "manual_remove":      "Удалить выбранное",
    "manual_done":        "Готово",

 # --- Финальный вердикт (для UI-таблицы) ---
      "final_verdict_a":     "ФИНАЛЬНАЯ ОЦЕНКА:  Команда A сильнее на {0}%",
    "final_verdict_b":     "ФИНАЛЬНАЯ ОЦЕНКА:  Команда B сильнее на {0}%",
    "final_verdict_equal": "ФИНАЛЬНАЯ ОЦЕНКА:  Команды равны (0%)",

    "radar_kd":    "K/D",
    "radar_wr":    "WR",
    "radar_elo":   "ELO",
    "radar_cap":   "ЗАХВ",
    "radar_hs":    "ХЕДШ",
    "radar_built": "ПОСТР",
    "radar_apc":   "БТР",
    "cmp_equal": "Равно",

}


LANG_EN = {
    # --- Buttons ---
    "btn_scan":         "📸 Scan",
    "btn_manual":       "✏️ Manual Input",
    "btn_compare":      "⚖️ Compare",
    "btn_clear":        "🧹 Clear Teams",
    "btn_log_show":     "📋 Show Log",
    "btn_log_hide":     "✖ Hide Log",
    "btn_sound_on":     "🔊",
    "btn_sound_off":    "🔇",
    "btn_copy":         "📋 Copy to Clipboard",
    "btn_copy_done":    "✅ Done",
    "btn_copy_reset":   "📋 Copy to Clipboard",
    "btn_copy_hint":    "✅ Copied to clipboard",
    "btn_copy_tooltip": "Copy screenshot for Discord",

    # --- Team headers ---
    "team_a": "Team A",
    "team_b": "Team B",

    # --- Comparison table headers ---
    "compare_title": "📊 Team Comparison",
    "cmp_param":     "Parameter",
    "cmp_team_a":    "Team A",
    "cmp_team_b":    "Team B",
    "cmp_diff":      "Diff",
    "cmp_stronger":  "Stronger",

    # --- PlayersTable columns ---
    "col_nick":      "Nick",
    "col_matches":   "Matches",
    "col_headshots": "Headshots",
    "col_captures":  "Captures",
    "col_apc":       "APC",
    "col_kd":        "K/D",
    "col_wr":        "WR",
    "col_elo":       "ELO",
    "col_veh":       "Vehicles",
    "col_built":     "Built",

    # --- Color legend ---
    "color_hint": (
        "📌 Colors: "
        "<span style='color:#44ff44;'>🟢 weak</span> | "
        "<span style='color:#ffd60a;'>🟡 below average</span> | "
        "<span style='color:#ff9f1c;'>🔶⚔️ average</span> | "
        "<span style='color:#ff4444;'>🟥💀 strong</span> | "
        "<span style='color:#c77dff;'>🟣👑 elite</span>"
    ),

    # --- Info line ---
    "teams_in_buffer_0": "Teams in buffer: 0",
    "teams_in_buffer_1": "Team 1 (filled) | Team 2 (empty)",
    "teams_in_buffer_2": "Team 1 (filled) | Team 2 (filled)",
    "status_ready":      "Ready",

    # --- Statuses ---
    "status_scan":              "Scanning",
    "status_compare":           "Comparing",
    "status_team_added":        "Team {0} added",
    "status_no_image":          "No image",
    "status_cancelled":         "Cancelled",
    "status_error":             "Error",
    "status_compare_done":      "Comparison finished",
    "status_copy_ready":        "✅ Screenshot copied",
    "status_no_copy_data":      "No data to copy",
    "status_not_enough_teams":  "Not enough teams",

    # --- Log ---
    "log_welcome":         "Welcome to Enlisted Oracle.",
    "log_scan_start":      "📸 Copy screenshot to clipboard...",
    "log_ocr":             "🔍 OCR via Oracle...",
    "log_no_image":        "❌ No image in clipboard.",
    "log_nothing_found":   "⚠️ Nothing found.",
    "log_found_players":   "✅ Found {0} players.",
    "log_compare":         "⚖️ Comparing teams...",
    "log_compare_done":    "✅ Comparison displayed below.",
    "log_compare_error":   "❌ Comparison error: {0}",
    "log_buffer_cleared":  "🧹 Team buffer cleared.",
    "log_sound_on":        "🔊 Sound enabled.",
    "log_sound_off":       "🔇 Sound disabled.",
    "log_copy_done":       "📋 Screenshot copied — paste into Discord (Ctrl+V)!",
    "log_copy_error":      "❌ Error: {0}",
    "log_no_copy_data":    "⚠️ Make a comparison first.",
    "log_need_two_teams":  "⚠️ Need at least two teams.",
    "log_manual_cancel":   "❌ Manual input cancelled or no players found.",
    "log_manual_error":    "❌ Manual input error: {0}",
    "log_manual_added":    "✅ Team {0} added (manual input).",
    "copy_hint_error":     "❌ Error",

    # --- Log dialog ---
    "dlg_log_title": "Confirmation",
    "dlg_log_text":  "There is no god beyond this point.",
    "dlg_yes":       "Yes",
    "dlg_no":        "No",
    "dlg_close":     "Close",

        # --- Donation dialog ---
    "dlg_donation_title":      "placeholder",
    "dlg_donation_header":     "placeholder",
    "dlg_donation_text":       "placeholder",
    "dlg_donation_requisites": "placeholder",
    "dlg_donation_card":       "placeholder",
    "dlg_donation_boosty":     "placeholder",
    "dlg_donation_tg":         "placeholder",
    
    # --- Manual input dialog ---
    "manual_title":       "Manual Nickname Input",
    "manual_placeholder": "Enter nickname and press Add",
    "manual_add":         "Add",
    "manual_remove":      "Remove selected",
    "manual_done":        "Done",

 # --- Final verdict (for UI table) ---
   "final_verdict_a":     "FINAL SCORE:  Team A is stronger by {0}%",
  "final_verdict_b":     "FINAL SCORE:  Team B is stronger by {0}%",
   "final_verdict_equal": "FINAL SCORE:  Teams are equal (0%)",
  #   радарп 

    "radar_kd":    "K/D",
    "radar_wr":    "WR",
    "radar_elo":   "ELO",
    "radar_cap":   "CAP",
    "radar_hs":    "HS",
    "radar_built": "BLD",
    "radar_apc":   "APC",
    "cmp_equal": "Equal",
    }   