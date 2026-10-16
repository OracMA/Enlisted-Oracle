from main import get_app_dir
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtMultimedia import QSoundEffect
import sys
import io
import os
import base64
import threading
import time
import random
import json
from radar_widget import (
    TeamRadarWidget, calc_metric_percent,
    value_to_rank, rank_to_color,
)
from contextlib import redirect_stdout
from PIL import ImageGrab

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QDialog, QLineEdit, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
)
from PyQt6.QtGui import QColor, QPalette, QIcon, QPixmap

from icon_data import ICON_B64

# --- локализация ---
from lang import LANG_RU, LANG_EN


# --- backend ---
from main import (
    load_players_dict, load_limits, DEFAULT_LIMITS,
    get_ocr_texts_lens, find_matches,
    analyze_team, compare_two_teams,
    team_buffer, MAX_PLAYERS, CSV_FILE,
    normalize_ocr_word, process, fuzz,
    safe_float, safe_int, safe_elo,
    get_color_icon, 
    get_resource_path   # ← ДОБАВИТЬ
)
from output import print_manual_players_table


def make_icon():
    """Возвращает QIcon, собранный из base64-строки в icon_data.py."""
    data = base64.b64decode(ICON_B64)
    pix = QPixmap()
    if not pix.loadFromData(data, "ICO"):
        print("⚠️ Failed to load ICON_B64")
    return QIcon(pix)


# ---------- ЦВЕТНЫЕ КВАДРАТЫ (глобальная функция, для совместимости) ----------
def colored_square(value, metric, limits=None):
    """
    Возвращает эмодзи-квадрат по значению и метрике.
    Если limits передан — используются пороги оттуда.
    Если нет — fallback на старый хардкод (но лучше всегда передавать limits).
    """
    if limits and metric in limits:
        l = limits[metric]
        if value >= l['purple']: return "🟣"
        if value >= l['red']:    return "🔴"   # было "🔻" — теперь красный квадрат
        if value >= l['orange']: return "🔶"
        if value >= l['yellow']: return "🟡"
        return "🟢"

    # Fallback (если лимиты не переданы) — старые значения
    if metric == "kd":
        if value >= 2.2:  return "🟣"
        if value >= 1.6:  return "🔴"
        if value >= 1.1:  return "🔶"
        if value >= 0.7:  return "🟡"
        return "🟢"
    if metric == "wr":
        if value >= 72:   return "🟣"
        if value >= 60:   return "🔴"
        if value >= 50:   return "🔶"
        if value >= 42:   return "🟡"
        return "🟢"
    if metric == "elo":
        if value >= 1672: return "🟣"
        if value >= 1316: return "🔴"
        if value >= 944:  return "🔶"
        if value >= 713:  return "🟡"
        return "🟢"
    if metric == "hs":
        if value >= 400:  return "🟣"
        if value >= 200:  return "🔴"
        if value >= 100:  return "🔶"
        if value >= 30:   return "🟡"
        return "🟢"
    if metric == "cap":
        if value >= 25:   return "🟣"
        if value >= 12:   return "🔴"
        if value >= 5:    return "🔶"
        if value >= 1:    return "🟡"
        return "🟢"
    if metric == "apc":
        if value >= 60:   return "🟣"
        if value >= 25:   return "🔴"
        if value >= 8:    return "🔶"
        if value >= 2:    return "🟡"
        return "🟢"
    if metric == "veh":
        if value >= 250:  return "🟣"
        if value >= 100:  return "🔴"
        if value >= 40:   return "🔶"
        if value >= 10:   return "🟡"
        return "🟢"
    if metric == "built":
        if value >= 150:  return "🟣"
        if value >= 60:   return "🔴"
        if value >= 20:   return "🔶"
        if value >= 5:    return "🟡"
        return "🟢"
    return "⬛"


# Длина ника в таблице (можешь менять)
NICK_MAX_LEN = 8

# Сколько строк показывать без скролла
ROWS_VISIBLE = 11
ROW_HEIGHT = 22
HEADER_HEIGHT = 25


