import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random, threading, time, os, math, struct

# ========== SOUND (opcional; se falhar, desativa) ==========
SOUND_ENABLED = True
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()
except Exception:
    SOUND_ENABLED = False

def synth_tone(freq=440.0, ms=180, volume=0.5):
    if not SOUND_ENABLED:
        return None
    sr = 44100
    n = int(sr * (ms/1000.0))
    amp = int(32767 * max(0.0, min(1.0, volume)))
    buf = bytearray()
    for i in range(n):
        t = i / sr
        s = int(amp * math.sin(2*math.pi*freq*t))
        buf += struct.pack("<h", s)
    try:
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None

def play(s):
    if SOUND_ENABLED and s:
        try: s.play()
        except Exception: pass

SND_SWORD  = synth_tone(220, 120, 0.7)
SND_MAGIC1 = synth_tone(660, 140, 0.6)
SND_MAGIC2 = synth_tone(880, 120, 0.5)
SND_ARROW  = synth_tone(320, 100, 0.6)
SND_CRIT   = synth_tone(520, 220, 0.8)
SND_HEAL   = synth_tone(520, 80, 0.4)

# ========== UTILS ==========
def center_window(win, w, h):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

def find_image_path(basename):
    if os.path.exists(basename): return basename
    base = os.path.splitext(basename)[0]
    for ext in [".png",".jpg",".jpeg",".PNG",".JPG",".JPEG"]:
        p = base+ext
        if os.path.exists(p): return p
    for f in os.listdir("."):
        if f.lower().startswith(base.lower()) and os.path.isfile(f):
            return f
    return None

