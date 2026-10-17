# radar_widget.py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import to_rgb

plt.style.use("dark_background")


ZONES = [
    (0,   20,  "#2ecc71", 0.09),   # 🟢
    (20,  40,  "#ffd700", 0.13),   # 🟡
    (40,  60,  "#ff7f00", 0.17),   # 🔶
    (60,  80,  "#e74c3c", 0.21),   # 🔴
    (80,  100, "#9b59b6", 0.26),   # 🟣
]

RING_BOUNDARIES = [20, 40, 60, 80, 100]


def rank_to_color(text):
    if "Элита" in text:     return "#9b59b6"
    if "Сильный" in text:   return "#e74c3c"
    if "Средний" in text:   return "#ff7f00"
    if "Ниже ср." in text:  return "#ffd700"
    if "Слабый" in text:    return "#2ecc71"
    return "#bbbbbb"


def soften_color(color, factor=0.35):
    r, g, b = to_rgb(color)
    r = r + (0.5 - r) * factor
    g = g + (0.5 - g) * factor
    b = b + (0.5 - b) * factor
    return (r, g, b)


def value_to_rank(value, limits_row):
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "Слабый"
    if v >= limits_row.get('purple', 0): return "Элита"
    if v >= limits_row.get('red', 0):    return "Сильный"
    if v >= limits_row.get('orange', 0): return "Средний"
    if v >= limits_row.get('yellow', 0): return "Ниже ср."
    return "Слабый"


def calc_metric_percent(value, limits_row):
    try:
        v = float(value)
    except (ValueError, TypeError):
        return 0.0
    y = limits_row.get('yellow', 0)
    o = limits_row.get('orange', 0)
    r = limits_row.get('red', 0)
    p = limits_row.get('purple', 0)
    if v < y:
        return max(0.0, (v / y) * 20.0) if y > 0 else 0.0
    if v < o:
        return 20.0 + ((v - y) / (o - y)) * 20.0 if o > y else 20.0
    if v < r:
        return 40.0 + ((v - o) / (r - o)) * 20.0 if r > o else 40.0
    if v < p:
        return 60.0 + ((v - r) / (p - r)) * 20.0 if p > r else 60.0
    cap = p * 1.2
    return min(100.0, 80.0 + ((v - p) / (cap - p)) * 20.0) if cap > p else 100.0


from PyQt6.QtCore import QTimer

