# Enlisted Oracle

A tool for analyzing players and teams in the game **Enlisted**.
It captures screenshots, extracts nicknames, looks up their career stats,
and compares two teams to predict the outcome of a battle.

> 🇷🇺 Русскоязычная версия: см. файл «Прочитай меня блять»

---

## ✨ Features

- 🔍 **OCR recognition** of player nicknames from screenshots
- 📁 **Player stats lookup** from a local database (687k+ entries)
- ⚖️ **Team comparison** with a final score and verdict
- 📊 **Radial (radar) diagrams** — visual side-by-side comparison of both teams
  by 7 key metrics, with the opponent's polygon drawn as a faint ghost overlay
- 🎨 **Color-coded metrics** (K/D, win rate, ELO, headshots, captures, APC,
  vehicles, builds)
- 🖥️ **GUI (PyQt6)** and CLI modes
- 🌐 **Bilingual interface** (Russian / English)

---

## 📦 Installation

### Windows (recommended)

1. Download or clone this repository.
2. Unpack `enlisted_players_full.7z` into the root folder
   (next to `gui.py` and `main.py`).
3. Make sure you have **Python 3.10 – 3.13** installed and added to PATH.
   *(Python 3.14 may have issues with some libraries.)*
4. Run `install.bat` — it will install all dependencies automatically.
5. Run `run.bat` to start the program.

### Manual installation (any OS)

```bash
# Clone the repo
git clone https://github.com/OracMA/Enlisted-Oracle.git
cd Enlisted-Oracle

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python gui.py
