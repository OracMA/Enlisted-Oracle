# Enlisted Oracle

A tool for analyzing players and teams in the game **Enlisted**.  
It captures screenshots, extracts nicknames, looks up their career stats, and compares two teams to predict the outcome of a battle.

> 🇷🇺 **Русскоязычная версия:** см. файл - Прочитай меня блять

## ✨ Features

- 🔍 **OCR recognition** of player nicknames from screenshots
- 📊 **Player stats lookup** from a local database (687k+ entries)
- ⚔️ **Team comparison** with a final score and verdict
- 🎨 **Color-coded metrics** (K/D, win rate, ELO, headshots, etc.)


- 🖥️ **GUI (PyQt6)** and **CLI** modes
- 🌐 **Bilingual interface** (Russian / English)

---

## 🚀 Installation

### Windows (recommended)

1. **Download or clone** this repository.
2. Make sure you have **Python 3.10 – 3.13** installed and added to PATH.  
   (Python 3.14 may have issues with some libraries.)
3. Run **`install.bat`** – it will install all dependencies automatically.
4. Run **`run.bat`** to start the program.

### Manual installation (any OS)

```bash
# Clone the repo
git clone https://github.com/your-username/enlisted-oracle.git
cd enlisted-oracle

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python gui.py



### Changing the language

If you accidentally selected the wrong language on first launch, you can change it:

1. Open `user_stats.json` in the program folder.
2. Find the line `"lang": "ru"` (or `"en"`).
3. Change it to `"lang": "en"` (or `"ru"`).
4. Save the file and restart the program.

Alternatively, just delete `user_stats.json` and the language selection dialog will appear again on the next launch.