class TeamRadarWidget(FigureCanvas):
    def __init__(self, team_name="Команда", accent_color="#d8d8d8", parent=None):
        self.fig, self.ax = plt.subplots(
            figsize=(2.5, 2.5),
            subplot_kw=dict(polar=True)
        )
        self.team_name = team_name
        self.accent_color = accent_color
        self.fig.patch.set_facecolor("#1e1e1e")
        self.ax.set_facecolor("#141414")
        super().__init__(self.fig)
        
        # --- Для анимации ---
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_progress = 1.0
        self._anim_target_values = []
        self._anim_metrics = []
        self._anim_rank_colors = []
        self._anim_ghost_values = None
        
        self.clear_radar()

    def clear_radar(self):
        """Пустая заготовка: цветные зоны + сетка, БЕЗ цифр и подписей."""
        self.ax.clear()
        self.ax.set_facecolor("#141414")

        theta = np.linspace(0, 2 * np.pi, 720)

        # Цветные зоны-ранги
        for inner, outer, color, alpha in ZONES:
            self.ax.fill_between(theta, inner, outer, color=color, alpha=alpha)

        # Границы колец
        for r in RING_BOUNDARIES:
            self.ax.plot(
                theta, np.full_like(theta, r),
                color="#666666", linewidth=0.8, alpha=0.35
            )

        # 8 спиц-радиалов
        for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            self.ax.plot(
                [ang, ang], [0, 100],
                color="#666666", linewidth=0.8, alpha=0.35
            )

        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_ylim(0, 100)
        self.ax.grid(False)
        self.ax.set_title("", pad=15)
        self.draw()

    def start_jojo_animation(self, metrics, target_values, rank_colors=None, 
                             ghost_values=None, duration_ms=1200):
        """
        Запускает JoJo-анимацию: раскрытие из центра с эффектом взрыва.
        """
        self._anim_metrics = metrics
        self._anim_target_values = list(target_values)
        self._anim_rank_colors = rank_colors or ["#2ecc71"] * len(metrics)
        self._anim_ghost_values = ghost_values
        
        self._anim_progress = 0.0
        self._anim_duration = duration_ms
        self._anim_elapsed = 0
        
        # 30 кадров в секунду (33 мс) для плавности
        self._anim_timer.start(33)
        
    def _anim_tick(self):
        """Один кадр анимации."""
        self._anim_elapsed += 33
        
        # Прогресс от 0.0 до 1.0
        t = min(1.0, self._anim_elapsed / self._anim_duration)
        
        # Ease-out cubic: быстрый старт, плавное замедление (эффект ДжоДжо)
        ease_t = 1.0 - (1.0 - t) ** 3
        
        # Текущие значения = финальные * прогресс
        current_values = [v * ease_t for v in self._anim_target_values]
        
        # Рисуем кадр
        self._draw_frame(
            self._anim_metrics, 
            current_values, 
            self._anim_rank_colors, 
            self._anim_ghost_values,
            progress=ease_t
        )
        
        if t >= 1.0:
            self._anim_timer.stop()

    def _draw_frame(self, metrics, values_pct, rank_colors, ghost_values, progress=1.0):
        """Внутренний метод для отрисовки кадра."""
        self.ax.clear()
        self.ax.set_facecolor("#141414")

        theta = np.linspace(0, 2 * np.pi, 720)
        
        # 1. Зоны-ранги
        for inner, outer, color, alpha in ZONES:
            self.ax.fill_between(theta, inner, outer, color=color, alpha=alpha)

        # 2. Кольца
        for r in RING_BOUNDARIES:
            self.ax.plot(theta, np.full_like(theta, r),
                         color="#666666", linewidth=0.8, alpha=0.35)

        num_vars = len(metrics)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        
        # Замыкаем значения для полигона
        values = values_pct + values_pct[:1]

        # 3. Призрак соседа (если передан)
        if ghost_values is not None and len(ghost_values) == num_vars:
            # Призрак тоже анимируем, чтобы он не появлялся сразу
            ghost_scaled = [v * progress for v in ghost_values]
            ghost = ghost_scaled + ghost_scaled[:1]
            self.ax.plot(angles, ghost, color="#aaaaaa", linewidth=1.2,
                         linestyle="--", alpha=0.30, zorder=35)

        # 4. Заливка (JoJo style!)
        # Добавляем полупрозрачную заливку цветом команды
        self.ax.fill(angles, values, color=self.accent_color, alpha=0.15, zorder=38)

        # 5. Свечение (Glow)
        self.ax.plot(angles, values, color="#ffffff", linewidth=8, alpha=0.02, zorder=40)
        self.ax.plot(angles, values, color="#ffffff", linewidth=5, alpha=0.04, zorder=41)
        self.ax.plot(angles, values, color="#ffffff", linewidth=3, alpha=0.075, zorder=42)
        
        # 6. Основная линия
        self.ax.plot(angles, values, color=self.accent_color, linewidth=2.5, zorder=50)

        # 7. Точки (маленькие и цветные)
        if rank_colors is None:
            rank_colors = ["#2ecc71"] * num_vars

        for a, v, c in zip(angles[:-1], values[:-1], rank_colors):
            self.ax.scatter(a, v, s=15, color=c, edgecolors='white', linewidths=0.5,
                            alpha=1.0, zorder=100)

        # 8. Подписи метрик
        self.ax.set_xticks(angles[:-1])
        labels = self.ax.set_xticklabels(metrics, color="#e0e0e0", fontsize=9, fontweight="bold")
        for lbl, color in zip(labels, rank_colors):
            lbl.set_color(color)
            lbl.set_alpha(0.80)

        self.ax.set_ylim(0, 100)
        self.ax.set_yticks(RING_BOUNDARIES)
        self.ax.set_yticklabels([])
        self.ax.grid(False)
        self.ax.set_title(self.team_name, color="#e0e0e0", fontsize=12, fontweight="bold", pad=15)
        self.draw()