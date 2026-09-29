from app import main_window
from app.theme import STYLE

# Theme dipisahkan dari engine agar polishing UI tidak mengganggu fungsi window manager.
main_window.STYLE = STYLE

if __name__ == "__main__":
    raise SystemExit(main_window.run())