class PlayersTable(QTableWidget):
    def __init__(self, limits, header_color="#e0e0e0", parent=None):
        super().__init__(parent)
        self.limits = limits
        self.header_color = header_color

        # --- Столбцы (без "Ранг" и "Статус") ---
        self.setColumnCount(10)
        self.setHorizontalHeaderLabels([
            LANG["col_nick"],
            LANG["col_matches"],
            LANG["col_headshots"],
            LANG["col_captures"],
            LANG["col_apc"],
            LANG["col_kd"],
            LANG["col_wr"],
            LANG["col_elo"],
            LANG["col_veh"],
            LANG["col_built"],
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)   # Ник — единственная растягиваемая
        # Колонки 1-9 — по содержимому, не растягиваются
        header.setStretchLastSection(False)

        # --- Компактные строки ---
        vh = self.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(ROW_HEIGHT)
        vh.setMinimumSectionSize(18)
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        # --- Поведение ---
        self.setWordWrap(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)

        # --- Стили ---
        self.setStyleSheet(f"""
            QTableWidget {{ gridline-color: #3a3a3a; font-size: 12px; }}
            QTableWidget::item {{ padding: 0px; margin: 0px; }}
            QHeaderView::section {{
                background-color: {self.header_color};
                color: #ffffff;
                padding: 2px 4px;
                min-height: 20px;
                font-weight: bold;
                border: 1px solid #1e1e1e;
            }}
        """)

        # --- Фиксированная высота: ровно ROWS_VISIBLE строк ---
        fixed_h = ROWS_VISIBLE * ROW_HEIGHT + HEADER_HEIGHT + 5
        self.setMinimumHeight(fixed_h)
        self.setMaximumHeight(fixed_h)

    def clear_table(self):
        self.setRowCount(0)

    def colored_square(self, value, metric):
        limits = self.limits.get(metric)
        if not limits:
            return "⬛"
        if value >= limits['purple']:
            return "🟣"
        elif value >= limits['red']:
            return "🟥"
        elif value >= limits['orange']:
            return "🔶"
        elif value >= limits['yellow']:
            return "🟡"
        else:
            return "🟢"

    def elo_color(self, elo):
        """Cyberpunk-палитра: тёмная подложка + цветной текст по категориям."""
        limits = self.limits['elo']
        BG = (43, 43, 43)
        K = 0.20   # фон почти невидимый

        def mix(rgb):
            r = int(rgb[0] * K + BG[0] * (1 - K))
            g = int(rgb[1] * K + BG[1] * (1 - K))
            b = int(rgb[2] * K + BG[2] * (1 - K))
            return QColor(r, g, b)

        if elo >= limits['purple']:
            # элита — бирюзовый текст
            return mix((100, 20, 180)), QColor("#00e5ff")
        elif elo >= limits['red']:
            # сильные — красный текст
            return mix((200, 20, 60)), QColor("#ff3060")
        elif elo >= limits['orange']:
            # средние — оранжевый текст
            return mix((200, 100, 20)), QColor("#ffb020")
        else:
            # слабые (жёлтые + зелёные) — белый текст
            return mix((20, 100, 60)), QColor("#ffffff")

    def kd_color(self, kd):
        """Возвращает QColor для K/D по тем же порогам, что и colored_square."""
        limits = self.limits.get('kd')
        if not limits:
            return QColor("#e0e0e0")
        if kd >= limits['purple']:
            return QColor("#c77dff")   # фиолетовый — элита
        elif kd >= limits['red']:
            return QColor("#ff4444")   # красный — сильный
        elif kd >= limits['orange']:
            return QColor("#ff9f1c")   # оранжевый — средний
        elif kd >= limits['yellow']:
            return QColor("#ffd60a")   # жёлтый — ниже среднего
        else:
            return QColor("#44ff44")   # зелёный — слабый

    def add_player(self, nick, data, score):
        row = self.rowCount()
        self.insertRow(row)

        kd = safe_float(data.get('kd', 0))
        wr = safe_float(data.get('win_percent', 0))
        elo = safe_elo(data.get('elo', 0))
        vehicles = safe_int(data.get('vehicles', 0))
        built = safe_int(data.get('built', 0))
        matches = safe_int(data.get('matches', 0))
        headshots = safe_int(data.get('headshots', 0))
        captures = safe_int(data.get('captures', 0))
        apc = safe_int(data.get('apc_spawns', 0))

        short_nick = nick[:NICK_MAX_LEN] if len(nick) > NICK_MAX_LEN else nick

        items = [
            (short_nick, None),
            (str(matches), None),
            (f"{self.colored_square(headshots, 'hs')} {headshots}", None),
            (f"{self.colored_square(captures, 'cap')} {captures}", None),
            (f"{self.colored_square(apc, 'apc')} {apc}", None),
            (f"{self.colored_square(kd, 'kd')} {kd:.2f}", None),
            (f"{self.colored_square(wr, 'wr')} {wr:.1f}%", None),
            (f"{self.colored_square(elo, 'elo')} {elo:.0f}", None),
            (f"{self.colored_square(vehicles, 'veh')} {vehicles}", None),
            (f"{self.colored_square(built, 'built')} {built}", None),
        ]

        # Цвета для ячейки ELO (плашка)
        elo_bg, elo_fg = self.elo_color(elo)

        for col, (text, _) in enumerate(items):
            item = QTableWidgetItem(text)

            # Ник (0) и Матчи (1) — по центру
            # Колонки с эмодзи+цифрами (2-9) — по левому краю, чтобы эмодзи не «плавал»
            if col in (0, 1):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

            # K/D — красим цифры в цвет ранга K/D (колонка 5)
            if col == 5:
                item.setForeground(self.kd_color(kd))

            # ELO — фон-плашка (колонка 7)
            elif col == 7:
                item.setBackground(elo_bg)
                item.setForeground(elo_fg)

            # Полный ник в подсказке, если обрезан
            if col == 0 and len(nick) > NICK_MAX_LEN:
                item.setToolTip(nick)

            self.setItem(row, col, item)

    def add_team(self, team, separator=True):
        if self.rowCount() > 0 and separator:
            row = self.rowCount()
            self.insertRow(row)
            sep_item = QTableWidgetItem("———")
            sep_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 0, sep_item)
        for nick, data, score in team:
            self.add_player(nick, data, score)
# ---------- ОБРЕЗКА ТЕКСТА СРАВНЕНИЯ ----------
def trim_compare_text(text):
    """Оставляет только таблицу сравнения + строку с финальной оценкой.
    Поддерживает RU и EN разметку."""
    lines = text.splitlines()

    # Ключевые слова (RU + EN)
    TBL_MARKERS = ("СРАВНИТЕЛЬНАЯ ТАБЛИЦА", "COMPARISON TABLE")
    ELO_MARKERS = ("Суммарный ELO", "Total ELO")
    FINAL_MARKERS = ("ФИНАЛЬНАЯ ОЦЕНКА", "FINAL SCORE")

    # 1) начало таблицы
    start = None
    for i, l in enumerate(lines):
        if any(m in l for m in TBL_MARKERS):
            start = i
            break
    if start is None:
        return text  # если разметка поменялась — отдаём как есть

    # 2) конец таблицы — ==== после строки с суммой ELO
    end = len(lines) - 1
    for i in range(start, len(lines)):
        if any(m in lines[i] for m in ELO_MARKERS):
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith("="):
                    end = j
                    break
            break

    # 3) строка финальной оценки
    final = ""
    for l in lines:
        if any(m in l for m in FINAL_MARKERS):
            final = l
            break

    result = lines[start:end + 1]
    if final:
        result.append("")
        result.append(final)
    return "\n".join(result)


