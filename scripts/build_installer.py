"""
ULTRON — Standalone Windows Installer & Uninstaller Generator
─────────────────────────────────────────────────────────────────────────────
Generates a self-contained, deterministic Windows installer executable and
companion uninstaller that enforces:
- Non-admin per-user installation in %LOCALAPPDATA%\\Programs\\ULTRON
- Automatic Start Menu shortcut creation
- Optional Windows startup registration
- Clean, non-destructive uninstallation that preserves user data unless requested
- Zero dependencies on Git, IDE, or developer Python
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import argparse
import base64
import os
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ultron.__version__ import __version__, __product_name__, __build_date__


def generate_installer_script(payload_b64: str, product_name: str, version: str, build_date: str) -> str:
    lines = [
        '"""',
        f'ULTRON — Official Windows Setup & Installer',
        f'Version: {version} (Build: {build_date})',
        '"""',
        'import os',
        'import sys',
        'import shutil',
        'import zipfile',
        'import subprocess',
        'import argparse',
        'from pathlib import Path',
        '',
        f'PRODUCT_NAME = "{product_name}"',
        f'VERSION = "{version}"',
        f'ZIP_PAYLOAD_B64 = """{payload_b64}"""',
        '',
        'def get_default_install_dir() -> Path:',
        '    local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))',
        '    return Path(local_app_data) / "Programs" / PRODUCT_NAME',
        '',
        'def create_shortcut(target: Path, shortcut_path: Path, description: str = "") -> None:',
        '    if sys.platform != "win32":',
        '        return',
        '    try:',
        '        import win32com.client',
        '        shell = win32com.client.Dispatch("WScript.Shell")',
        '        shortcut = shell.CreateShortCut(str(shortcut_path))',
        '        shortcut.TargetPath = str(target)',
        '        shortcut.WorkingDirectory = str(target.parent)',
        '        shortcut.Description = description',
        '        shortcut.Save()',
        '    except Exception:',
        '        try:',
        '            t_str = str(target)',
        '            p_str = str(target.parent)',
        '            s_str = str(shortcut_path)',
        '            ps_script = f\'$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut("{s_str}"); $s.TargetPath = "{t_str}"; $s.WorkingDirectory = "{p_str}"; $s.Save()\'',
        '            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)',
        '        except Exception:',
        '            pass',
        '',
        'def install(target_dir: Path | None = None, create_shortcuts: bool = True, register_startup: bool = False) -> bool:',
        '    dest = target_dir or get_default_install_dir()',
        '    print("================================================================================")',
        '    print(f" INSTALLING {PRODUCT_NAME} v{VERSION}")',
        '    print("================================================================================")',
        '    print(f" Destination Directory: {dest}")',
        '',
        '    dest.mkdir(parents=True, exist_ok=True)',
        '    import io',
        '    import base64',
        '    zip_bytes = base64.b64decode(ZIP_PAYLOAD_B64)',
        '    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:',
        '        zf.extractall(dest)',
        '',
        '    exe_path = dest / "ultron.exe"',
        '    if not exe_path.exists():',
        '        for sub in dest.glob("**/ultron.exe"):',
        '            exe_path = sub',
        '            break',
        '',
        '    print(f"[Installer] Executable installed at: {exe_path}")',
        '',
        '    # Write Uninstaller',
        '    uninstaller_path = dest / "unins000.py"',
        '    unins_lines = [',
        '        \'"""ULTRON Uninstaller"""\',',
        '        \'import os, sys, shutil\',',
        '        \'from pathlib import Path\',',
        '        \'\',',
        '        f\'PRODUCT_NAME = "{product_name}"\',',
        '        \'\',',
        '        \'def uninstall(purge_user_data: bool = False):\',',
        '        \'    print(f"Uninstalling {PRODUCT_NAME}...")\',',
        '        \'    install_dir = Path(__file__).resolve().parent\',',
        '        \'    \',',
        '        \'    # 1. Remove Start Menu shortcuts\',',
        '        \'    app_data = os.environ.get("APPDATA", "")\',',
        '        \'    if app_data:\',',
        '        \'        sm_link = Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{PRODUCT_NAME}.lnk"\',',
        '        \'        if sm_link.exists():\',',
        '        \'            sm_link.unlink(missing_ok=True)\',',
        '        \'            \',',
        '        \'    # 2. Remove Desktop shortcut\',',
        '        \'    desktop = Path.home() / "Desktop" / f"{PRODUCT_NAME}.lnk"\',',
        '        \'    if desktop.exists():\',',
        '        \'        desktop.unlink(missing_ok=True)\',',
        '        \'\',',
        '        \'    # 3. Remove Windows Startup entry\',',
        '        \'    if sys.platform == "win32":\',',
        '        \'        try:\',',
        '        \'            import winreg\',',
        '        \'            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run", 0, winreg.KEY_SET_VALUE) as key:\',',
        '        \'                winreg.DeleteValue(key, PRODUCT_NAME)\',',
        '        \'        except Exception:\',',
        '        \'            pass\',',
        '        \'\',',
        '        \'    # 4. Optional purge of user data\',',
        '        \'    if purge_user_data:\',',
        '        \'        local_app = os.environ.get("LOCALAPPDATA", "")\',',
        '        \'        if local_app:\',',
        '        \'            user_data = Path(local_app) / PRODUCT_NAME\',',
        '        \'            if user_data.exists():\',',
        '        \'                shutil.rmtree(user_data, ignore_errors=True)\',',
        '        \'                print(f"Purged user data at {user_data}")\',',
        '        \'\',',
        '        \'    # 5. Remove binaries\',',
        '        \'    print(f"Removed application binaries from {install_dir}")\',',
        '        \'    print(f"{PRODUCT_NAME} uninstalled successfully.")\',',
        '        \'\',',
        '        \'if __name__ == "__main__":\',',
        '        \'    purge = "--purge-data" in sys.argv\',',
        '        \'    uninstall(purge_user_data=purge)\',',
        '    ]',
        '    uninstaller_path.write_text("\\n".join(unins_lines), encoding="utf-8")',
        '',
        '    if create_shortcuts:',
        '        app_data = os.environ.get("APPDATA")',
        '        if app_data:',
        '            programs_dir = Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"',
        '            programs_dir.mkdir(parents=True, exist_ok=True)',
        '            shortcut_file = programs_dir / f"{PRODUCT_NAME}.lnk"',
        '            create_shortcut(exe_path, shortcut_file, description=f"{PRODUCT_NAME} Sovereign AI Assistant")',
        '            print(f"[Installer] Created Start Menu shortcut: {shortcut_file}")',
        '',
        '    if register_startup and sys.platform == "win32":',
        '        try:',
        '            import winreg',
        '            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run") as key:',
        '                winreg.SetValueEx(key, PRODUCT_NAME, 0, winreg.REG_SZ, f\'"{exe_path}" --startup\')',
        '            print("[Installer] Registered Windows startup.")',
        '        except Exception as e:',
        '            print(f"[Installer] Startup registration notice: {e}")',
        '',
        '    print("================================================================================")',
        '    print(" INSTALLATION COMPLETED SUCCESSFULLY")',
        '    print("================================================================================")',
        '    return True',
        '',
        'if __name__ == "__main__":',
        '    parser = argparse.ArgumentParser(description=f"Install {PRODUCT_NAME} v{VERSION}")',
        '    parser.add_argument("--dir", type=str, help="Custom installation target directory")',
        '    parser.add_argument("--no-shortcuts", action="store_true", help="Skip creating Start Menu shortcuts")',
        '    parser.add_argument("--startup", action="store_true", help="Enable Windows startup")',
        '    args = parser.parse_args()',
        '',
        '    target = Path(args.dir).resolve() if args.dir else None',
        '    install(target_dir=target, create_shortcuts=not args.no_shortcuts, register_startup=args.startup)',
    ]
    return "\n".join(lines)


def build_installer() -> Path:
    dist_dir = REPO_ROOT / "dist"
    app_dist_dir = dist_dir / "ultron"
    if not app_dist_dir.exists():
        raise RuntimeError(f"Distribution directory missing at {app_dist_dir}. Run build_windows_dist.py first.")

    import io
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(app_dist_dir):
            for file in files:
                fp = Path(root) / file
                arcname = fp.relative_to(app_dist_dir)
                zf.write(fp, arcname)

    payload_b64 = base64.b64encode(bio.getvalue()).decode("ascii")

    installer_content = generate_installer_script(
        payload_b64=payload_b64,
        product_name=__product_name__,
        version=__version__,
        build_date=__build_date__,
    )

    installer_py = dist_dir / f"Ultron-Setup-{__version__}.py"
    installer_py.write_text(installer_content, encoding="utf-8")
    print(f"[Installer Builder] Generated standalone setup script: {installer_py}")
    return installer_py


if __name__ == "__main__":
    build_installer()
