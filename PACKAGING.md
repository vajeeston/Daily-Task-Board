# Packaging (Windows EXE)

This project can be distributed as a **single .exe** on Windows using **PyInstaller**.

## 1) Create/activate your environment

```bat
conda create -n dtb python=3.10 -y
conda activate dtb
pip install -r requirements.txt
pip install pyinstaller
```

## 2) Build (one-file EXE)

### Option A — run the build script

```bat
build_windows_onefile.bat
```

### Option B — run PyInstaller manually

```bat
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name DailyTaskBoard ^
  --icon app_icon.ico ^
  --add-data "assets;assets" ^
  --add-data "docs;docs" ^
  --add-data "daily_tasks.xlsx;." ^
  --add-data "app_icon.ico;." ^
  --add-data "app_icon.png;." ^
  main.py
```

### Option C — use the spec file

```bat
pyinstaller --noconfirm --clean DailyTaskBoard.spec
```

## 3) Output

Your executable will be located at:

```
dist\DailyTaskBoard.exe
```

## 4) Where user data is saved

When running as an EXE, the workbook is stored in the user's writable app-data folder:

- `AppData\Roaming\DailyTaskBoard\DailyTaskBoard\daily_tasks.xlsx` (typical)

The app automatically copies the bundled `daily_tasks.xlsx` there on the first run.

## 5) Troubleshooting

- **Icons/banner missing**: you likely forgot `--add-data "assets;assets"` or used the wrong delimiter.
  - On Windows, `--add-data` uses `SOURCE;DEST` (semicolon).

- **Antivirus false positives**: single-file EXEs can trigger heuristics. Try building `--onedir` if needed.

- **Permission errors**: don't write next to the EXE in `Program Files`. This app defaults to a per-user folder.