def load_or_placeholder(name, image_name, size=(220,220), color=(80,80,80)):
    path = find_image_path(image_name)
    if path:
        try:
            img = Image.open(path).convert("RGBA")
            try:
                resample = Image.Resampling.LANCZOS  # PIL>=10
            except AttributeError:
                resample = Image.LANCZOS
            return img.resize(size, resample)
        except Exception:
            pass
    # Placeholder
    img = Image.new("RGBA", size, (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.ellipse((8,8,size[0]-8,size[1]-8), fill=color)
    font = ImageFont.load_default()
    t = (name or "?")[0].upper()
    try:
        bbox = d.textbbox((0,0), t, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        tw = d.textlength(t, font=font)
        th = getattr(font, "size", 16)
    d.text(((size[0]-tw)//2,(size[1]-th)//2), t, fill="white", font=font)
    return img

def tint_image(pil_img, tint_color=(255,0,0,140)):
    over = Image.new("RGBA", pil_img.size, tint_color)
    return Image.alpha_composite(pil_img.convert("RGBA"), over)

# ========== MODEL ==========
class Character:
    def __init__(self, name, hp, attack, defense, image_name, color):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.image_name = image_name
        self.color = color
        self.image_pil = None
        self.image_tk = None
        self.moves = ["Basic Attack"]
        self.load_image()

    def load_image(self, size=(220,220)):
        img = load_or_placeholder(self.name, self.image_name, size=size, color=self.color)
        self.image_pil = img
        self.image_tk = ImageTk.PhotoImage(img)

    def attack_enemy(self, enemy, move=None):
        dmg = max(0, self.attack - enemy.defense + random.randint(-3,3))
        enemy.hp -= dmg
        return f"{self.name} attacks {enemy.name} for {dmg} damage!", dmg, "neutral"

class Warrior(Character):
    def __init__(self, name="Warrior", image_name="Imagem_Guerreiro"):
        super().__init__(name, 110, 26, 8, image_name, (40,100,200))
        self.moves = ["Sword Slash", "Shield Bash", "Dragon Rage"]

    def attack_enemy(self, enemy, move=None):
        move = move or random.choice(self.moves)
        crit = random.random() < 0.15
        base = self.attack + random.randint(-4,10)
        dmg = max(0, base - enemy.defense)
        if crit: dmg = int(dmg*1.5)
        enemy.hp -= dmg
        return f"⚔️ {self.name} used {move} and dealt {dmg}{' (CRIT!)' if crit else ''} damage!", dmg, ("crit" if crit else "physical")

class Mage(Character):
    def __init__(self, name="Mage", image_name="Imagem_Mago"):
        super().__init__(name, 95, 30, 6, image_name, (140,50,180))
        self.moves = ["Fireball", "Arcane Bolt", "Mystic Heal"]

    def attack_enemy(self, enemy, move=None):
        move = move or random.choice(self.moves)
        if move == "Mystic Heal":
            heal = random.randint(14, 26)
            self.hp = min(self.max_hp, self.hp + heal)
            return f"💚 {self.name} cast {move} and healed {heal} HP!", -heal, "heal"
        base = self.attack + random.randint(0,14)
        dmg = max(0, base - enemy.defense)
        enemy.hp -= dmg
        return f"🔥 {self.name} cast {move} and dealt {dmg} magic damage!", dmg, "magic"

class Archer(Character):
    def __init__(self, name="Archer", image_name="Imagem_Arqueiro"):
        super().__init__(name, 100, 24, 7, image_name, (60,160,100))
        self.moves = ["Quick Shot", "Piercing Arrow", "Volley"]

    def attack_enemy(self, enemy, move=None):
        move = move or random.choice(self.moves)
        def_penalty = enemy.defense if move != "Piercing Arrow" else max(0, enemy.defense - 4)
        base = self.attack + random.randint(-2,12)
        dmg = max(0, base - def_penalty)
        enemy.hp -= dmg
        return f"🏹 {self.name} used {move} and dealt {dmg} damage!", dmg, "arrow"

# ========== CONTROLLER / VIEW ==========
class BattleSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("⚔️ Battle Simulator – Final Edition (OOP)")
        center_window(self.root, 1000, 680)
        self.root.configure(bg="#141414")

        self.all_characters = [Warrior(), Mage(), Archer()]
        self.center_popup = None
        self.show_selection_screen()

    # ----- selection -----
    def show_selection_screen(self):
        self.clear_root()
        self.sel_frame = tk.Frame(self.root, bg="#141414")
        self.sel_frame.pack(expand=True, fill="both")

        tk.Label(self.sel_frame, text="Choose your character",
                 fg="white", bg="#141414", font=("Arial", 20, "bold")).pack(pady=20)

        grid = tk.Frame(self.sel_frame, bg="#141414"); grid.pack()
        for col, ch in enumerate(self.all_characters):
            card = tk.Frame(grid, bg="#1e1e1e"); card.grid(row=0, column=col, padx=20, pady=10)
            img = load_or_placeholder(ch.name, ch.image_name, size=(220,220), color=ch.color)
            img_tk = ImageTk.PhotoImage(img)
            setattr(self, f"_img_{col}", img_tk)  # evitar GC
            tk.Label(card, image=img_tk, bg="#1e1e1e").pack(padx=12, pady=12)
            tk.Label(card, text=ch.name, fg="white", bg="#1e1e1e",
                     font=("Arial", 14, "bold")).pack()
            tk.Label(card, text=f"HP:{ch.max_hp}  ATK:{ch.attack}  DEF:{ch.defense}",
                     fg="#cfcfcf", bg="#1e1e1e", font=("Consolas", 10)).pack(pady=(2,8))
            tk.Button(card, text="Select", bg="#2e8b57", fg="white",
                      command=lambda c=ch: self.start_battle_as(c)).pack(pady=10, ipadx=10, ipady=5)

    def start_battle_as(self, player_char):
        def clone(c):
            if isinstance(c, Warrior): return Warrior(c.name, c.image_name)
            if isinstance(c, Mage):    return Mage(c.name, c.image_name)
            if isinstance(c, Archer):  return Archer(c.name, c.image_name)
            return Character(c.name, c.max_hp, c.attack, c.defense, c.image_name, c.color)
        self.player = clone(player_char)
        self.enemy = clone(random.choice([x for x in self.all_characters if x.__class__ != player_char.__class__]))
        self.build_battle_ui()

    # ----- battle ui -----
    def build_battle_ui(self):
        self.clear_root()
        self.frame = tk.Frame(self.root, bg="#141414"); self.frame.pack(expand=True, fill="both")

        tk.Button(self.frame, text="← Back", command=self.show_selection_screen,
                  bg="#444", fg="white").place(x=20, y=12)
        tk.Button(self.frame, text="New Battle", command=self.reset_battle,
                  bg="#444", fg="white").place(x=120, y=12)

        self.lbl_name_p = tk.Label(self.frame, text=self.player.name, fg="white", bg="#141414", font=("Arial", 14, "bold"))
        self.lbl_name_p.place(x=120, y=60)
        self.lbl_name_e = tk.Label(self.frame, text=self.enemy.name,  fg="white", bg="#141414", font=("Arial", 14, "bold"))
        self.lbl_name_e.place(x=700, y=60)

        # HP bars
        self.hp_canvas_p = tk.Canvas(self.frame, width=260, height=20, bg="#222", highlightthickness=0)
        self.hp_canvas_e = tk.Canvas(self.frame, width=260, height=20, bg="#222", highlightthickness=0)
        self.hp_canvas_p.place(x=120, y=90); self.hp_canvas_e.place(x=700, y=90)
        self.hp_fill_p = self.hp_canvas_p.create_rectangle(0,0,260,20, fill="#2ecc71", width=0)
        self.hp_fill_e = self.hp_canvas_e.create_rectangle(0,0,260,20, fill="#2ecc71", width=0)
        self.hp_text_p = self.hp_canvas_p.create_text(130,10, text="", fill="white", font=("Consolas", 10))
        self.hp_text_e = self.hp_canvas_e.create_text(130,10, text="", fill="white", font=("Consolas", 10))
        self.update_hp_bars(animated=False)

        # images (refs persistentes)
        self.lbl_player = tk.Label(self.frame, image=self.player.image_tk, bg="#141414")
        self.lbl_player.place(x=100, y=170)
        self.player_show_pil = self.player.image_pil
        self.player_show_tk  = self.player.image_tk
        self.lbl_player._img_ref = self.player_show_tk

        self.set_enemy_image_label()

        # moves
        self.buttons = []
        for i, mv in enumerate(self.player.moves):
            b = tk.Button(self.frame, text=mv, font=("Consolas", 12, "bold"),
                          bg="#2e8b57", fg="white",
                          command=lambda m=mv: threading.Thread(target=self.turn, args=(m,)).start())
            b.place(x=120 + i*280, y=420, width=260, height=44)
            self.buttons.append(b)

        # log
        self.log = tk.Text(self.frame, width=118, height=8, bg="#1f1f1f", fg="white", font=("Consolas", 10))
        self.log.place(x=40, y=520)
        self.log.insert("end", f"🔥 {self.player.name} vs {self.enemy.name}! Choose a move.\n")

    def set_enemy_image_label(self):
        self.enemy_show_pil = self.enemy.image_pil.transpose(Image.FLIP_LEFT_RIGHT)
        self.enemy_show_tk  = ImageTk.PhotoImage(self.enemy_show_pil)
        self.lbl_enemy = tk.Label(self.frame, image=self.enemy_show_tk, bg="#141414")
        self.lbl_enemy.place(x=680, y=170)
        self.lbl_enemy._img_ref = self.enemy_show_tk

    # ----- popup central -----
    def clear_center_popup(self):
        if getattr(self, "center_popup", None) is not None:
            try: self.center_popup.destroy()
            except Exception: pass
            self.center_popup = None

    def show_center_popup(self, text, color="#ffcccc"):
        self.clear_center_popup()
        self.center_popup = tk.Label(self.frame, text=text, fg=color, bg="#141414", font=("Arial", 20, "bold"))
        self.center_popup.place(relx=0.5, rely=0.35, anchor="center")

    # ----- effects -----
    def tint_flash_on_label(self, label, base_pil, base_tk, color=(255,0,0,120), duration=0.12):
        tinted = tint_image(base_pil, color)
        tinted_tk = ImageTk.PhotoImage(tinted)
        label.configure(image=tinted_tk); label._img_ref = tinted_tk
        self.root.update(); time.sleep(duration)
        label.configure(image=base_tk); label._img_ref = base_tk
        self.root.update()

    # ----- hp bars -----
    def update_hp_bars(self, animated=True):
        def bar(cnv, rect, txt, hp, max_hp):
            pct = max(0.0, min(1.0, hp/max_hp))
            width = int(260 * pct)
            color = "#2ecc71" if pct>0.6 else ("#f1c40f" if pct>0.3 else "#e74c3c")
            if not animated:
                cnv.coords(rect, 0,0, width,20); cnv.itemconfig(rect, fill=color)
            else:
                cur = cnv.coords(rect)[2]
                for s in range(12):
                    x = int(cur + (width-cur)*(s+1)/12)
                    cnv.coords(rect, 0,0, x,20); cnv.itemconfig(rect, fill=color)
                    self.root.update(); time.sleep(0.02)
            cnv.itemconfig(txt, text=f"{max(0,int(hp))}/{max_hp}")
        bar(self.hp_canvas_p, self.hp_fill_p, self.hp_text_p, self.player.hp, self.player.max_hp)
        bar(self.hp_canvas_e, self.hp_fill_e, self.hp_text_e, self.enemy.hp, self.enemy.max_hp)

    # ----- turn -----
    def turn(self, move_name):
        self.disable_buttons()
        self.clear_center_popup()

        # Player
        txt, dmg, kind = self.player.attack_enemy(self.enemy, move_name)
        self.log.insert("end", txt+"\n"); self.log.see("end")

        if   kind == "crit":    play(SND_CRIT)
        elif kind == "physical": play(SND_SWORD)
        elif kind == "magic":    play(SND_MAGIC1)
        elif kind == "arrow":    play(SND_ARROW)
        elif kind == "heal":     play(SND_HEAL)

        if kind == "heal":
            self.show_center_popup(f"+{abs(dmg)}", "#77ff77")
        else:
            if dmg > 0:
                self.tint_flash_on_label(self.lbl_enemy, self.enemy_show_pil, self.enemy_show_tk)
                self.show_center_popup(f"-{dmg}", "#ffcccc")

        self.dash(self.lbl_player, 60); self.shake(self.lbl_enemy, 10)
        self.update_hp_bars()

        if self.enemy.hp <= 0:
            self.finish_battle(self.player); self.clear_center_popup(); return

        time.sleep(1.0); self.clear_center_popup()

        # Enemy
        txt2, dmg2, kind2 = self.enemy.attack_enemy(self.player)
        self.log.insert("end", txt2+"\n"); self.log.see("end")

        if   kind2 == "crit":    play(SND_CRIT)
        elif kind2 == "physical": play(SND_SWORD)
        elif kind2 == "magic":    play(SND_MAGIC1); time.sleep(0.05); play(SND_MAGIC2)
        elif kind2 == "arrow":    play(SND_ARROW)
        elif kind2 == "heal":     play(SND_HEAL)

        if kind2 == "heal":
            self.show_center_popup(f"+{abs(dmg2)}", "#77ff77")
        else:
            if dmg2 > 0:
                self.tint_flash_on_label(self.lbl_player, self.player_show_pil, self.player_show_tk)
                self.show_center_popup(f"-{dmg2}", "#ffcccc")

        self.dash(self.lbl_enemy, -60); self.shake(self.lbl_player, 10)
        self.update_hp_bars()

        if self.player.hp <= 0:
            self.finish_battle(self.enemy); self.clear_center_popup(); return

        self.enable_buttons()

    # ----- winner (sem enfeites) -----
    def show_winner_screen(self, winner_obj):
        self.clear_root()
        frame = tk.Frame(self.root, bg="#141414"); frame.pack(expand=True, fill="both")

        title = tk.Label(frame, text=f"{winner_obj.name} won",
                         fg="white", bg="#141414", font=("Arial", 26, "bold"))
        title.pack(pady=28)

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img_big = winner_obj.image_pil.resize((300,300), resample)
        img_big_tk = ImageTk.PhotoImage(img_big)
        img_lbl = tk.Label(frame, image=img_big_tk, bg="#141414")
        img_lbl.image = img_big_tk
        img_lbl.pack(pady=10)

        btns = tk.Frame(frame, bg="#141414"); btns.pack(pady=24)
        tk.Button(btns, text="New Battle", bg="#2e8b57", fg="white",
                  command=self.show_selection_screen, width=14, height=2).grid(row=0, column=0, padx=8)
        tk.Button(btns, text="Exit", bg="#444", fg="white",
                  command=self.root.destroy, width=10, height=2).grid(row=0, column=1, padx=8)

        # salva log (best-effort)
        try:
            with open("battle_log.txt", "w", encoding="utf-8") as f:
                f.write(getattr(self, "log", tk.Text()).get("1.0", "end"))
        except Exception:
            pass

    # ----- helpers -----
    def shake(self, label, distance=10, times=6, delay=0.03):
        ox, oy = label.winfo_x(), label.winfo_y()
        for i in range(times):
            dx = distance if i%2==0 else -distance
            label.place(x=ox+dx, y=oy); self.root.update(); time.sleep(delay)
        label.place(x=ox, y=oy)

    def dash(self, label, distance=60, speed=0.03):
        x, y = label.winfo_x(), label.winfo_y()
        for i in range(5):
            label.place(x=x + distance//5*(i+1), y=y); self.root.update(); time.sleep(speed)
        for i in range(5):
            label.place(x=x + distance - distance//5*(i+1), y=y); self.root.update(); time.sleep(speed)
        label.place(x=x, y=y)

    def disable_buttons(self, final=False):
        for b in getattr(self, "buttons", []):
            b.config(state="disabled")
            if final: b.config(text="🏁 Battle Over", bg="#555")

    def enable_buttons(self):
        for b in getattr(self, "buttons", []):
            b.config(state="normal")

    def reset_battle(self):
        self.player.hp = self.player.max_hp
        self.enemy.hp = self.enemy.max_hp
        self.log.delete("1.0", "end")
        self.log.insert("end", f"🔄 New battle started: {self.player.name} vs {self.enemy.name}!\n")
        self.update_hp_bars(animated=False)
        self.clear_center_popup()
        self.enable_buttons()

    def finish_battle(self, winner_obj):
        self.show_winner_screen(winner_obj)

    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()

# ========== MAIN ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = BattleSimulator(root)
    root.mainloop()
