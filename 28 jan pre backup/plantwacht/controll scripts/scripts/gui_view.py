import tkinter as tk

def start_gui(controller):
    root = tk.Tk()
    root.title("plantwacht")
    root.geometry("520x360")

    def clear():
        for w in root.winfo_children():
            w.destroy()

    def render():
        st = controller.get_state_copy()
        clear()

        # ---------------- MENU ----------------
        if st["screen"] == "menu":
            tk.Label(root, text="Smart Plant Menu", font=("Arial", 22)).pack(pady=18)

            tk.Button(
                root, text="Vochtmeting", font=("Arial", 18),
                width=18, height=2,
                command=lambda: controller.goto("moisture")
            ).pack(pady=10)

            tk.Button(
                root, text="Lichtmeting", font=("Arial", 18),
                width=18, height=2,
                command=lambda: controller.goto("light")
            ).pack(pady=10)

            tk.Button(
                root, text="Water geven", font=("Arial", 18),
                width=18, height=2,
                command=lambda: controller.goto("water")
            ).pack(pady=10)

        # ---------------- VOCHT ----------------
        elif st["screen"] == "moisture":
            tk.Label(root, text="Vochtmeting", font=("Arial", 22)).pack(pady=18)

            tk.Label(
                root, text=f"Waarde: {st.get('moisture_percent', '-') } %",
                font=("Arial", 18)
            ).pack(pady=8)

            tk.Label(
                root, text=f"Raw: {st.get('moisture_raw', '-')}",
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
