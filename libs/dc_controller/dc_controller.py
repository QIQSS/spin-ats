import tkinter as tk
from tkinter import ttk
import pyperclip
import os
import json
import threading


def load_voltages(filename):
    """
    Charge et retourne le dictionnaire de tensions défini dans le fichier passé en argument
    """
    with open(filename, "r") as f:
        lines = f.readlines()
        lines[0] = "{"
        return json.loads("".join(lines))

def save_voltages(voltages_dict, filename):
    """
    Enregistre un dictionnaire de tensions dans un fichier.
    """
    with open(filename, "w") as f:
        f.write("voltages = ")
        f.write(json.dumps(voltages_dict, indent="\t"))

class DCControllerItem:
    """
    Classe qui permet de faciliter la gestion des grilles à controler avec 
    """
    def __init__(self, gates_dict, name, frame, update_func):
        self.gates_dict = gates_dict
        self.name = name
        self.increment = 1e-3
        self.update_func = update_func
        self.resolution = 4  # Nombre de chiffres après la virgule sur les tensions

        self.name_label = tk.Label(frame, text=self.name)
        self.minus_btn = tk.Button(frame, text="-", command=lambda: self.increment_value(positive=False))
        self.plus_btn = tk.Button(frame, text="+", command=lambda: self.increment_value(positive=True))

        self.increment_entry = tk.Entry(frame, width=10)
        self.increment_entry.insert(0, str(self.increment))
        self.increment_entry.bind("<Return>", lambda event: self.set_increment())

        self.value_entry = tk.Entry(frame, width=10)
        self.value_entry.insert(0, str(round(self.gates_dict[self.name], self.resolution)))
        self.value_entry.bind("<Return>", lambda event: self.set_value(float(self.value_entry.get())))

    def increment_value(self, positive=True):
        if positive:
            self.set_value(self.gates_dict[self.name] + self.increment)
        else:
            self.set_value(self.gates_dict[self.name] - self.increment)
    
    def set_increment(self):
        try:
            self.increment = float(self.increment_entry.get())
        except ValueError:
            pass
    
    def set_value(self, value):
        self.gates_dict[self.name] = value
        self.value_entry.delete(0, tk.END)
        self.value_entry.insert(0, str(round(value, self.resolution)))
        self.update_func(self.gates_dict)


def dc_controller(voltages_file, update_func, add_gates:list[str]=[]):
    gates_dict = load_voltages(voltages_file)
    def add_controller(gate_name):
        if gate_name == "":
            return
        
        for ctrl in controllers:
            if ctrl.name == gate_name:
                return
        
        ctrl = DCControllerItem(gates_dict, gate_name, frame_controllers, update_func)
        controllers.append(ctrl)

        ctrl.name_label.grid(row=len(controllers), column=0, padx=5, pady=2)
        ctrl.minus_btn.grid(row=len(controllers), column=1, padx=5, pady=2)
        ctrl.plus_btn.grid(row=len(controllers), column=2, padx=5, pady=2)
        ctrl.increment_entry.grid(row=len(controllers), column=3, padx=5, pady=2)
        ctrl.value_entry.grid(row=len(controllers), column=4, padx=5, pady=2)

    
    def copy_all_gates_dict():
        str_dict = str(gates_dict).replace("{", "{\n\t").replace(", ", ",\n\t").replace("}", "\n}").replace("'", "\"")
        pyperclip.copy(str_dict)

    def copy_shown_gates_dict():
        shown_dict = {ctr.name: gates_dict[ctr.name] for ctr in controllers}
        str_dict = str(shown_dict).replace("{", "{\n\t").replace(", ", ",\n\t").replace("}", "\n}").replace("'", "\"")
        pyperclip.copy(str_dict)


    root = tk.Tk()
    root.title("DC Controller")

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "icone_video.ico")
        root.iconbitmap(icon_path)
    except:
        pass

    controllers = list()

    # Définition des frames
    frame_title = tk.Frame(root)
    frame_title.grid(row=0, column=0, padx=10, pady=5)

    frame_setup = tk.Frame(root)
    frame_setup.grid(row=1, column=0, padx=10, pady=5)

    frame_controllers = tk.Frame(root)
    frame_controllers.grid(row=2, column=0, padx=10, pady=5)
    
    # Frame des titres
    title_label = tk.Label(frame_title, text="DC Controller", font=("Arial", 20))
    title_label.grid(row=0, column=0, pady=0)

    fname_label = tk.Label(frame_title, text=f"Voltages from:\n{voltages_file}", justify=tk.LEFT, wraplength=350)
    fname_label.grid(row=1, column=0, pady=5)

    # Frame de configuration
    gate_list = ttk.Combobox(frame_setup, values=list(gates_dict.keys()))
    gate_list.grid(row=0, column=0, padx=5)

    add_button = tk.Button(frame_setup, text="Add Gate", command=lambda: add_controller(gate_list.get()), width=15)
    add_button.grid(row=1, column=0, padx=5)

    cpy_all_btn = tk.Button(frame_setup, text="Copy Full Voltages Dict", command=copy_all_gates_dict, width=22)
    cpy_all_btn.grid(row=0, column=1, padx=5)

    cpy_shown_btn = tk.Button(frame_setup, text="Copy Shown Voltages Dict", command=copy_shown_gates_dict, width=22)
    cpy_shown_btn.grid(row=1, column=1, padx=5)

    save_btn = tk.Button(frame_setup, text="Save Voltages Dict to File", command=lambda: save_voltages(gates_dict, voltages_file), width=22)
    save_btn.grid(row=2, column=1, padx=5)

    # Frame des contrôleurs
    gate_name_label = tk.Label(frame_controllers, text="Gate Name")
    gate_name_label.grid(row=0, column=0, padx=5)
    increment_label = tk.Label(frame_controllers, text="Increment")
    increment_label.grid(row=0, column=3, padx=5)
    value_label = tk.Label(frame_controllers, text="Voltage (V)")
    value_label.grid(row=0, column=4, padx=5)

    # Ajout des gates:
    for gate_str in add_gates:
        if not gate_str in list(gates_dict.keys()):
            print(f"no gate '{gate_str}'")
            continue
        add_controller(gate_str)
        

    root.mainloop()

def dc_controller_in_thread(*args, **kwargs):
    thr = threading.Thread(target=dc_controller, args=args, kwargs=kwargs)
    thr.start()
    return thr


if __name__ == "__main__":
    fname = r"C:\Data\Intel Tunnel Fall\Code\Intel_tunnel_fall_12qd01_2026-03-30\parameters\dc_voltage_dicts\dc_tuning.py"

    def dummy_func(voltage_dict):
        print(voltage_dict)

    # thr = dc_controller(fname, dummy_func, ["P1", "P2_2"])
    thr = dc_controller_in_thread(fname, dummy_func, ["P1", "P2_2"])