# ---------- ДИАЛОГ СРАВНЕНИЯ ----------
class CompareDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LANG["compare_title"])
        self.setGeometry(300, 180, 760, 460)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; }")

        layout = QVBoxLayout(self)

        log = QTextEdit()
        log.setReadOnly(True)
        log.setPlainText(text)
        log.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: Consolas, "Courier New", monospace;
                font-size: 12px;
                border: 1px solid #3a3a3a;
                padding: 6px;
            }
        """)
        layout.addWidget(log)

        btn = QPushButton(LANG["dlg_close"])
        btn.clicked.connect(self.accept)
        btn.setStyleSheet("""
            QPushButton { background-color: #2b2b2b; color: #fff;
                          border: 1px solid #3a3a3a; padding: 8px; }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        layout.addWidget(btn)


# ---------- ГЛАВНОЕ ОКНО ----------
class EnlistedOracleUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.players, self.nicknames = load_players_dict(CSV_FILE)
        self.limits = load_limits(get_resource_path("limits.csv")) or DEFAULT_LIMITS
        self.team_buffer = team_buffer

        # --- Пасхалка: статистика ---
        self.stats_file = os.path.join(get_app_dir(), "user_stats.json")
        self.scan_count = 0
        self.donation_unlocked = False
        self.donation_icon = None
        self._load_stats()

        # --- Звуки (лежат в корне, рядом с gui.py или .exe) ---
        SOUNDS_DIR = os.path.dirname(get_resource_path("scan_done.wav"))
        self.sounds = {}
        self.sound_enabled = True

        def load_sound(name, filename, volume=0.3):
            path = os.path.join(SOUNDS_DIR, filename)
            if not os.path.exists(path):
                print(f"[sound] NOT FOUND: {path}")
                return None
            snd = QSoundEffect()
            snd.setSource(QUrl.fromLocalFile(path))
            snd.setVolume(volume)
            return snd

        # --- Одиночные звуки с индивидуальной громкостью ---
        self.sounds['scan_done']    = load_sound('scan_done',    'scan_done.wav',    volume=1.0)
        self.sounds['compare_done'] = load_sound('compare_done', 'compare_done.wav', volume=0.9)

        # --- Три варианта scan_empty с разной громкостью ---
        self.scan_empty_variants = []
        empty_volumes = [0.6, 0.6, 0.6]

        for i in (1, 2, 3):
            vol = empty_volumes[i - 1] if i - 1 < len(empty_volumes) else 0.3
            snd = load_sound(f'scan_empty_{i}', f'scan_empty_{i}.wav', volume=vol)
            if snd is not None:
                self.scan_empty_variants.append(snd)

        # --- Окно ---
        self.setWindowTitle("Enlisted Oracle")
        self.setWindowIcon(make_icon())
        self.setGeometry(200, 100, 1200, 800)

        # Тёмная тема
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QPushButton { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3a3a3a; padding: 6px; }
            QPushButton:hover { background-color: #3a3a3a; }
            QTextEdit { background-color: #2b2b2b; color: #e0e0e0; border: none; }
            QTableWidget { background-color: #2b2b2b; color: #e0e0e0; }
            QHeaderView::section { background-color: #3a3a3a; color: #ffffff; }
            QLabel { color: #e0e0e0; }
        """)

        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Кнопки ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        layout.addLayout(btn_row)

        for key, handler in [
            ("btn_scan",    self.scan),
            ("btn_manual",  self.manual_input),
            ("btn_compare", self.compare_teams),
            ("btn_clear",   self.clear_teams),
        ]:
            btn = QPushButton(LANG[key])
            btn.clicked.connect(handler)
            btn_row.addWidget(btn)

        # --- Кнопка лога ---
        btn_log = QPushButton(LANG["btn_log_show"])
        btn_log.clicked.connect(self.toggle_log)
        btn_row.addWidget(btn_log)
        self.btn_log = btn_log

        btn_row.addStretch()

        # --- Кнопка звука ---
        self.btn_sound = QPushButton(LANG["btn_sound_on"])
        self.btn_sound.setFixedWidth(40)
        self.btn_sound.clicked.connect(self.toggle_sound)
        btn_row.addWidget(self.btn_sound)           
        # --- Подсказка по цветам ---
        hint = QLabel(LANG["color_hint"])
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet("""
            QLabel {
                color: #cfcfcf;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)
        btn_row.addWidget(hint)

        # --- Две таблицы рядом (Команда A | Команда B) ---
        tables_row = QHBoxLayout()

        # Таблица команды A
        team1_col = QVBoxLayout()
        team1_label = QLabel(LANG["team_a"])
        team1_label.setStyleSheet("font-weight: bold; color: rgb(44, 105, 127); padding: 2px;")
        team1_col.addWidget(team1_label)

        self.table_team1 = PlayersTable(self.limits, header_color="#2c697f")
        team1_col.addWidget(self.table_team1)
        tables_row.addLayout(team1_col, stretch=1)

        # Вертикальный разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #555555;")
        tables_row.addWidget(separator)

        # Таблица команды B
        team2_col = QVBoxLayout()
        team2_label = QLabel(LANG["team_b"])
        team2_label.setStyleSheet("font-weight: bold; color: #8f5450; padding: 2px;")
        team2_col.addWidget(team2_label)

        self.table_team2 = PlayersTable(self.limits, header_color="#8f5450")
        team2_col.addWidget(self.table_team2)
        tables_row.addLayout(team2_col, stretch=1)

        layout.addLayout(tables_row)

        # --- Таблица сравнения (под командами) ---
        compare_label = QLabel(LANG["compare_title"])
        compare_label.setStyleSheet("font-weight: bold; color: rgb(255, 255, 255); padding: 4px;")
        compare_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(compare_label)

        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(5)
        self.compare_table.setHorizontalHeaderLabels([
            LANG["cmp_param"],
            LANG["cmp_team_a"],
            LANG["cmp_team_b"],
            LANG["cmp_diff"],
            LANG["cmp_stronger"],
        ])

        # --- Фиксированные ширины колонок ---
        header = self.compare_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.compare_table.setColumnWidth(0, 160)
        self.compare_table.setColumnWidth(1, 90)
        self.compare_table.setColumnWidth(2, 90)
        self.compare_table.setColumnWidth(3, 230)
        self.compare_table.setColumnWidth(4, 130)

        # --- Фиксированная ширина таблицы под сумму колонок ---
        total_width = 160 + 90 + 90 + 230 + 130   # = 700
        self.compare_table.setFixedWidth(total_width)

        # --- Узкие строки ---
        vh = self.compare_table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(14)
        vh.setMinimumSectionSize(12)
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.compare_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.compare_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.compare_table.setShowGrid(True)
        self.compare_table.setWordWrap(False)

        # --- Убираем скроллбары ---
        self.compare_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.compare_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # --- Фиксированная высота: 12 строк × 14 + заголовок ---
        fixed_h = 12 * 14 + 25
        self.compare_table.setMinimumHeight(fixed_h)
        self.compare_table.setMaximumHeight(fixed_h)

        self.compare_table.setStyleSheet("""
            QTableWidget { gridline-color: #3a3a3a; font-size: 11px; }
            QTableWidget::item { padding: 0px; margin: 0px; }
            QHeaderView::section { padding: 1px 3px; min-height: 16px; font-size: 11px; }
        """)

        # --- Радары + таблица сравнения в один ряд ---
        self.radar_a = TeamRadarWidget("КОМАНДА А", "#d8d8d8")
        self.radar_b = TeamRadarWidget("КОМАНДА Б", "#d8d8d8")

        compare_row = QHBoxLayout()
        compare_row.setSpacing(4)
        compare_row.addWidget(self.radar_a)
        compare_row.addWidget(self.compare_table)
        compare_row.addWidget(self.radar_b)
        layout.addLayout(compare_row)

        # --- Строка с финальным вердиктом ---
        self.verdict_label = QLabel("")
        self.verdict_label.setStyleSheet(
            "font-weight: bold; color: #ffffff; font-size: 12px; padding: 4px;"
        )
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.verdict_label)

        # --- Кнопка экспорта + подпись ---
        export_row = QHBoxLayout()
        export_row.addStretch()

        self.btn_copy = QPushButton(LANG["btn_copy"])
        self.btn_copy.setToolTip(LANG["btn_copy_tooltip"])
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        export_row.addWidget(self.btn_copy)

        self.copy_hint = QLabel("")
        self.copy_hint.setStyleSheet("color: #44ff44; font-size: 12px; padding: 4px 8px;")
        export_row.addWidget(self.copy_hint)
        export_row.addStretch()
        layout.addLayout(export_row)

        # --- Информационная строка (команды + статус) ---
        info_row = QHBoxLayout()
        layout.addLayout(info_row)

        self.team_label = QLabel(LANG["teams_in_buffer_0"])
        info_row.addWidget(self.team_label)

        self.status_label = QLabel(LANG["status_ready"])
        info_row.addWidget(self.status_label)

        info_row.addStretch()

        # --- Пружина ---
        layout.addStretch()

        # --- Лог (внизу, скрыт по умолчанию) ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setVisible(False)
        layout.addWidget(self.log_text)
        self.log_visible = False
        self.log(LANG["log_welcome"], "info")
        self.update_team_info()

        # --- Иконка поддержки — всегда видна ---
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(400, self._show_donation_icon)

    # ---------- Пасхалка: статистика ----------
    def _load_stats(self):
        """Загружает счётчик сканов из файла."""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.scan_count = data.get('scan_count', 0)
                    self.donation_unlocked = data.get('donation_unlocked', False)
        except Exception:
            self.scan_count = 0
            self.donation_unlocked = False

    def _save_stats(self):
        """Сохраняет счётчик сканов в файл."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'scan_count': self.scan_count,
                    'donation_unlocked': self.donation_unlocked,
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _increment_scan(self):
        """Счётчик сканов для статистики. Иконка поддержки теперь всегда видна."""
        self.scan_count += 1
        self._save_stats()

    # ---------- Звук ----------
    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.btn_sound.setText(
            LANG["btn_sound_on"] if self.sound_enabled else LANG["btn_sound_off"]
        )
        self.log(
            LANG["log_sound_on"] if self.sound_enabled else LANG["log_sound_off"],
            "info"
        )

    # ---------- Лог ----------
    def log(self, text, level="info"):
        colors = {"info": "#8ecae6", "success": "#44ff44", "warning": "#ffb703", "danger": "#ff4444"}
        color = colors.get(level, "#ffffff")
        self.log_text.append(f"<font color='{color}'>{text}</font>")

    def capture_output(self, func, *args, **kwargs):
        f = io.StringIO()
        with redirect_stdout(f):
            func(*args, **kwargs)
        out = f.getvalue()
        if out:
            self.log(out.strip())

    def play_sound(self, name):
        """Проигрывает звук по имени, если звук включён."""
        if not self.sound_enabled:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        if snd.status() == QSoundEffect.Status.Loading:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(30, snd.play)
        else:
            snd.play()

    def play_scan_empty(self):
        """Играет случайный из 3 файлов scan_empty."""
        if not self.sound_enabled:
            return
        if not self.scan_empty_variants:
            return

        snd = random.choice(self.scan_empty_variants)
        if snd.status() == QSoundEffect.Status.Loading:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(30, snd.play)
        else:
            snd.play()

    # ---------- Управление командами ----------
    def update_team_info(self):
        count = len(self.team_buffer)
        if count == 0:
            self.team_label.setText(LANG["teams_in_buffer_0"])
        elif count == 1:
            self.team_label.setText(LANG["teams_in_buffer_1"])
        else:
            self.team_label.setText(LANG["teams_in_buffer_2"])

    def set_status(self, text, color="#8ecae6"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def start_anim(self, base_text=None):
        """Запускает мигание в статус-строке."""
        if base_text is None:
            base_text = LANG["status_scan"]
        self._anim_running = True
        self._anim_base = base_text
        self._anim_idx = 0

    def stop_anim(self):
        """Останавливает мигание."""
        self._anim_running = False

    def _tick_anim(self):
        """Один кадр анимации — чередует 🔍🎖️ / 🎖️🔍."""
        if not self._anim_running:
            return
        frames = ["🔍🎖️", "🎖️🔍"]
        icon = frames[self._anim_idx % 2]
        self.status_label.setText(f"{self._anim_base}... {icon}")
        self._anim_idx += 1

    def toggle_log(self):
        """Показывает/скрывает лог. При первом открытии — спрашивает."""
        if self.log_visible:
            # Скрываем без вопросов
            self.log_text.setVisible(False)
            self.log_visible = False
            self.btn_log.setText(LANG["btn_log_show"])
            return

        # Показываем — сначала спрашиваем
        msg = QMessageBox(self)
        msg.setWindowTitle(LANG["dlg_log_title"])
        msg.setText(LANG["dlg_log_text"])
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.button(QMessageBox.StandardButton.Yes).setText(LANG["dlg_yes"])
        msg.button(QMessageBox.StandardButton.No).setText(LANG["dlg_no"])

        msg.setStyleSheet("""
            QMessageBox { background-color: #1e1e1e; }
            QMessageBox QLabel { color: #e0e0e0; font-size: 13px; }
            QMessageBox QPushButton {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 4px 12px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover { background-color: #3a3a3a; }
        """)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            self.log_text.setVisible(True)
            self.log_visible = True
            self.btn_log.setText(LANG["btn_log_hide"])

    def show_teams(self):
        """Заполняет две таблицы: слева команда 1, справа команда 2."""
        self.table_team1.clear_table()
        self.table_team2.clear_table()

        # Команда 1 (первый элемент буфера)
        if len(self.team_buffer) >= 1:
            for player in self.team_buffer[0]:
                if isinstance(player, dict):
                    self.table_team1.add_player(player['name'], player, 100)
                else:
                    nick, data, score = player
                    self.table_team1.add_player(nick, data, score)

        # Команда 2 (второй элемент буфера)
        if len(self.team_buffer) >= 2:
            for player in self.team_buffer[1]:
                if isinstance(player, dict):
                    self.table_team2.add_player(player['name'], player, 100)
                else:
                    nick, data, score = player
                    self.table_team2.add_player(nick, data, score)

    def clear_teams(self):
        self.team_buffer.clear()
        self.table_team1.clear_table()
        self.table_team2.clear_table()
        self.compare_table.setRowCount(0)
        self.verdict_label.setText("")
        if hasattr(self, '_verdict_timer') and self._verdict_timer is not None:
            self._verdict_timer.stop()

        # --- Возвращаем радары в пустое состояние («вентилятор») ---
        self.radar_a.clear_radar()
        self.radar_b.clear_radar()

        self.update_team_info()
        self.log(LANG["log_buffer_cleared"], "info")
        self.set_status(LANG["log_buffer_cleared"], "#8ecae6")

    # ---------- Сканирование ----------
    # ---------- Сканирование ----------
    def scan(self):
        # Защита от повторного нажатия, пока идет сканирование
        if hasattr(self, '_scan_timer') and self._scan_timer.isActive():
            self.log("Сканирование уже идет, подождите...", "warning")
            return

        self.log(LANG["log_scan_start"], "info")
        self.set_status(LANG["log_scan_start"], "#8ecae6")

        img = ImageGrab.grabclipboard()
        if img is None:
            self.log(LANG["log_no_image"], "danger")
            self.set_status(LANG["status_no_image"], "#ff4444")
            self.play_scan_empty()
            return

        self.log(LANG["log_ocr"], "info")
        self.start_anim(LANG["status_scan"])

        # --- OCR в отдельном потоке ---
        self._ocr_result = None
        self._ocr_done = False
        self._scan_start_time = time.time()
        self._min_anim_time = 3.5

        def _do_ocr():
            try:
                self._ocr_result = get_ocr_texts_lens(img)
            except Exception as e:
                print(f"[scan] OCR error: {e}")
                self._ocr_result = []
            self._ocr_done = True

        threading.Thread(target=_do_ocr, daemon=True).start()

        # --- Запускаем QTimer вместо блокирующего while ---
        from PyQt6.QtCore import QTimer
        self._scan_timer = QTimer()
        self._scan_timer.timeout.connect(self._check_scan_status)
        self._scan_timer.start(350)  # проверять каждые 350 мс

    def _check_scan_status(self):
        """Вызывается таймером, пока идет OCR. Не блокирует GUI."""
        self._tick_anim()
        
        if not self._ocr_done:
            return # Еще не готово, ждем дальше

        # OCR готов. Проверяем, прошло ли минимальное время анимации
        texts = self._ocr_result or []
        has_content = any(t.strip() for t in texts)

        if has_content and (time.time() - self._scan_start_time) < self._min_anim_time:
            return # Ждем, чтобы анимация покрутилась хотя бы 3.5 секунды

        # Останавливаем таймер и завершаем скан
        self._scan_timer.stop()
        self.stop_anim()

        all_matches = []
        seen = set()
        for raw in texts:
            if not raw:
                continue
            matches = find_matches(raw, self.nicknames, self.players)
            for nick, data, score in matches:
                if nick not in seen:
                    seen.add(nick)
                    all_matches.append((nick, data, score))

        if not all_matches:
            self.log(LANG["log_nothing_found"], "warning")
            self.set_status(LANG["log_nothing_found"], "#ffb703")
            self.play_scan_empty()
            return

        all_matches = all_matches[:MAX_PLAYERS]
        self.log(LANG["log_found_players"].format(len(all_matches)), "success")
        self._increment_scan()

        self.team_buffer.append(all_matches)
        if len(self.team_buffer) > 2:
            self.team_buffer.pop(0)

        self.show_teams()
        self.update_team_info()
        self.set_status(LANG["status_team_added"].format(len(self.team_buffer)), "#44ff44")

        self.play_sound('scan_done')

        from PyQt6.QtCore import QTimer
        players_data = [data for _, data, _ in all_matches]
        QTimer.singleShot(50, lambda: self.capture_output(analyze_team, players_data, self.limits))    
    # ---------- Ручной ввод ----------
    def manual_input(self):
        try:
            dlg = ManualInputDialog(self.players, self.nicknames, self.limits)
            dlg.exec()

            if not dlg.result_players:
                self.log(LANG["log_manual_cancel"], "warning")
                self.set_status(LANG["status_cancelled"], "#ffb703")
                return

            team = [(p['name'], p, 100) for p in dlg.result_players]
            self.team_buffer.append(team)
            if len(self.team_buffer) > 2:
                self.team_buffer.pop(0)

            self.show_teams()
            self.update_team_info()
            self.log(
                LANG["log_manual_added"].format(len(self.team_buffer)),
                "success"
            )
            self.set_status(
                LANG["status_team_added"].format(len(self.team_buffer)),
                "#44ff44"
            )
            self.capture_output(analyze_team, dlg.result_players, self.limits)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(LANG["log_manual_error"].format(e), "danger")
            self.set_status(LANG["status_error"], "#ff4444")

    # ---------- Сравнение ----------
    def compare_teams(self):
        if len(self.team_buffer) < 2:
            self.log(LANG["log_need_two_teams"], "warning")
            self.set_status(LANG["status_not_enough_teams"], "#ffb703")
            self.play_scan_empty()
            return

        def extract_data(team):
            result = []
            for p in team:
                if isinstance(p, dict):
                    result.append(p)
                else:
                    result.append(p[1])
            return result

        team_a = extract_data(self.team_buffer[-2])
        team_b = extract_data(self.team_buffer[-1])

        self.log(LANG["log_compare"], "info")
        self.start_anim(LANG["status_compare"])

        self._cmp_text = ""
        self._cmp_done = False

        def _do_compare():
            f = io.StringIO()
            try:
                with redirect_stdout(f):
                    compare_two_teams(
                        team_a, team_b,
                        self.players, self.nicknames, self.limits,
                        normalize_ocr_word, process, fuzz,
                        get_color_icon,
                        safe_float, safe_int, safe_elo
                    )
                self._cmp_text = f.getvalue()
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._cmp_text = LANG["log_compare_error"].format(e)
            self._cmp_done = True

        threading.Thread(target=_do_compare, daemon=True).start()

        start_time = time.time()
        MIN_ANIM_TIME = 0.6

        while not self._cmp_done or (time.time() - start_time) < MIN_ANIM_TIME:
            self._tick_anim()
            QApplication.processEvents()
            time.sleep(0.35)

        self.stop_anim()
        text = self._cmp_text
        self._fill_compare_table(text)
        self._update_radars(team_a, team_b)         
        self.log(text)
        self.set_status(LANG["status_compare_done"], "#44ff44")
        self.log(LANG["log_compare_done"], "success")

        QApplication.processEvents()
        self.play_sound('compare_done')
    def _update_radars(self, team_a, team_b):
        """
        Считает метрики для двух команд и обновляет радары.

        Агрегация:
          - K/D, WR, Захваты, Хедшоты, Постройки, БТР — среднее по команде.
          - ELO — сумма по команде (как «Суммарный ELO» в compare_two_teams).
            Пороги limits['elo'] умножаем на число игроков, чтобы шкала 0–100%
            осталась сравнимой с одиночным игроком.
        """
        # (ключ данных, ключ limits, ключ подписи в LANG, режим)
        METRIC_MAP = [
            ('kd',          'kd',       'radar_kd',    'avg'),
            ('win_percent', 'wr',       'radar_wr',    'avg'),
            ('elo',         'elo_team', 'radar_elo',   'sum'),
            ('captures',    'cap',      'radar_cap',   'avg'),
            ('headshots',   'hs',       'radar_hs',    'avg'),
            ('built',       'built',    'radar_built', 'avg'),
            ('apc_spawns',  'apc',      'radar_apc',   'avg'),
        ]

        def agg(team, key, mode):
            """Возвращает (значение, кол-во игроков)."""
            vals = []
            for p in team:
                v = p.get(key, 0)
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    pass
            if not vals:
                return 0.0, 0
            total = sum(vals)
            if mode == 'sum':
                return total, len(vals)
            return total / len(vals), len(vals)

        labels   = []
        pct_a    = []
        pct_b    = []
        colors_a = []
        colors_b = []

        for data_key, limits_key, label_key, mode in METRIC_MAP:
            lim = self.limits.get(limits_key, {}) or {}

            a_val, a_n = agg(team_a, data_key, mode)
            b_val, b_n = agg(team_b, data_key, mode)

            # Пороги для sum-метрик уже заданы в limits.csv под команду.
            a_lim = lim
            b_lim = lim

            pct_a.append(calc_metric_percent(a_val, a_lim))
            pct_b.append(calc_metric_percent(b_val, b_lim))
            colors_a.append(rank_to_color(value_to_rank(a_val, a_lim)))
            colors_b.append(rank_to_color(value_to_rank(b_val, b_lim)))
            labels.append(LANG.get(label_key, label_key))

        # Каждый радар получает призрак соседа — для визуального сравнения
        self.radar_a.update_radar(labels, pct_a, colors_a, ghost_values=pct_b)
        self.radar_b.update_radar(labels, pct_b, colors_b, ghost_values=pct_a)

    def _fill_compare_table(self, text):
        """Парсит вывод compare_two_teams и заполняет таблицу.
        Поддерживает RU и EN разметку. Переводит финальный вердикт и колонку 'Сильнее'."""
        import re
        self.compare_table.setRowCount(0)
        self.verdict_label.setText("")

        lines = text.splitlines()
        in_table = False

        # RU + EN маркеры
        TBL_MARKERS = ("СРАВНИТЕЛЬНАЯ ТАБЛИЦА", "COMPARISON TABLE")
        PARAM_MARKERS = ("Параметр", "Parameter")
        FINAL_MARKERS = ("ФИНАЛЬНАЯ ОЦЕНКА", "FINAL SCORE")
        TEAM_A_MARKERS = ("Команда A", "Team A")
        TEAM_B_MARKERS = ("Команда B", "Team B")

        for line in lines:
            stripped = line.strip()

            if any(m in stripped for m in TBL_MARKERS):
                in_table = True
                continue

            if in_table:
                if stripped.startswith("===="):
                    if self.compare_table.rowCount() > 0:
                        in_table = False
                    continue
                if any(stripped.startswith(m) for m in PARAM_MARKERS):
                    continue
                if stripped.startswith("---") or not stripped:
                    continue

                parts = re.split(r'\s{2,}', stripped)
                if len(parts) >= 5:
                    row = self.compare_table.rowCount()
                    self.compare_table.insertRow(row)
                    for col, cell in enumerate(parts[:5]):
                        # Колонка "Сильнее" — переводим "Команда A/B" на текущий язык
                        if col == 4:
                            cell = cell.replace("🟢 ", "").replace("🔴 ", "").strip()
                            if any(m in cell for m in TEAM_A_MARKERS):
                                cell = LANG["team_a"]
                            elif any(m in cell for m in TEAM_B_MARKERS):
                                cell = LANG["team_b"]
                            elif "Равно" in cell:
                                cell = LANG["cmp_equal"]

                        item = QTableWidgetItem(cell)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                        if col == 4:
                            if any(m in cell for m in TEAM_A_MARKERS) or cell == LANG["team_a"]:
                                item.setForeground(QColor("#2c697f"))
                            elif any(m in cell for m in TEAM_B_MARKERS) or cell == LANG["team_b"]:
                                item.setForeground(QColor("#8f5450"))

                        self.compare_table.setItem(row, col, item)

            # Финальный вердикт — переводим на текущий язык
            if any(m in stripped for m in FINAL_MARKERS):
                match = re.search(r'([\d.]+)%', stripped)
                if match:
                    pct = match.group(1)
                    if any(m in stripped for m in TEAM_A_MARKERS):
                        self._animate_verdict(LANG["final_verdict_a"].format(pct))
                    elif any(m in stripped for m in TEAM_B_MARKERS):
                        self._animate_verdict(LANG["final_verdict_b"].format(pct))
                    else:
                        self._animate_verdict(LANG["final_verdict_equal"])
                else:
                    self._animate_verdict(LANG["final_verdict_equal"])
    def _animate_verdict(self, text):
        """Fade-in + золотая вспышка → откат к белому. Синхронно со звуком."""
        from PyQt6.QtCore import QTimer
        import math

        # Останавливаем предыдущую анимацию, если была
        if hasattr(self, '_verdict_timer') and self._verdict_timer is not None:
            self._verdict_timer.stop()

        self.verdict_label.setText(text)

        # Параметры анимации
        self._v_total = 40          # всего кадров
        self._v_step = 0
        self._v_step_ms = 20        # 20 мс × 40 = 0.8 сек

        self._verdict_timer = QTimer(self)
        self._verdict_timer.timeout.connect(self._verdict_tick)
        self._verdict_timer.start(self._v_step_ms)

    def _verdict_tick(self):
        """Один кадр: alpha 0→1 на первых 20%, потом золото→белый."""
        import math

        self._v_step += 1
        if self._v_step > self._v_total:
            self._verdict_timer.stop()
            # Финал — чистый белый
            self.verdict_label.setStyleSheet(
                "font-weight: bold; color: #ffffff; font-size: 12px; padding: 4px;"
            )
            return

        t = self._v_step / self._v_total         # 0..1

        # --- Фаза 1 (0..0.5): фейд от чёрного к золотому ---
        # --- Фаза 2 (0.5..1): плавный откат золота к белому ---
        if t < 0.5:
            k = t / 0.5                          # 0..1
            # цвет от очень тёмного к золоту
            r = int(0x30 + (0xff - 0x30) * k)
            g = int(0x30 + (0xd7 - 0x30) * k)
            b = int(0x30 + (0x00 - 0x30) * k)
        else:
            k = (t - 0.5) / 0.5                  # 0..1
            # цвет от золота к белому
            r = int(0xff + (0xff - 0xff) * k)    # остаётся ff
            g = int(0xd7 + (0xff - 0xd7) * k)
            b = int(0x00 + (0xff - 0x00) * k)

        self.verdict_label.setStyleSheet(
            f"font-weight: bold; color: rgb({r},{g},{b}); font-size: 12px; padding: 4px;"
        )
    def copy_to_clipboard(self):
        """Скриншот всего окна → буфер обмена + подпись 'Скопировано'."""
        if self.compare_table.rowCount() == 0:
            self.log(LANG["log_no_copy_data"], "warning")
            self.set_status(LANG["status_no_copy_data"], "#ffb703")
            self.play_scan_empty()
            return

        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer

            was_log_visible = self.log_visible
            if was_log_visible:
                self.log_text.setVisible(False)

            was_maximized = self.isMaximized()
            if not was_maximized:
                self.showMaximized()

            QApplication.processEvents()
            time.sleep(0.15)
            QApplication.processEvents()

            pixmap = self.grab()

            if not was_maximized:
                self.showNormal()
            if was_log_visible:
                self.log_text.setVisible(True)

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

            self.copy_hint.setText(LANG["btn_copy_hint"])
            self.copy_hint.setStyleSheet("color: #44ff44; font-size: 12px; padding: 4px 8px;")

            self.btn_copy.setText(LANG["btn_copy_done"])
            self.btn_copy.setStyleSheet("background-color: #2c5a2c; color: #ffffff;")

            def reset_button():
                self.copy_hint.setText("")
                self.btn_copy.setText(LANG["btn_copy_reset"])
                self.btn_copy.setStyleSheet("")

            QTimer.singleShot(3000, reset_button)

            self.log(LANG["log_copy_done"], "success")
            self.set_status(LANG["status_copy_ready"], "#ff44ff")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(LANG["log_copy_error"].format(e), "danger")
            self.set_status(LANG["status_error"], "#ff4444")
            self.copy_hint.setText(LANG["copy_hint_error"])
            self.copy_hint.setStyleSheet("color: #ff4444; font-size: 12px; padding: 4px 8px;")
    # ---------- Пасхалка: иконка ☕ ----------
    def _show_donation_icon(self):
        """Иконка поддержки в правом нижнем углу с парением."""
        if self.donation_icon is not None:
            return

        from PyQt6.QtCore import QTimer

        self.donation_icon = QPushButton("☕", self)
        self.donation_icon.setFixedSize(40, 40)
        self.donation_icon.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #ffd700;
            }
        """)
        self.donation_icon.setToolTip(LANG["dlg_donation_title"])
        self.donation_icon.clicked.connect(self._open_donation_dialog)

        self.donation_icon.setParent(self)
        self.donation_icon.show()
        self.donation_icon.raise_()

        # --- Парение через QTimer ---
        self._anim_step = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_donation)
        self._anim_timer.start(50)   # 20 кадров в секунду

    def _tick_donation(self):
        """Один кадр парения — синусоида ±4 px."""
        import math
        if self.donation_icon is None:
            return
        self._anim_step = (self._anim_step + 1) % 80
        offset = int(4 * math.sin(self._anim_step / 80 * 2 * math.pi))
        self.donation_icon.move(self.width() - 60, self.height() - 80 + offset)

    def _open_donation_dialog(self):
        """Диалог 'Поддержать проект' с фоном-котом."""
        cat_path = None
        for name in ("cat.png", "cat.jpg", "cat.jpeg"):
            p = get_resource_path(name)
            if os.path.exists(p):
               cat_path = p
               break

        W, H = 420, 400

        # --- Создаём диалог ---
        dlg = QDialog(self)
        dlg.setWindowTitle(LANG["dlg_donation_title"])
        dlg.setFixedSize(W, H)

        # --- Фон-кот (QLabel под всем контентом) ---
        if cat_path:
            from PyQt6.QtGui import QPixmap, QPainter, QColor

            # 1. Масштаб: заполняет окно, пропорции сохранены
            pix = QPixmap(cat_path).scaled(
                W, H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

            # 2. Обрезка по центру, если картинка «вылезла»
            if pix.width() > W or pix.height() > H:
                x = (pix.width() - W) // 2
                y = (pix.height() - H) // 2
                pix = pix.copy(x, y, W, H)

            # 3. Лёгкое затемнение (число в конце: 0=прозрачно, 255=чёрный)
            painter = QPainter(pix)
            painter.fillRect(pix.rect(), QColor(20, 20, 30, 110))
            painter.end()

            # 4. Фоновый QLabel
            bg = QLabel(dlg)
            bg.setGeometry(0, 0, W, H)
            bg.setPixmap(pix)
            bg.setScaledContents(False)
            bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            bg.lower()

        # --- Стили диалога (кнопки) ---
        dlg.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QPushButton {
                background-color: rgba(43, 43, 43, 230);
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(58, 58, 58, 250);
                border: 1px solid #ffd700;
            }
        """)

        # --- Layout ---
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # --- Заголовок ---
        title = QLabel(LANG["dlg_donation_header"])
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #ffd700; padding: 8px;"
            "background-color: rgba(0, 0, 0, 180); border-radius: 6px;"
        )
        layout.addWidget(title)

        # --- Основной текст ---
        text = QLabel(LANG["dlg_donation_text"])
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        text.setStyleSheet(
            "font-size: 12px; padding: 8px;"
            "background-color: rgba(0, 0, 0, 160); border-radius: 6px;"
        )
        layout.addWidget(text)

        # --- Заголовок реквизитов ---
        req_label = QLabel(LANG["dlg_donation_requisites"])
        req_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        req_label.setStyleSheet(
            "font-weight: bold; color: #8ecae6; padding: 6px;"
            "background-color: rgba(0, 0, 0, 180); border-radius: 6px;"
        )
        layout.addWidget(req_label)

        # --- Карта ---
        card = QLabel(LANG["dlg_donation_card"])
        card.setTextFormat(Qt.TextFormat.RichText)
        card.setStyleSheet(
            "font-size: 13px; padding: 6px;"
            "background-color: rgba(0, 0, 0, 160); border-radius: 6px;"
        )
        layout.addWidget(card)

        # --- Boosty ---
        link = QLabel(LANG["dlg_donation_boosty"])
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)
        link.setStyleSheet(
            "font-size: 13px; padding: 6px;"
            "background-color: rgba(0, 0, 0, 160); border-radius: 6px;"
        )
        layout.addWidget(link)

        # --- Telegram ---
        tg = QLabel(LANG["dlg_donation_tg"])
        tg.setTextFormat(Qt.TextFormat.RichText)
        tg.setStyleSheet(
            "font-size: 13px; padding: 6px;"
            "background-color: rgba(0, 0, 0, 160); border-radius: 6px;"
        )
        layout.addWidget(tg)

        # --- Кнопка "Скопировать карту" ---
        btn_copy_card = QPushButton("📋 Скопировать номер карты")

        def copy_card():
            import re
            from PyQt6.QtCore import QTimer
            raw = LANG["dlg_donation_card"]
            m = re.search(r'(\d[\d\s]{10,})', raw)
            if m:
                QApplication.clipboard().setText(m.group(1).strip())
                btn_copy_card.setText("✅ Скопировано")
                QTimer.singleShot(
                    2000,
                    lambda: btn_copy_card.setText("📋 Скопировать номер карты")
                )

        btn_copy_card.clicked.connect(copy_card)
        layout.addWidget(btn_copy_card)

        layout.addStretch()

        # --- Кнопка "Закрыть" ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(LANG["dlg_close"])
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()

# ---------- ДИАЛОГ РУЧНОГО ВВОДА ----------
class ManualInputDialog(QDialog):
    def __init__(self, players, nicknames, limits):
        super().__init__()
        self.players = players
        self.nicknames = nicknames
        self.limits = limits
        self.result_players = []

        self.setWindowTitle(LANG["manual_title"])
        self.setGeometry(400, 200, 400, 500)
        self.setStyleSheet(
            "QDialog { background-color: #2b2b2b; } "
            "QLineEdit, QListWidget { background-color: #3a3a3a; color: #ffffff; }"
        )

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText(LANG["manual_placeholder"])
        layout.addWidget(self.entry)

        self.listbox = QListWidget()
        layout.addWidget(self.listbox)

        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)

        btn_add = QPushButton(LANG["manual_add"])
        btn_add.clicked.connect(self.add_nick)
        btn_row.addWidget(btn_add)

        btn_remove = QPushButton(LANG["manual_remove"])
        btn_remove.clicked.connect(self.remove_selected)
        btn_row.addWidget(btn_remove)

        btn_finish = QPushButton(LANG["manual_done"])
        btn_finish.clicked.connect(self.finish)
        layout.addWidget(btn_finish)

        self.entry.returnPressed.connect(self.add_nick)

    def add_nick(self):
        nick = self.entry.text().strip()
        if nick:
            self.listbox.addItem(QListWidgetItem(nick))
            self.entry.clear()

    def remove_selected(self):
        for item in self.listbox.selectedItems():
            row = self.listbox.row(item)
            self.listbox.takeItem(row)

    def finish(self):
        raw_inputs = [self.listbox.item(i).text() for i in range(self.listbox.count())]
        if not raw_inputs:
            self.accept()
            return

        # Перехватываем print из print_manual_players_table, чтобы не мусорить в консоль
        f = io.StringIO()
        try:
            with redirect_stdout(f):
                self.result_players = print_manual_players_table(
                    raw_inputs=raw_inputs,
                    players=self.players,
                    nicknames=self.nicknames,
                    limits=self.limits,
                    normalize_ocr_word=normalize_ocr_word,
                    process=process,
                    fuzz=fuzz,
                    get_color_icon=get_color_icon,
                    safe_float=safe_float,
                    safe_int=safe_int,
                    safe_elo=safe_elo
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.result_players = []
        self.accept()


# ---------- ЗАПУСК ----------
# ---------- ВЫБОР ЯЗЫКА ПРИ ПЕРВОМ ЗАПУСКЕ ----------
def choose_language_if_needed():
    """
    Если в user_stats.json нет ключа 'lang' — показываем диалог выбора.
    Возвращает 'ru' или 'en'.
    """
    stats_file = os.path.join(get_app_dir(), "user_stats.json")

    # Читаем существующий выбор
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                lang = data.get('lang')
                if lang in ('ru', 'en'):
                    return lang
        except Exception:
            pass

    # Диалог выбора языка (при первом запуске)
    dlg = QDialog()
    dlg.setWindowTitle("Language / Язык")
    dlg.setFixedSize(340, 200)
    dlg.setStyleSheet("""
        QDialog { background-color: #1e1e1e; }
        QLabel { color: #e0e0e0; font-size: 13px; }
        QPushButton {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #3a3a3a;
            padding: 10px;
            font-size: 14px;
            min-height: 30px;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
            border: 1px solid #8ecae6;
        }
    """)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(10)

    title = QLabel("Choose language / Выберите язык")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)

    btn_ru = QPushButton("🇷🇺 Русский")
    layout.addWidget(btn_ru)

    btn_en = QPushButton("🇬🇧 English")
    layout.addWidget(btn_en)

    chosen = {'lang': 'ru'}   # по умолчанию — русский

    def pick(lang):
        chosen['lang'] = lang
        dlg.accept()

    btn_ru.clicked.connect(lambda: pick('ru'))
    btn_en.clicked.connect(lambda: pick('en'))

    dlg.exec()

    # Сохраняем выбор
    try:
        data = {}
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data['lang'] = chosen['lang']
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[lang] save error: {e}")

    return chosen['lang']


# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    import qdarkstyle

    # Windows: чтобы панель задач брала нашу иконку, а не иконку Python
    if sys.platform == "win32":
        import ctypes
        res = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "EnlistedOracle.App.1"
        )
        print(f"[AppUserModelID] result: {res} (0 = success)")
    else:
        print(f"[AppUserModelID] skipped, platform: {sys.platform}")

    # --- Создаём QApplication ДО диалога выбора языка ---
    app = QApplication(sys.argv)
    app.setApplicationName("Enlisted Oracle")
    app.setOrganizationName("EnlistedOracle")
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))

    # --- Выбор языка (только при первом запуске) ---
    current_lang = choose_language_if_needed()

    # --- Устанавливаем глобальную LANG ---
    globals()['LANG'] = LANG_RU if current_lang == 'ru' else LANG_EN

    icon = make_icon()
    print(f"[icon] isNull: {icon.isNull()}")
    print(f"[icon] sizes: {icon.availableSizes()}")
    app.setWindowIcon(icon)

    window = EnlistedOracleUI()
    window.setWindowIcon(icon)
    window.show()

    print(f"[window] icon.isNull(): {window.windowIcon().isNull()}")
    print(f"[window] icon sizes: {window.windowIcon().availableSizes()}")

    sys.exit(app.exec())