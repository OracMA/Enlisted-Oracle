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
