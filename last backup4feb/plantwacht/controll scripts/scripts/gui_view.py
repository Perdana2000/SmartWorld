import tkinter as tk

# --- ADDED: voor smileys ---
import os
from PIL import Image, ImageTk


def start_gui(controller):
    root = tk.Tk()
    root.title("plantwacht")
    root.geometry("520x360")

    # --- ADDED: smileys 1x laden (niet elke refresh) ---
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    def _load_smiley(filename, size=(90, 90)):
        path = os.path.join(assets_dir, filename)
        img = Image.open(path).convert("RGBA")
        img = img.resize(size)
        return ImageTk.PhotoImage(img)

    try:
        _SMILEYS = {
            "RED": _load_smiley("red_smiley.png"),
            "YELLOW": _load_smiley("yellow_smiley.png"),
            "GREEN": _load_smiley("green_smiley.png"),
        }
    except Exception as e:
        print("⚠️ Smiley images niet geladen:", e)
        _SMILEYS = None

    # zelfde thresholds als je LED-logica
    GREEN_FROM = 70
    YELLOW_FROM = 35

    def _moisture_state(p):
        """Return (state_name, color) op basis van %."""
        if p is None:
            return ("RED", "red")
        if p >= GREEN_FROM:
            return ("GREEN", "green")
        if p >= YELLOW_FROM:
            return ("YELLOW", "#c9a400")  # iets donkerder geel voor leesbaarheid
        return ("RED", "red")

    def clear():
        for w in root.winfo_children():
            w.destroy()

    def render():
        st = controller.get_state_copy()
                # UI sleep/wake
        if not st.get("ui_awake", True):
            try:
                root.withdraw()
            except Exception:
                pass
            return
        else:
            try:
                root.deiconify()
            except Exception:
                pass

        clear()

        # ---------------- MENU ----------------
        if st["screen"] == "menu":
            tk.Label(root, text="Smart Plant Menu", font=("Arial", 16)).pack(pady=18)

            tk.Button(
                root, text="Vochtmeting", font=("Arial", 14),
                width=16, height=2,
                command=lambda: controller.goto("moisture")
            ).pack(pady=10)

            tk.Button(
                root, text="Lichtmeting", font=("Arial", 14),
                width=16, height=2,
                command=lambda: controller.goto("light")
            ).pack(pady=10)

            tk.Button(
                root, text="Water geven", font=("Arial", 14),
                width=16, height=2,
                command=lambda: controller.goto("water")
            ).pack(pady=10)
            
            tk.Button(
                root, text="Dashboard", font=("Arial", 14),
                width=16, height=2,
                command=lambda: controller.goto("Dasboard")
            ).pack(pady=10)

        # ---------------- VOCHT ----------------
        elif st["screen"] == "moisture":
            tk.Label(root, text="Vochtmeting", font=("Arial", 22)).pack(pady=18)

            p = st.get("moisture_percent", None)
            raw = st.get("moisture_raw", "-")

            state, color = _moisture_state(p)

            # --- ADDED: smiley onder titel ---
            if _SMILEYS is not None:
                lbl_smiley = tk.Label(root, image=_SMILEYS[state])
                # reference bewaren zodat image niet "verdwijnt"
                lbl_smiley.image = _SMILEYS[state]
                lbl_smiley.pack(pady=4)

            # --- CHANGED: waarde label krijgt kleur (zelfde positie/pady als jij had) ---
            tk.Label(
                root, text=f"Waarde: {p if p is not None else '-'} %",
                font=("Arial", 18),
                fg=color
            ).pack(pady=8)

            tk.Label(
                root, text=f"Raw: {raw}",
                font=("Arial", 14)
            ).pack(pady=4)

            tk.Button(
                root, text="Vernieuw", font=("Arial", 16),
                command=controller.refresh_moisture
            ).pack(pady=8)

            tk.Button(
                root, text="← Terug", font=("Arial", 16),
                command=lambda: controller.goto("menu")
            ).pack(pady=18)

        # ---------------- LICHT ----------------
        elif st["screen"] == "light":
            tk.Label(root, text="Lichtmeting", font=("Arial", 22)).pack(pady=18)

            tk.Label(
                root, text=f"Waarde: {st.get('light', '-')}",
                font=("Arial", 18)
            ).pack(pady=16)

            tk.Button(
                root, text="Vernieuw", font=("Arial", 16),
                command=controller.refresh_light
            ).pack(pady=8)

            tk.Button(
                root, text="← Terug", font=("Arial", 16),
                command=lambda: controller.goto("menu")
            ).pack(pady=18)

        # ---------------- WATER (zoals gui_app.py) ----------------
        elif st["screen"] == "water":
            tk.Label(root, text="Water menu", font=("Arial", 22)).pack(pady=20)

            # status label (komt uit controller state)
            tk.Label(
                root, text=str(st.get("servo_text", "")),
                font=("Arial", 16)
            ).pack(pady=10)

            frame = tk.Frame(root)
            frame.pack(pady=20)

            tk.Button(
                frame,
                text="OPEN",
                font=("Arial", 16),
                bg="green",
                fg="white",
                width=12,
                height=3,
                command=controller.servo_open
            ).grid(row=0, column=0, padx=15)

            tk.Button(
                frame,
                text="DICHT",
                font=("Arial", 16),
                bg="red",
                fg="white",
                width=12,
                height=3,
                command=controller.servo_close
            ).grid(row=0, column=1, padx=15)

            tk.Button(
                root,
                text="← Terug",
                font=("Arial", 16),
                command=lambda: controller.goto("menu")
            ).pack(pady=30)

        else:
            tk.Label(root, text="Onbekend scherm", font=("Arial", 18)).pack(pady=20)
            tk.Button(root, text="← Terug", font=("Arial", 16),
                      command=lambda: controller.goto("menu")).pack(pady=18)

    # Controller -> GUI sync (altijd via Tk thread)
    def on_state_change():
        root.after(0, render)

    controller.add_observer(on_state_change)

    render()
    return root
