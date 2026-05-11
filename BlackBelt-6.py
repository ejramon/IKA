import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import os
import hashlib

# ── PostgreSQL ───────────────────────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False
try:
    from tkcalendar import DateEntry as _TkCalDateEntry
    _TKCAL_OK = True
except ImportError:
    _TKCAL_OK = False

# ── DateEntry nativo: 3 campos Día / Mes / Año ──────────────────────────────
class DateEntry(tk.Frame):
    """Selector de fecha con campos separados Día/Mes/Año. Sin tkcalendar."""
    def __init__(self, parent, width=14, date_pattern="dd/mm/yyyy",
                 background=None, foreground=None, borderwidth=0, font=None, **kw):
        bg = "#FFFFFF"   # se sobreescribe cuando COLORES ya existe
        try: bg = COLORES.get("fondo", "#FFFFFF")
        except: pass
        super().__init__(parent, bg=bg)
        _f  = font or ("Segoe UI", 10)
        _fs = ("Segoe UI", 7)
        _fg = "#7A6F68"
        try: _fg = COLORES.get("texto_suave", "#7A6F68")
        except: pass

        # Etiquetas
        tk.Label(self, text="Día",  font=_fs, fg=_fg, bg=bg).grid(row=0, column=0, padx=(0,2))
        tk.Label(self, text="Mes",  font=_fs, fg=_fg, bg=bg).grid(row=0, column=2, padx=4)
        tk.Label(self, text="Año",  font=_fs, fg=_fg, bg=bg).grid(row=0, column=4, padx=(4,0))

        # Separadores
        tk.Label(self, text="/", font=_f, bg=bg).grid(row=1, column=1)
        tk.Label(self, text="/", font=_f, bg=bg).grid(row=1, column=3)

        # Campos
        self._dia  = ttk.Entry(self, width=3,  font=_f, justify="center")
        self._mes  = ttk.Entry(self, width=3,  font=_f, justify="center")
        self._anio = ttk.Entry(self, width=5,  font=_f, justify="center")
        self._dia .grid(row=1, column=0, padx=(0,2))
        self._mes .grid(row=1, column=2, padx=4)
        self._anio.grid(row=1, column=4, padx=(4,0))

        # Valor inicial = hoy
        hoy = datetime.today()
        self._dia .insert(0, f"{hoy.day:02d}")
        self._mes .insert(0, f"{hoy.month:02d}")
        self._anio.insert(0, str(hoy.year))

        # Avance automático al escribir
        self._dia .bind("<KeyRelease>", lambda e: self._avanzar(self._dia,  2, self._mes))
        self._mes .bind("<KeyRelease>", lambda e: self._avanzar(self._mes,  2, self._anio))

    def _avanzar(self, campo, maxlen, siguiente):
        if len(campo.get()) >= maxlen:
            siguiente.focus_set()
            siguiente.select_range(0, "end")

    def _limpiar(self, val):
        """Retorna solo dígitos."""
        return "".join(c for c in val if c.isdigit())

    def get(self):
        d = self._limpiar(self._dia .get()).zfill(2)
        m = self._limpiar(self._mes .get()).zfill(2)
        a = self._limpiar(self._anio.get()).zfill(4)
        try:
            datetime.strptime(f"{d}/{m}/{a}", "%d/%m/%Y")
            return f"{d}/{m}/{a}"
        except ValueError:
            hoy = datetime.today()
            return hoy.strftime("%d/%m/%Y")

    def set_date(self, date_obj):
        if hasattr(date_obj, "day"):
            d, m, a = date_obj.day, date_obj.month, date_obj.year
        else:
            try:
                dt = datetime.strptime(str(date_obj), "%d/%m/%Y")
                d, m, a = dt.day, dt.month, dt.year
            except:
                hoy = datetime.today(); d, m, a = hoy.day, hoy.month, hoy.year
        for campo, val in ((self._dia, f"{d:02d}"), (self._mes, f"{m:02d}"), (self._anio, str(a))):
            campo.delete(0, "end")
            campo.insert(0, val)
from datetime import datetime
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_OK = True
except ImportError:
    EXCEL_OK = False

# --- TEMAS DE COLOR ---
TEMAS = {
    "Estándar": {
        "fondo":        "#FFFFFE",
        "superficie":   "#EDEAE4",
        "superficie2":  "#E2DED7",
        "primario":     "#41141B",
        "primario_dark":"#5C1A27",
        "acento":       "#9B743D",
        "texto":        "#2C2420",
        "texto_suave":  "#7A6F68",
        "borde":        "#D0C9C0",
        "exito":        "#2C684A",
        "peligro":      "#A63228",
        "blanco":       "#FFFFFF",
    },
    "Deportivo": {
        "fondo":        "#0D1117",
        "superficie":   "#161B22",
        "superficie2":  "#21262D",
        "primario":     "#4E0D0D",
        "primario_dark":"#C1121F",
        "acento":       "#FFD60A",
        "texto":        "#F0F6FC",
        "texto_suave":  "#8B949E",
        "borde":        "#30363D",
        "exito":        "#2EA043",
        "peligro":      "#F85149",
        "blanco":       "#FFFFFF",
    },
    "Sobrio": {
        "fondo":        "#F8F9FA",
        "superficie":   "#EAECEF",
        "superficie2":  "#DDE1E7",
        "primario":     "#1A1A2E",
        "primario_dark":"#0D0D1A",
        "acento":       "#457B9D",
        "texto":        "#212529",
        "texto_suave":  "#6C757D",
        "borde":        "#CED4DA",
        "exito":        "#2D6A4F",
        "peligro":      "#9B2226",
        "blanco":       "#FFFFFF",
    },
    "Elegante": {
        "fondo":        "#1C1C1E",
        "superficie":   "#737377",
        "superficie2":  "#3A3A3C",
        "primario":     "#32280B",
        "primario_dark":"#A28A5E",
        "acento":       "#D4AF70",
        "texto":        "#F5F5F0",
        "texto_suave":  "#9A9A8A",
        "borde":        "#48484A",
        "exito":        "#32D74B",
        "peligro":      "#FF453A",
        "blanco":       "#FFFFFF",
    },
}

# Configuración persistente
import json, os, sys

# ── Carpeta de datos del usuario (Mac: ~/Documents/BlackBelt/) ──────────────
_DOCS = os.path.join(os.path.expanduser("~"), "Documents", "BlackBelt")
os.makedirs(_DOCS, exist_ok=True)          # la crea si no existe, sin error si ya existe

CONFIG_FILE  = os.path.join(_DOCS, "club_config.json")

# ── Pools de conexión PostgreSQL ─────────────────────────────────────────────
# Se inicializan en conectar_db() la primera vez que se llama.
# Usan las credenciales guardadas en club_config.json bajo la clave "postgres".
_pool_miembros = None
_pool_chat     = None

def _get_pg_config():
    """Devuelve el dict con credenciales PG o None si no están configuradas."""
    cfg = cargar_config()
    return cfg.get("postgres", None)

def _hacer_pool(db_key):
    """
    Crea un SimpleConnectionPool para la BD indicada (db_key = 'miembros' o 'chat').
    Usa los datos guardados en club_config.json > postgres > miembros / chat.
    """
    pg = _get_pg_config()
    if not pg:
        return None
    creds = pg.get(db_key, {})
    if not creds.get("url"):
        return None
    try:
        pool = psycopg2.pool.SimpleConnectionPool(
            1, 5,
            creds["url"],
            connect_timeout=10
        )
        return pool
    except Exception as e:
        print(f"[BlackBelt] Error pool {db_key}: {e}")
        return None

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "tema": "Estándar", "password": "", "font_scale": 1.0,
        "admin_nombre": "", "admin_apellido": "",
        "postgres": {
            "miembros": {"url": ""},
            "chat":     {"url": ""}
        }
    }

def guardar_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

_config = cargar_config()

# --- PALETA IKA ECUADOR ---
COLORES = dict(TEMAS[_config.get("tema", "Estándar")])

def _calcular_fuentes(escala=1.0):
    def s(n): return max(7, round(n * escala))
    return {
        "mega":      ("Georgia",     s(22), "bold"),
        "titulo":    ("Georgia",     s(16), "bold"),
        "subtitulo": ("Georgia",     s(13), "bold"),
        "normal":    ("Segoe UI",    s(12)),
        "small":     ("Segoe UI",    s(10)),
        "bold":      ("Segoe UI",    s(12), "bold"),
        "mono":      ("Courier New",),
    }

FUENTES = _calcular_fuentes(_config.get("font_scale", 1.0))

# ─── ESTILO GLOBAL TTK ──────────────────────────────────────────────────────
def aplicar_tema():
    style = ttk.Style()
    style.theme_use("clam")

    # Tamaños escalados (todos los estilos TTK usan la escala guardada)
    _f = FUENTES  # ya viene calculado con la escala correcta
    _fs = _config.get("font_scale", 1.0)
    def _sz(n): return max(7, round(n * _fs))

    # Botones principales
    style.configure("IKA.TButton",
        font=("Segoe UI", _sz(10), "bold"),
        background=COLORES["primario"],
        foreground=COLORES["blanco"],
        borderwidth=0,
        relief="flat",
        padding=(14, 8),
        focusthickness=0,
    )
    style.map("IKA.TButton",
        background=[("active", COLORES["primario_dark"]), ("pressed", "#600818")],
        foreground=[("active", COLORES["acento"])],
    )

    # Botones secundarios (dorado)
    style.configure("Gold.TButton",
        font=("Segoe UI", _sz(9), "bold"),
        background=COLORES["acento"],
        foreground="#0D0D0D",
        borderwidth=0,
        relief="flat",
        padding=(10, 6),
        focusthickness=0,
    )
    style.map("Gold.TButton",
        background=[("active", "#E6C200"), ("pressed", "#BFA000")],
    )

    # Botón peligro
    style.configure("Danger.TButton",
        font=("Segoe UI", _sz(9), "bold"),
        background=COLORES["peligro"],
        foreground=COLORES["blanco"],
        borderwidth=0,
        relief="flat",
        padding=(10, 6),
        focusthickness=0,
    )
    style.map("Danger.TButton",
        background=[("active", "#C0392B")],
    )

    # Entry
    style.configure("TEntry",
        fieldbackground=COLORES["superficie2"],
        foreground=COLORES["texto"],
        insertcolor=COLORES["acento"],
        borderwidth=1,
        relief="flat",
        padding=6,
        font=("Segoe UI", _sz(11)),
    )

    # Combobox
    style.configure("TCombobox",
        fieldbackground=COLORES["superficie2"],
        background=COLORES["superficie2"],
        foreground=COLORES["texto"],
        selectbackground=COLORES["primario"],
        selectforeground=COLORES["blanco"],
        borderwidth=1,
        relief="flat",
        padding=6,
        font=("Segoe UI", _sz(11)),
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", COLORES["superficie2"])],
        foreground=[("readonly", COLORES["texto"])],
    )

    # Treeview
    style.configure("IKA.Treeview",
        background=COLORES["superficie"],
        fieldbackground=COLORES["superficie"],
        foreground=COLORES["texto"],
        rowheight=max(22, round(28 * _fs)),
        borderwidth=0,
        font=("Segoe UI", _sz(9)),
    )
    style.configure("IKA.Treeview.Heading",
        background=COLORES["primario"],
        foreground=COLORES["blanco"],
        font=("Segoe UI", _sz(9), "bold"),
        relief="flat",
        padding=(8, 6),
    )
    style.map("IKA.Treeview",
        background=[("selected", COLORES["primario"])],
        foreground=[("selected", COLORES["blanco"])],
    )
    style.map("IKA.Treeview.Heading",
        background=[("active", COLORES["primario_dark"])],
    )

    # Scrollbar
    style.configure("TScrollbar",
        background=COLORES["superficie2"],
        troughcolor=COLORES["superficie"],
        borderwidth=0,
        arrowcolor=COLORES["texto_suave"],
    )

    # LabelFrame
    style.configure("IKA.TLabelframe",
        background=COLORES["superficie"],
        foreground=COLORES["acento"],
        bordercolor=COLORES["borde"],
        relief="flat",
    )
    style.configure("IKA.TLabelframe.Label",
        background=COLORES["superficie"],
        foreground=COLORES["acento"],
        font=("Segoe UI", _sz(9), "bold"),
    )


def _hash_cedula(cedula):
    """Genera el password_hash inicial a partir de la cédula."""
    return hashlib.sha256(cedula.encode()).hexdigest()

def _parsear_fecha(texto):
    """
    Convierte strings de fecha a objeto date de Python.
    Acepta: 'dd/mm/yyyy', 'yyyy-mm-dd', 'yyyy-mm-dd HH:MM:SS'
    Devuelve None si no puede parsear.
    """
    if not texto or str(texto).strip() in ("", "None"):
        return None
    s = str(texto).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _fmt_fecha(valor):
    """
    Convierte un valor de fecha de PostgreSQL (date, datetime, str) a 'dd/mm/yyyy'
    para mostrar en la interfaz. Devuelve '—' si es None o vacío.
    """
    if valor is None or str(valor).strip() in ("", "None"):
        return "—"
    from datetime import date, datetime as _ddt
    if isinstance(valor, (date, _ddt)):
        return valor.strftime("%d/%m/%Y")
    s = str(valor).strip()
    # ya viene formateado
    if "/" in s and len(s) == 10:
        return s
    # viene como yyyy-mm-dd
    try:
        return _ddt.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return s

def conectar_db():
    """
    Devuelve una conexión al pool de club_miembros.
    Si el pool no existe aún lo inicializa.
    Si las credenciales no están configuradas muestra aviso y devuelve None.
    """
    global _pool_miembros
    if not PSYCOPG2_OK:
        messagebox.showerror("Dependencia faltante",
            "psycopg2 no está instalado.\n\nEjecutá: pip install psycopg2-binary")
        return None
    if _pool_miembros is None:
        _pool_miembros = _hacer_pool("miembros")
    if _pool_miembros is None:
        messagebox.showwarning("Sin conexión",
            "No hay credenciales de PostgreSQL configuradas.\n"
            "Ingresá las credenciales en Configuración → PostgreSQL.")
        return None
    try:
        conn = _pool_miembros.getconn()
        conn.autocommit = False
        return conn
    except Exception as e:
        messagebox.showerror("Error de conexión", f"No se pudo conectar a club_miembros:\n{e}")
        return None

def liberar_db(conn):
    """Devuelve la conexión al pool de miembros."""
    global _pool_miembros
    if conn and _pool_miembros:
        try:
            _pool_miembros.putconn(conn)
        except:
            pass

def conectar_chat_db():
    """
    Devuelve una conexión al pool de club_chat.
    """
    global _pool_chat
    if not PSYCOPG2_OK:
        return None
    if _pool_chat is None:
        _pool_chat = _hacer_pool("chat")
    if _pool_chat is None:
        return None
    try:
        conn = _pool_chat.getconn()
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"[BlackBelt] Error chat conn: {e}")
        return None

def liberar_chat(conn):
    """Devuelve la conexión al pool de chat."""
    global _pool_chat
    if conn and _pool_chat:
        try:
            _pool_chat.putconn(conn)
        except:
            pass

# ══════════════════════════════════════════════════════════════════════════
# CACHÉ LOCAL EN RAM
# Al arrancar BlackBelt se descarga toda la BD en memoria.
# Las lecturas van contra la caché — instantáneo, sin latencia de Railway.
# Las escrituras van a Railway y luego refrescan la caché.
# ══════════════════════════════════════════════════════════════════════════
_cache = {
    "miembros":    [],   # lista de tuplas SELECT * FROM miembros
    "categorias":  [],   # lista de strings
    "eventos":     [],   # lista de tuplas (id, nombre, fecha, descripcion)
    "participantes": {}, # dict evento_id → set de socio_ids
    "cargado":     False
}

def _cargar_cache():
    """Descarga toda la BD en _cache. Se llama al arrancar y después de cada escritura."""
    global _cache
    conn = conectar_db()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, nombres, apellidos, cedula, categoria,
            ciudad_nacimiento, fecha_nacimiento, telefono, direccion, correo, fecha_ingreso, genero
            FROM miembros ORDER BY apellidos, nombres""")
        _cache["miembros"] = cur.fetchall()
        cur.execute("SELECT nombre FROM categorias ORDER BY nombre")
        _cache["categorias"] = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id, nombre, fecha, descripcion FROM eventos ORDER BY id DESC")
        _cache["eventos"] = cur.fetchall()
        cur.execute("SELECT evento_id, socio_id FROM evento_participantes")
        _cache["participantes"] = {}
        for ev_id, soc_id in cur.fetchall():
            _cache["participantes"].setdefault(ev_id, set()).add(soc_id)
        _cache["cargado"] = True
    except Exception as e:
        print(f"[Cache] Error cargando caché: {e}")
    finally:
        liberar_db(conn)

def _invalidar_cache():
    """Recarga la caché desde Railway (llamar después de cualquier escritura)."""
    _cargar_cache()

def hacer_ventana(root, titulo, ancho, alto, modal=False):
    v = tk.Toplevel(root)
    v.title(titulo)
    v.configure(bg=COLORES["fondo"])
    v.resizable(True, True)
    v.update_idletasks()
    sw = v.winfo_screenwidth()
    sh = v.winfo_screenheight()
    # En macOS reservar ~80px para barra de menú (25) + Dock (55)
    margen_v = 80
    alto_real = min(alto, sh - margen_v)
    ancho_real = min(ancho, sw - 40)
    x = max(0, (sw - ancho_real) // 2)
    y = max(30, (sh - alto_real) // 2)   # 30px desde top para dejar menú
    v.geometry(f"{ancho_real}x{alto_real}+{x}+{y}")
    v.minsize(min(ancho, ancho_real), min(300, alto_real))
    if modal:
        v.grab_set()
    return v

def label(parent, texto, fuente="normal", color=None, bg=None, **kw):
    return tk.Label(
        parent, text=texto,
        font=FUENTES.get(fuente, FUENTES["normal"]),
        fg=color or COLORES["texto"],
        bg=bg or COLORES["fondo"],
        **kw
    )

def separador(parent, bg=None):
    tk.Frame(parent, height=1, bg=bg or COLORES["borde"]).pack(fill="x", padx=0, pady=4)

def badge(parent, texto, color_bg, color_fg="#fff"):
    f = tk.Frame(parent, bg=color_bg, padx=8, pady=2)
    tk.Label(f, text=texto, font=FUENTES["small"], bg=color_bg, fg=color_fg).pack()
    return f


# ─── APP PRINCIPAL ───────────────────────────────────────────────────────────
class AplicacionClubPro:
    def __init__(self, root):
        self.root = root
        self.root.title("IKA Ecuador · Sistema de Gestión")
        self.root.geometry("520x630")
        self.root.configure(bg=COLORES["fondo"])
        self.root.resizable(False, False)
        self.ventanas = {}
        # Verificar contraseña si hay una configurada
        if _config.get("password", ""):
            self._pedir_password_ingreso()
        else:
            self._construir_home()

    def _pedir_password_ingreso(self):
        """Ventana de ingreso con contraseña"""
        v = tk.Toplevel(self.root)
        v.title("IKA Ecuador · Acceso")
        v.geometry("340x280")
        v.configure(bg=COLORES["fondo"])
        v.grab_set()
        v.protocol("WM_DELETE_WINDOW", self.root.destroy)

        hdr = tk.Frame(v, bg=COLORES["primario"], pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🥋", font=("Segoe UI Emoji", 30), bg=COLORES["primario"]).pack()
        tk.Label(hdr, text="IKA ECUADOR", font=("Georgia", 16, "bold"),
                 fg=COLORES["acento"], bg=COLORES["primario"]).pack()

        body = tk.Frame(v, bg=COLORES["fondo"], padx=40)
        body.pack(fill="x", pady=20)
        tk.Label(body, text="CONTRASEÑA DE ACCESO", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_pw = ttk.Entry(body, show="●", font=FUENTES["normal"])
        ent_pw.pack(fill="x", ipady=5, pady=(4, 12))
        ent_pw.focus()

        def verificar(event=None):
            if ent_pw.get() == _config.get("password", ""):
                v.destroy()
                self._construir_home()
            else:
                messagebox.showerror("Acceso denegado", "Contraseña incorrecta.", parent=v)
                ent_pw.delete(0, tk.END)

        ent_pw.bind("<Return>", verificar)
        ttk.Button(body, text="🔓  INGRESAR", style="IKA.TButton",
                   command=verificar).pack(fill="x", ipady=4)

    def _construir_home(self):
        # ── HEADER con banda de color ──
        header = tk.Frame(self.root, bg=COLORES["primario"], height=8)
        header.pack(fill="x")

        # ── Logo / identidad ──
        hero = tk.Frame(self.root, bg=COLORES["fondo"], pady=28)
        hero.pack(fill="x")

        # Kanji decorativo de fondo (usa Canvas para superponer)
        tk.Label(hero, text="空手道", font=("Georgia", 42, "bold"),
                 fg="#DDD8D0", bg=COLORES["fondo"]).place(x=340, y=-8)

        tk.Label(hero, text="🥋", font=("Segoe UI Emoji", 36),
                 bg=COLORES["fondo"]).pack()
        tk.Label(hero, text="IKA ECUADOR",
                 font=("Georgia", 38, "bold"),
                 fg=COLORES["acento"], bg=COLORES["fondo"]).pack()
        tk.Label(hero, text="International Karate Association",
                 font=("Segoe UI", 12), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"]).pack()

        # Línea dorada
        tk.Frame(hero, height=2, bg=COLORES["acento"], width=180).pack(pady=(6, 0))

        # ── Subtítulo ──
        tk.Label(self.root, text="S I S T E M A   D E   G E S T I Ó N   D E   A F I L I A D O S",
                 font=("Segoe UI", 7, "bold"), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"]).pack(pady=(0, 16))

        separador(self.root, COLORES["borde"])

        # ── Botones ──
        btn_frame = tk.Frame(self.root, bg=COLORES["fondo"])
        btn_frame.pack(expand=True, fill="both", padx=60, pady=10)

        botones = [
            ("📋  BASE DE DATOS MASTER",     "master",     self.ventana_base_datos),
            ("🔍  BUSCAR POR CÉDULA",         "buscar",     self.ventana_busqueda_individual),
            ("➕  NUEVO AFILIADO",            "registro",   self.ventana_registro),
            ("🏆  EVENTOS",                  "eventos",    self.ventana_eventos),
            ("⚙️  GESTIONAR CATEGORÍAS",      "categorias", self.ventana_categorias),
            ("🔧  CONFIGURACIÓN",             "config",     self.ventana_configuracion),
        ]

        for texto, clave, fn in botones:
            ttk.Button(btn_frame, text=texto, style="IKA.TButton", width=36,
                       command=lambda c=clave, f=fn: self.controlar_ventana(c, f)
                       ).pack(fill="x", pady=5, ipady=4)

        # ── Footer ──
        separador(self.root, COLORES["borde"])
        tk.Label(self.root,
                 text="Club IKA Pro  ·  Gestión Deportiva  ·  Ecuador",
                 font=FUENTES["small"], fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"]).pack(pady=(4, 10))

    def controlar_ventana(self, clave, funcion, *args):
        if clave in self.ventanas and self.ventanas[clave].winfo_exists():
            self.ventanas[clave].lift()
            self.ventanas[clave].focus_force()
        else:
            self.ventanas[clave] = funcion(*args)

    # ── CONFIGURACIÓN ────────────────────────────────────────────────────────
    def ventana_configuracion(self):
        v = hacer_ventana(self.root, "Configuración", 420, 280, modal=True)

        tk.Label(v, text="🔧  CONFIGURACIÓN",
                 font=FUENTES["titulo"], fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(pady=(20, 4))
        tk.Frame(v, height=2, bg=COLORES["primario"]).pack(fill="x", padx=30, pady=(0, 16))

        body = tk.Frame(v, bg=COLORES["fondo"], padx=40)
        body.pack(fill="x")
        tk.Label(body, text="CLAVE MAESTRA (numérica):", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_master = ttk.Entry(body, show="●", font=FUENTES["normal"])
        ent_master.pack(fill="x", ipady=5, pady=(4, 14))
        ent_master.focus()

        def verificar_master(event=None):
            if ent_master.get() == "805375":
                v.destroy()
                self.ventana_config_detalle()
            else:
                messagebox.showerror("Clave incorrecta", "La clave maestra no es válida.", parent=v)
                ent_master.delete(0, tk.END)

        ent_master.bind("<Return>", verificar_master)
        ttk.Button(body, text="🔓  ACCEDER A CONFIGURACIÓN",
                   style="IKA.TButton", command=verificar_master).pack(fill="x", ipady=4)
        return v

    def ventana_config_detalle(self):
        v = hacer_ventana(self.root, "Panel de Configuración", 500, 980, modal=True)

        hdr = tk.Frame(v, bg=COLORES["primario"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔧  PANEL DE CONFIGURACIÓN",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        # Canvas scrollable para que quepa todo el contenido
        _canvas = tk.Canvas(v, bg=COLORES["fondo"], highlightthickness=0)
        _sc     = ttk.Scrollbar(v, orient="vertical", command=_canvas.yview)
        _inner  = tk.Frame(_canvas, bg=COLORES["fondo"])
        _inner.bind("<Configure>", lambda e: _canvas.configure(scrollregion=_canvas.bbox("all")))
        _win_id = _canvas.create_window((0, 0), window=_inner, anchor="nw")
        _canvas.configure(yscrollcommand=_sc.set)
        # FIX: propagar el ancho del canvas al frame interno
        _canvas.bind("<Configure>", lambda e: _canvas.itemconfig(_win_id, width=e.width))
        # FIX: scroll con rueda del mouse
        def _on_mousewheel(event):
            _canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _on_mousewheel_linux(event):
            _canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        _canvas.bind("<MouseWheel>", _on_mousewheel)        # Windows/Mac
        _canvas.bind("<Button-4>",   _on_mousewheel_linux)  # Linux scroll up
        _canvas.bind("<Button-5>",   _on_mousewheel_linux)  # Linux scroll down
        _inner.bind("<MouseWheel>",  _on_mousewheel)
        _sc.pack(side="right", fill="y")
        _canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(_inner, bg=COLORES["fondo"], padx=36)
        body.pack(fill="both", expand=True, pady=16)

        # ── Sección contraseña ──
        tk.Label(body, text="🔑  CONTRASEÑA DE INGRESO",
                 font=("Segoe UI", 9, "bold"), fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 4))
        tk.Label(body,
                 text="Solo 6 dígitos numéricos. Dejá vacío para deshabilitar el acceso con contraseña.",
                 font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

        tk.Label(body, text="NUEVA CONTRASEÑA:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_pw1 = ttk.Entry(body, show="●", font=FUENTES["normal"])
        ent_pw1.pack(fill="x", ipady=5, pady=(2, 8))

        tk.Label(body, text="CONFIRMAR CONTRASEÑA:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_pw2 = ttk.Entry(body, show="●", font=FUENTES["normal"])
        ent_pw2.pack(fill="x", ipady=5, pady=(2, 4))

        # Pre-llenar si ya hay contraseña
        if _config.get("password"):
            ent_pw1.insert(0, _config["password"])
            ent_pw2.insert(0, _config["password"])

        def guardar_password():
            pw1 = ent_pw1.get().strip()
            pw2 = ent_pw2.get().strip()
            if pw1 == "" and pw2 == "":
                _config["password"] = ""
                guardar_config(_config)
                messagebox.showinfo("✅", "Contraseña eliminada. El ingreso será libre.", parent=v)
                return
            if not pw1.isdigit() or len(pw1) != 6:
                messagebox.showwarning("⚠️", "La contraseña debe ser exactamente 6 dígitos numéricos.", parent=v)
                return
            if pw1 != pw2:
                messagebox.showerror("Error", "Las contraseñas no coinciden. Verificá e intentá de nuevo.", parent=v)
                ent_pw2.delete(0, tk.END)
                return
            _config["password"] = pw1
            guardar_config(_config)
            messagebox.showinfo("✅", "Contraseña guardada correctamente.", parent=v)

        ttk.Button(body, text="💾  GUARDAR CONTRASEÑA",
                   style="Gold.TButton", command=guardar_password).pack(fill="x", ipady=4, pady=(4, 16))

        tk.Frame(body, height=1, bg=COLORES["borde"]).pack(fill="x", pady=(0, 12))

        # ── Sección Admin Principal ──
        tk.Label(body, text="👤  ADMINISTRADOR PRINCIPAL",
                 font=("Segoe UI", 9, "bold"), fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 4))
        tk.Label(body,
                 text="Este nombre aparece como remitente en el chat de eventos.",
                 font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

        tk.Label(body, text="NOMBRE:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_adm_nom = ttk.Entry(body, font=FUENTES["normal"])
        ent_adm_nom.pack(fill="x", ipady=5, pady=(2, 8))
        if _config.get("admin_nombre"):
            ent_adm_nom.insert(0, _config["admin_nombre"])

        tk.Label(body, text="APELLIDO:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_adm_ape = ttk.Entry(body, font=FUENTES["normal"])
        ent_adm_ape.pack(fill="x", ipady=5, pady=(2, 4))
        if _config.get("admin_apellido"):
            ent_adm_ape.insert(0, _config["admin_apellido"])

        def guardar_admin():
            nom = ent_adm_nom.get().strip()
            ape = ent_adm_ape.get().strip()
            if not nom or not ape:
                messagebox.showwarning("⚠️", "Ingresá nombre y apellido del administrador.", parent=v)
                return
            _config["admin_nombre"]   = nom
            _config["admin_apellido"] = ape
            guardar_config(_config)
            messagebox.showinfo("✅", f"Administrador guardado: {nom} {ape}", parent=v)

        ttk.Button(body, text="💾  GUARDAR ADMINISTRADOR",
                   style="Gold.TButton", command=guardar_admin).pack(fill="x", ipady=4, pady=(4, 8))

        ttk.Button(body, text="➕  REGISTRAR ADMIN EN BASE DE DATOS",
                   style="IKA.TButton",
                   command=lambda: self.ventana_registro_admin()).pack(fill="x", ipady=4, pady=(0, 16))

        tk.Frame(body, height=1, bg=COLORES["borde"]).pack(fill="x", pady=(0, 12))

        # ── Sección tema de colores ──
        tk.Label(body, text="🎨  TEMA DE COLORES",
                 font=("Segoe UI", 9, "bold"), fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 8))

        var_tema = tk.StringVar(value=_config.get("tema", "Estándar"))

        temas_info = {
            "Estándar":  "Crema y borgoña clásico",
            "Deportivo": "Oscuro intenso con rojo y amarillo",
            "Sobrio":    "Gris neutro y azul profesional",
            "Elegante":  "Negro con dorado premium",
        }

        tema_frame = tk.Frame(body, bg=COLORES["fondo"])
        tema_frame.pack(fill="x")

        for tema, desc in temas_info.items():
            colores_t = TEMAS[tema]
            row = tk.Frame(tema_frame, bg=COLORES["fondo"], pady=3)
            row.pack(fill="x")
            rb = tk.Radiobutton(row, text=f"  {tema}", variable=var_tema, value=tema,
                                font=FUENTES["bold"], fg=COLORES["texto"],
                                bg=COLORES["fondo"], activebackground=COLORES["fondo"],
                                selectcolor=COLORES["superficie2"])
            rb.pack(side="left")
            # Preview de colores
            prev = tk.Frame(row, bg=colores_t["fondo"], width=18, height=18,
                            relief="flat")
            prev.pack(side="left", padx=4)
            tk.Frame(prev, bg=colores_t["primario"], width=8, height=18).pack(side="left")
            tk.Frame(prev, bg=colores_t["acento"], width=5, height=18).pack(side="left")
            tk.Label(row, text=desc, font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                     bg=COLORES["fondo"]).pack(side="left", padx=6)

        def guardar_tema():
            tema_sel = var_tema.get()
            _config["tema"] = tema_sel
            guardar_config(_config)
            messagebox.showinfo("✅ Tema guardado",
                f"Tema «{tema_sel}» guardado.\nReiniciá la aplicación para aplicar los cambios.", parent=v)

        ttk.Button(body, text="🎨  APLICAR TEMA (requiere reinicio)",
                   style="IKA.TButton", command=guardar_tema).pack(fill="x", ipady=4, pady=(10, 0))

        tk.Frame(body, height=1, bg=COLORES["borde"]).pack(fill="x", pady=(14, 8))

        # ── Sección tamaño de letra ──
        tk.Label(body, text="🔤  TAMAÑO DE LETRA",
                 font=("Segoe UI", 9, "bold"), fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 4))
        tk.Label(body,
                 text="Ajusta el tamaño de toda la tipografía de la aplicación.",
                 font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

        escala_inicial = _config.get("font_scale", 1.0)
        var_escala = tk.DoubleVar(value=escala_inicial)

        slider_row = tk.Frame(body, bg=COLORES["fondo"])
        slider_row.pack(fill="x")
        tk.Label(slider_row, text="A", font=("Segoe UI", 8), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"]).pack(side="left")
        slider_font = tk.Scale(
            slider_row, variable=var_escala,
            from_=0.7, to=1.5, resolution=0.05, orient="horizontal",
            bg=COLORES["fondo"], fg=COLORES["texto"],
            highlightthickness=0, troughcolor=COLORES["superficie2"],
            activebackground=COLORES["primario"], sliderrelief="flat",
            showvalue=False, length=260,
        )
        slider_font.pack(side="left", padx=6)
        tk.Label(slider_row, text="A", font=("Segoe UI", 14, "bold"), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"]).pack(side="left")

        # Panel de preview en vivo
        preview_frame = tk.Frame(body, bg=COLORES["superficie"],
                                 padx=14, pady=10, relief="flat", bd=1)
        preview_frame.pack(fill="x", pady=(10, 0))

        lbl_prev_titulo = tk.Label(preview_frame,
            text="Título de ejemplo  —  IKA Ecuador",
            fg=COLORES["primario"], bg=COLORES["superficie"])
        lbl_prev_titulo.pack(anchor="w")
        lbl_prev_normal = tk.Label(preview_frame,
            text="Texto normal: Juan Pérez  ·  Cinturón Negro  ·  Quito",
            fg=COLORES["texto"], bg=COLORES["superficie"])
        lbl_prev_normal.pack(anchor="w", pady=(4, 0))
        lbl_prev_small = tk.Label(preview_frame,
            text="Texto pequeño: categoría / estado / fecha ingreso",
            fg=COLORES["texto_suave"], bg=COLORES["superficie"])
        lbl_prev_small.pack(anchor="w", pady=(2, 0))

        lbl_pct = tk.Label(body, text=f"Escala actual: {int(escala_inicial*100)}%",
                           font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                           bg=COLORES["fondo"])
        lbl_pct.pack(anchor="w", pady=(6, 0))

        def actualizar_preview(val=None):
            esc = var_escala.get()
            def sz(n): return max(7, round(n * esc))
            lbl_prev_titulo.config(font=("Georgia",  sz(14), "bold"))
            lbl_prev_normal.config(font=("Segoe UI", sz(12)))
            lbl_prev_small.config( font=("Segoe UI", sz(10)))
            lbl_pct.config(text=f"Escala actual: {int(esc*100)}%")

        slider_font.config(command=actualizar_preview)
        actualizar_preview()   # aplicar valores iniciales al preview

        def guardar_escala():
            esc = round(var_escala.get(), 2)
            _config["font_scale"] = esc
            guardar_config(_config)
            messagebox.showinfo("✅ Tamaño guardado",
                f"Escala «{int(esc*100)}%» guardada.\nReiniciá la aplicación para aplicar los cambios.", parent=v)

        ttk.Button(body, text="💾  GUARDAR TAMAÑO DE LETRA",
                   style="Gold.TButton", command=guardar_escala).pack(fill="x", ipady=4, pady=(10, 0))

        tk.Frame(body, height=1, bg=COLORES["borde"]).pack(fill="x", pady=(16, 10))

        # ── Sección PostgreSQL (Railway) ──────────────────────────────────────
        tk.Label(body, text="🐘  POSTGRESQL  (Railway)",
                 font=("Segoe UI", 9, "bold"), fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 4))
        tk.Label(body,
                 text="Pegá la DATABASE_URL que te da Railway para cada base de datos.\n"
                      "Formato: postgresql://user:pass@host:port/dbname",
                 font=("Segoe UI", 7), fg=COLORES["texto_suave"],
                 bg=COLORES["fondo"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 10))

        pg_cfg = _config.get("postgres", {"miembros": {"url": ""}, "chat": {"url": ""}})

        tk.Label(body, text="URL — club_miembros:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_pg_m = ttk.Entry(body, font=("Segoe UI", 9), show="")
        ent_pg_m.pack(fill="x", ipady=5, pady=(2, 10))
        ent_pg_m.insert(0, pg_cfg.get("miembros", {}).get("url", ""))

        tk.Label(body, text="URL — club_chat:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_pg_c = ttk.Entry(body, font=("Segoe UI", 9), show="")
        ent_pg_c.pack(fill="x", ipady=5, pady=(2, 4))
        ent_pg_c.insert(0, pg_cfg.get("chat", {}).get("url", ""))

        def guardar_postgres():
            global _pool_miembros, _pool_chat
            url_m = ent_pg_m.get().strip()
            url_c = ent_pg_c.get().strip()
            if not url_m or not url_c:
                messagebox.showwarning("⚠️", "Ingresá ambas URLs de PostgreSQL.", parent=v)
                return
            _config["postgres"] = {
                "miembros": {"url": url_m},
                "chat":     {"url": url_c}
            }
            guardar_config(_config)
            # Reiniciar pools para que usen las nuevas credenciales
            if _pool_miembros:
                try: _pool_miembros.closeall()
                except: pass
            if _pool_chat:
                try: _pool_chat.closeall()
                except: pass
            _pool_miembros = None
            _pool_chat     = None
            messagebox.showinfo("✅ PostgreSQL guardado",
                "Credenciales guardadas.\nLa conexión se establecerá en la próxima operación.", parent=v)

        def probar_conexion():
            conn = conectar_db()
            if conn is None: return
            if conn:
                liberar_db(conn)
                messagebox.showinfo("✅ Conexión exitosa",
                    "club_miembros conectado correctamente.", parent=v)

        ttk.Button(body, text="💾  GUARDAR CREDENCIALES POSTGRESQL",
                   style="IKA.TButton", command=guardar_postgres).pack(fill="x", ipady=4, pady=(6, 4))
        ttk.Button(body, text="🔌  PROBAR CONEXIÓN",
                   style="Gold.TButton", command=probar_conexion).pack(fill="x", ipady=4, pady=(0, 8))

        return v

    # ── CATEGORÍAS ──────────────────────────────────────────────────────────
    def ventana_categorias(self):
        v = hacer_ventana(self.root, "Gestionar Categorías", 340, 440)

        tk.Label(v, text="⚙️  CATEGORÍAS / ROLES",
                 font=FUENTES["titulo"], fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(pady=(20, 4))
        tk.Frame(v, height=2, bg=COLORES["primario"]).pack(fill="x", padx=30, pady=(0, 16))

        inner = tk.Frame(v, bg=COLORES["fondo"])
        inner.pack(padx=30, fill="x")

        tk.Label(inner, text="Nueva categoría:", font=FUENTES["bold"],
                 fg=COLORES["texto"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_cat = ttk.Entry(inner)
        ent_cat.pack(fill="x", pady=(4, 8))

        def agregar():
            nombre = ent_cat.get().strip()
            if nombre:
                conn = conectar_db()
                if conn is None:
                    messagebox.showerror("Sin conexión",
                        "No hay conexión a PostgreSQL.\n"
                        "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                    return
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre,))
                    conn.commit()
                    _invalidar_cache()
                    ent_cat.delete(0, tk.END); cargar()
                except Exception as e:
                    conn.rollback()
                    if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                        messagebox.showerror("Error", "Ya existe esa categoría.")
                    else:
                        messagebox.showerror("Error", f"Error al guardar:\n{e}")
                        
                finally:
                    liberar_db(conn)

        ttk.Button(inner, text="➕  Agregar", style="IKA.TButton",
                   command=agregar).pack(fill="x", pady=(0, 12))

        tk.Label(v, text="Categorías existentes:", font=FUENTES["bold"],
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", padx=30)

        lista_frame = tk.Frame(v, bg=COLORES["superficie"], bd=1,
                                relief="flat", padx=4, pady=4)
        lista_frame.pack(fill="both", expand=True, padx=30, pady=(4, 8))

        lista_cat = tk.Listbox(lista_frame, bg=COLORES["superficie2"],
                               fg=COLORES["texto"], selectbackground=COLORES["primario"],
                               selectforeground=COLORES["blanco"],
                               font=FUENTES["normal"], relief="flat", bd=0,
                               activestyle="none", highlightthickness=0)
        lista_cat.pack(fill="both", expand=True)

        def cargar():
            lista_cat.delete(0, tk.END)
            if not _cache["cargado"]:
                _cargar_cache()
            for nombre in _cache["categorias"]:
                lista_cat.insert(tk.END, f"  {nombre}")

        def eliminar():
            if not lista_cat.curselection(): return
            sel = lista_cat.get(lista_cat.curselection()).strip()
            if messagebox.askyesno("Confirmar", f"¿Eliminar «{sel}»?"):
                conn = conectar_db()
                if conn is None:
                    messagebox.showerror("Sin conexión",
                        "No hay conexión a PostgreSQL.\n"
                        "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                    return
                cur = conn.cursor()
                cur.execute("DELETE FROM categorias WHERE nombre=%s", (sel,))
                conn.commit(); liberar_db(conn)
                _invalidar_cache()
                cargar()

        ttk.Button(v, text="🗑️  Eliminar seleccionada",
                   style="Danger.TButton", command=eliminar).pack(padx=30, fill="x", pady=(0, 16))

        cargar()
        return v

    # ── REGISTRO / EDICIÓN ──────────────────────────────────────────────────
    def ventana_registro(self, datos_edicion=None):
        titulo = "Editar Afiliado" if datos_edicion else "Nuevo Afiliado"
        v_reg = hacer_ventana(self.root, titulo, 540, 820, modal=True)

        # Header interno
        hdr = tk.Frame(v_reg, bg=COLORES["primario"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🥋  {titulo.upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        canvas = tk.Canvas(v_reg, bg=COLORES["fondo"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(v_reg, orient="vertical", command=canvas.yview)
        form_container = tk.Frame(canvas, bg=COLORES["fondo"])

        form_container.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        form = tk.Frame(form_container, bg=COLORES["fondo"], padx=36)
        form.pack(fill="both", expand=True, pady=16)

        self.entradas = {}
        campos = [
            ("Nombres",              "nombres"),
            ("Apellidos",            "apellidos"),
            ("Cédula",               "cedula"),
            ("Teléfono",             "telefono"),
            ("Dirección",            "direccion"),
            ("Correo electrónico",   "correo"),
            ("Ciudad de nacimiento", "ciudad_nacimiento"),
        ]

        for label_text, key in campos:
            tk.Label(form, text=label_text.upper(),
                     font=("Segoe UI", 8, "bold"),
                     fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(10, 2))
            ent = ttk.Entry(form)
            ent.pack(fill="x", ipady=4)
            self.entradas[key] = ent

        # Género
        tk.Label(form, text="GÉNERO",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        genero_frame = tk.Frame(form, bg=COLORES["fondo"])
        genero_frame.pack(anchor="w", pady=(0, 4))
        self.var_genero = tk.StringVar(value="")
        tk.Radiobutton(genero_frame, text="Hombre", variable=self.var_genero, value="Hombre",
                       bg=COLORES["fondo"], fg=COLORES["texto"], activebackground=COLORES["fondo"],
                       selectcolor=COLORES["superficie2"], font=FUENTES["normal"]).pack(side="left", padx=(0,16))
        tk.Radiobutton(genero_frame, text="Mujer", variable=self.var_genero, value="Mujer",
                       bg=COLORES["fondo"], fg=COLORES["texto"], activebackground=COLORES["fondo"],
                       selectcolor=COLORES["superficie2"], font=FUENTES["normal"]).pack(side="left")

        # Fecha nacimiento
        tk.Label(form, text="FECHA DE NACIMIENTO",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        self.cal_nac = DateEntry(form, width=18,
                                  background=COLORES["primario"],
                                  foreground=COLORES["blanco"],
                                  borderwidth=0, date_pattern='dd/mm/yyyy',
                                  font=FUENTES["normal"])
        self.cal_nac.pack(anchor="w")

        # Categoría
        tk.Label(form, text="CATEGORÍA / ROL",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        if not _cache["cargado"]:
            _cargar_cache()
        cats = _cache["categorias"]
        self.combo_cat = ttk.Combobox(form, values=cats, state="readonly", font=FUENTES["normal"])
        self.combo_cat.pack(fill="x", ipady=4)

        # Fecha ingreso
        tk.Label(form, text="FECHA DE INGRESO AL CLUB",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        self.cal = DateEntry(form, width=18,
                              background=COLORES["primario"],
                              foreground=COLORES["blanco"],
                              borderwidth=0, date_pattern='dd/mm/yyyy',
                              font=FUENTES["normal"])
        self.cal.pack(anchor="w")

        # Pre-rellenar si es edición
        if datos_edicion:
            for i, key in enumerate(["nombres","apellidos","cedula","telefono","direccion","correo"]):
                self.entradas[key].insert(0, datos_edicion[i+1])
            self.entradas["ciudad_nacimiento"].insert(0, datos_edicion[9] or "")
            self.combo_cat.set(datos_edicion[8] or "")
            if datos_edicion[7]:
                # PG devuelve date objects; DateEntry.set_date los acepta directamente
                try:
                    if hasattr(datos_edicion[7], "day"):
                        self.cal.set_date(datos_edicion[7])
                    else:
                        self.cal.set_date(datetime.strptime(str(datos_edicion[7])[:10], "%Y-%m-%d"))
                except Exception:
                    pass
            if datos_edicion[10]:
                try:
                    if hasattr(datos_edicion[10], "day"):
                        self.cal_nac.set_date(datos_edicion[10])
                    else:
                        self.cal_nac.set_date(datetime.strptime(str(datos_edicion[10])[:10], "%Y-%m-%d"))
                except Exception:
                    pass
            if len(datos_edicion) > 11 and datos_edicion[11]:
                self.var_genero.set(datos_edicion[11])

        # Botón guardar
        btn_txt = "💾  GUARDAR CAMBIOS" if datos_edicion else "✅  REGISTRAR AFILIADO"
        btn_frame = tk.Frame(v_reg, bg=COLORES["fondo"], pady=14)
        btn_frame.pack(fill="x", padx=36)
        ttk.Button(btn_frame, text=btn_txt, style="IKA.TButton",
                   command=lambda: self.guardar(v_reg, datos_edicion[0] if datos_edicion else None)
                   ).pack(fill="x", ipady=6)

        return v_reg

    def guardar(self, ventana, id_socio=None):
        d = {k: v.get().strip() for k, v in self.entradas.items()}
        fecha_ing = self.cal.get()
        fecha_nac = self.cal_nac.get()
        cat = self.combo_cat.get()
        genero = self.var_genero.get()

        if not all(d.values()) or not cat or not genero:
            messagebox.showwarning("⚠️ Atención",
                "Todos los campos son obligatorios para guardar el registro.")
            return

        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cursor = conn.cursor()
        try:
            if id_socio:
                cursor.execute("""UPDATE miembros SET nombres=%s, apellidos=%s, cedula=%s,
                    telefono=%s, direccion=%s, correo=%s, fecha_ingreso=%s, categoria=%s,
                    ciudad_nacimiento=%s, fecha_nacimiento=%s, genero=%s WHERE id=%s""",
                    (d["nombres"], d["apellidos"], d["cedula"], d["telefono"],
                     d["direccion"], d["correo"],
                     _parsear_fecha(fecha_ing), cat,
                     d["ciudad_nacimiento"], _parsear_fecha(fecha_nac), genero, id_socio))
            else:
                pw_hash = _hash_cedula(d["cedula"])
                cursor.execute("""INSERT INTO miembros (nombres, apellidos, cedula, telefono,
                    direccion, correo, fecha_ingreso, categoria, ciudad_nacimiento,
                    fecha_nacimiento, genero, password_hash, debe_cambiar_pass)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (d["nombres"], d["apellidos"], d["cedula"], d["telefono"],
                     d["direccion"], d["correo"],
                     _parsear_fecha(fecha_ing), cat,
                     d["ciudad_nacimiento"], _parsear_fecha(fecha_nac),
                     genero, pw_hash, True))
            conn.commit()
            _invalidar_cache()
            messagebox.showinfo("✅ Éxito", "Afiliado guardado correctamente.")
            if "master" in self.ventanas and self.ventanas["master"].winfo_exists():
                self.cargar_datos_tabla()
            ventana.destroy()
        except Exception as e:
            conn.rollback()
            if "unique" in str(e).lower():
                messagebox.showerror("Error", "Ya existe un afiliado con esa cédula.")
            else:
                messagebox.showerror("Error", f"{e}")
        finally:
            liberar_db(conn)

    # ── FICHA VISUALIZACIÓN ─────────────────────────────────────────────────
    def mostrar_visualizacion_horizontal(self, socio):
        v_ver = hacer_ventana(self.root, f"{socio[1]} {socio[2]}", 620, 660)

        hdr = tk.Frame(v_ver, bg=COLORES["primario"], pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🥋", font=("Segoe UI Emoji", 24),
                 bg=COLORES["primario"]).pack()
        tk.Label(hdr, text=f"{socio[1].upper()} {socio[2].upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()
        cat_text = socio[8] or "Sin categoría"
        badge_f = tk.Frame(hdr, bg=COLORES["acento"], padx=10, pady=3)
        badge_f.pack(pady=(6, 0))
        tk.Label(badge_f, text=cat_text.upper(),
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["blanco"], bg=COLORES["acento"]).pack()

        info_frame = tk.Frame(v_ver, bg=COLORES["fondo"], padx=30, pady=16)
        info_frame.pack(fill="both", expand=True)

        genero_val = socio[11] if len(socio) > 11 else "—"
        campos = [
            ("🪪  Cédula",        socio[3]),
            ("⚧  Género",        genero_val or "—"),
            ("📅  F. Nacimiento", _fmt_fecha(socio[10])),
            ("🏙️  Ciudad Nac.",   socio[9]),
            ("📞  Teléfono",      socio[4]),
            ("📍  Dirección",     socio[5]),
            ("✉️  Correo",        socio[6]),
            ("📋  Ingreso",       _fmt_fecha(socio[7])),
        ]

        tk.Label(info_frame,
                 text="💡 Hacé clic en cualquier campo para seleccionar y copiar (Ctrl+C)",
                 font=("Segoe UI", 7, "italic"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 8))

        for i, (lab, val) in enumerate(campos):
            bg_row = COLORES["superficie"] if i % 2 == 0 else COLORES["superficie2"]
            row = tk.Frame(info_frame, bg=bg_row, pady=6, padx=10)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=lab, font=FUENTES["bold"],
                     fg=COLORES["texto_suave"], bg=bg_row,
                     width=18, anchor="w").pack(side="left")
            # Entry de solo lectura — permite seleccionar y Ctrl+C
            ent = tk.Entry(row, font=FUENTES["normal"],
                           fg=COLORES["texto"], bg=bg_row,
                           relief="flat", bd=0,
                           readonlybackground=bg_row,
                           state="readonly")
            ent.pack(side="left", fill="x", expand=True)
            # Insertar valor
            ent.config(state="normal")
            ent.insert(0, str(val or "—"))
            ent.config(state="readonly")

        btn_frame = tk.Frame(v_ver, bg=COLORES["fondo"], pady=14)
        btn_frame.pack()
        ttk.Button(btn_frame, text="✏️  Editar Datos", style="Gold.TButton",
                   command=lambda: [v_ver.destroy(), self.ventana_registro(socio)]
                   ).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="📜  Ver Historial", style="IKA.TButton",
                   command=lambda: self.controlar_ventana(
                       f"hist_{socio[0]}", self.ventana_historial, socio)
                   ).pack(side="left", padx=8)
        return v_ver


    def ventana_historial(self, socio):
        v_hist = hacer_ventana(self.root, f"Historial · {socio[1]} {socio[2]}", 720, 680)
        self.id_historial_editando = None

        # Header
        hdr = tk.Frame(v_hist, bg=COLORES["primario_dark"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📜  HISTORIAL  —  {socio[1].upper()} {socio[2].upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario_dark"]).pack()

        # Formulario entrada
        add_frame = ttk.LabelFrame(v_hist, text="  Nueva Entrada  ",
                                    style="IKA.TLabelframe",
                                    padding=14)
        add_frame.pack(fill="x", padx=20, pady=12)
        add_frame.configure(style="IKA.TLabelframe")

        inner_form = tk.Frame(add_frame, bg=COLORES["superficie"])
        inner_form.pack(fill="x")

        tk.Label(inner_form, text="Fecha:", font=FUENTES["bold"],
                 fg=COLORES["texto_suave"], bg=COLORES["superficie"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        cal_suceso = DateEntry(inner_form, width=14,
                                background=COLORES["primario"],
                                foreground=COLORES["blanco"],
                                borderwidth=0, date_pattern='dd/mm/yyyy')
        cal_suceso.grid(row=0, column=1, sticky="w", padx=8)

        tk.Label(inner_form, text="Descripción:", font=FUENTES["bold"],
                 fg=COLORES["texto_suave"], bg=COLORES["superficie"]).grid(row=1, column=0, sticky="nw", pady=(8, 0))
        txt_suceso = tk.Text(inner_form, height=3, width=52,
                              bg=COLORES["superficie2"], fg=COLORES["texto"],
                              insertbackground=COLORES["primario"],
                              relief="flat", font=FUENTES["normal"],
                              padx=8, pady=6, bd=1,
                              highlightbackground=COLORES["borde"],
                              highlightthickness=1)
        txt_suceso.grid(row=2, column=0, columnspan=2, pady=(4, 8), sticky="ew")
        inner_form.columnconfigure(1, weight=1)

        def guardar_suceso():
            desc = txt_suceso.get("1.0", "end-1c").strip()
            if not desc: return
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión",
                    "No hay conexión a PostgreSQL.\n"
                    "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                return
            cursor = conn.cursor()
            if self.id_historial_editando:
                cursor.execute("UPDATE historial SET fecha_suceso=%s, descripcion=%s WHERE id=%s",
                               (_parsear_fecha(cal_suceso.get()), desc, self.id_historial_editando))
                self.id_historial_editando = None
                btn_guardar_h.config(text="➕  Guardar en Historial")
            else:
                cursor.execute("INSERT INTO historial (socio_id, fecha_suceso, descripcion) VALUES (%s,%s,%s)",
                               (socio[0], _parsear_fecha(cal_suceso.get()), desc))
            conn.commit(); liberar_db(conn)
            txt_suceso.delete("1.0", "end"); cargar_lista_historial()

        btn_guardar_h = ttk.Button(inner_form, text="➕  Guardar en Historial",
                                    style="IKA.TButton", command=guardar_suceso)
        btn_guardar_h.grid(row=3, column=0, columnspan=2, sticky="ew")

        # Tabla historial
        list_frame = tk.Frame(v_hist, bg=COLORES["fondo"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        cols = ("id", "fecha", "descripcion")
        tabla_hist = ttk.Treeview(list_frame, columns=cols, show="headings",
                                   style="IKA.Treeview")
        tabla_hist.heading("id", text="ID")
        tabla_hist.heading("fecha", text="Fecha")
        tabla_hist.heading("descripcion", text="Descripción / Evento")
        tabla_hist.column("id", width=44, anchor="center")
        tabla_hist.column("fecha", width=100, anchor="center")
        tabla_hist.column("descripcion", width=460)

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tabla_hist.yview)
        tabla_hist.configure(yscrollcommand=scroll.set)
        tabla_hist.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def cargar_lista_historial():
            for item in tabla_hist.get_children(): tabla_hist.delete(item)
            conn = conectar_db()
            if conn is None: return
            cursor = conn.cursor()
            cursor.execute("SELECT id, fecha_suceso, descripcion FROM historial WHERE socio_id=%s ORDER BY id DESC",
                           (socio[0],))
            for fila in cursor.fetchall():
                fila = list(fila)
                fila[1] = _fmt_fecha(fila[1])  # fecha_suceso
                tabla_hist.insert("", "end", values=fila)
            liberar_db(conn)

        def preparar_edicion():
            sel = tabla_hist.selection()
            if not sel: return
            valores = tabla_hist.item(sel)['values']
            self.id_historial_editando = valores[0]
            try:
                cal_suceso.set_date(datetime.strptime(valores[1], '%d/%m/%Y'))
            except Exception:
                pass  # si el formato es distinto, deja la fecha actual
            txt_suceso.delete("1.0", "end")
            txt_suceso.insert("1.0", valores[2])
            btn_guardar_h.config(text="💾  Actualizar Historial")

        def borrar_item():
            sel = tabla_hist.selection()
            if not sel: return
            if messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
                id_item = tabla_hist.item(sel)['values'][0]
                conn = conectar_db()
                if conn is None:
                    messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                    return
                cursor = conn.cursor()
                cursor.execute("DELETE FROM historial WHERE id=%s", (id_item,))
                conn.commit(); liberar_db(conn); cargar_lista_historial()

        acc_f = tk.Frame(v_hist, bg=COLORES["fondo"])
        acc_f.pack(pady=(0, 12))
        ttk.Button(acc_f, text="✏️  Editar seleccionado",
                   style="Gold.TButton", command=preparar_edicion).pack(side="left", padx=6)
        ttk.Button(acc_f, text="🗑️  Borrar seleccionado",
                   style="Danger.TButton", command=borrar_item).pack(side="left", padx=6)

        cargar_lista_historial()
        return v_hist

    # ── BÚSQUEDA ────────────────────────────────────────────────────────────
    def ventana_busqueda_individual(self):
        v_bus = hacer_ventana(self.root, "Buscar Afiliado", 400, 240)

        tk.Label(v_bus, text="🔍  BUSCAR POR CÉDULA",
                 font=FUENTES["titulo"], fg=COLORES["acento"],
                 bg=COLORES["fondo"]).pack(pady=(20, 4))
        tk.Frame(v_bus, height=2, bg=COLORES["primario"]).pack(fill="x", padx=40, pady=(0, 14))

        inner = tk.Frame(v_bus, bg=COLORES["fondo"])
        inner.pack(padx=40, fill="x")
        tk.Label(inner, text="Número de cédula:", font=FUENTES["bold"],
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent = ttk.Entry(inner)
        ent.pack(fill="x", ipady=4, pady=(4, 12))
        ent.focus()

        def buscar(event=None):
            cedula = ent.get().strip()
            if not _cache["cargado"]:
                _cargar_cache()
            s = next((m for m in _cache["miembros"] if m[3] == cedula), None)
            if s:
                v_bus.destroy()
                self.mostrar_visualizacion_horizontal(s)
            else:
                messagebox.showerror("No encontrado", "No existe un afiliado con esa cédula.")

        ent.bind("<Return>", buscar)
        ttk.Button(inner, text="🔍  BUSCAR", style="IKA.TButton",
                   command=buscar).pack(fill="x", ipady=4)
        return v_bus

    # ── BASE MASTER ─────────────────────────────────────────────────────────
    def ventana_base_datos(self):
        v_db = tk.Toplevel(self.root)
        v_db.title("Base de Datos Master")
        v_db.geometry("1150x640")
        v_db.configure(bg=COLORES["fondo"])

        # Header
        hdr = tk.Frame(v_db, bg=COLORES["primario"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  BASE DE DATOS MASTER  —  IKA ECUADOR",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        frame = tk.Frame(v_db, bg=COLORES["fondo"])
        frame.pack(fill="both", expand=True, padx=14, pady=10)

        columnas = ("id","nombres","apellidos","cedula","categoria","ciudad","f_nac","telefono","direccion","correo","ingreso")
        self.tabla = ttk.Treeview(frame, columns=columnas, show="headings", style="IKA.Treeview")

        titulos = ["ID","Nombres","Apellidos","Cédula","Categoría","Ciudad Nac.","F. Nacimiento","Teléfono","Dirección","Correo","Ingreso"]
        anchos  = [44, 110, 110, 100, 100, 100, 100, 90, 140, 140, 90]

        for col, tit, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=tit,
                               command=lambda c=col: self.ordenar_columna(c, False))
            self.tabla.column(col, width=ancho, anchor="center")

        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.tabla.yview)
        scroll_x = ttk.Scrollbar(v_db, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tabla.pack(side="top", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x", padx=14, pady=(0, 4))

        self.cargar_datos_tabla()

        btn_f = tk.Frame(v_db, bg=COLORES["fondo"], pady=10)
        btn_f.pack()
        ttk.Button(btn_f, text="🔍  Ver Ficha e Historial",
                   style="IKA.TButton", command=self.ver_desde_tabla).pack(side="left", padx=8)
        ttk.Button(btn_f, text="🔄  Actualizar Tabla",
                   style="Gold.TButton", command=self.cargar_datos_tabla).pack(side="left", padx=8)
        ttk.Button(btn_f, text="📤  Exportar a Excel",
                   style="Gold.TButton",
                   command=self.exportar_excel).pack(side="left", padx=8)
        ttk.Button(btn_f, text="📥  Importar desde Excel",
                   style="IKA.TButton",
                   command=lambda: self.importar_excel(self.cargar_datos_tabla)).pack(side="left", padx=8)

        return v_db

    def cargar_datos_tabla(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        if not _cache["cargado"]:
            _cargar_cache()
        for i, f in enumerate(_cache["miembros"]):
            tag = "par" if i % 2 == 0 else "impar"
            f = list(f)
            f[6]  = _fmt_fecha(f[6])   # fecha_nacimiento
            f[10] = _fmt_fecha(f[10])  # fecha_ingreso
            self.tabla.insert("", "end", values=tuple(f[:11]), tags=(tag,))
        self.tabla.tag_configure("par",   background=COLORES["superficie"])
        self.tabla.tag_configure("impar", background=COLORES["superficie2"])

    def ver_desde_tabla(self):
        item = self.tabla.selection()
        if not item: return
        socio_id = self.tabla.item(item)['values'][0]
        s = next((m for m in _cache["miembros"] if m[0] == socio_id), None)
        if s:
            self.mostrar_visualizacion_horizontal(s)
        else:
            conn = conectar_db()
            if conn is None: return
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM miembros WHERE id=%s", (socio_id,))
            s = cursor.fetchone(); liberar_db(conn)
            if s: self.mostrar_visualizacion_horizontal(s)

    def ordenar_columna(self, col, reverse):
        l = [(self.tabla.set(k, col), k) for k in self.tabla.get_children("")]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): self.tabla.move(k, "", index)
        self.tabla.heading(col, command=lambda: self.ordenar_columna(col, not reverse))


    # ── EVENTOS ─────────────────────────────────────────────────────────────
    def ventana_eventos(self):
        v_ev = hacer_ventana(self.root, "Eventos IKA", 820, 580)
        hdr = tk.Frame(v_ev, bg=COLORES["primario"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🏆  EVENTOS  —  IKA ECUADOR",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        top_bar = tk.Frame(v_ev, bg=COLORES["fondo"], pady=10)
        top_bar.pack(fill="x", padx=20)

        def abrir_crear():
            self.ventana_crear_evento(cargar_eventos)

        def ver_sel():
            sel = tabla_ev.selection()
            if not sel: return
            self.ventana_detalle_evento(tabla_ev.item(sel)["values"][0], callback_reload=cargar_eventos)

        ttk.Button(top_bar, text="➕  CREAR NUEVO EVENTO",
                   style="IKA.TButton", command=abrir_crear).pack(side="left")
        ttk.Button(top_bar, text="🔍  VER SELECCIONADO",
                   style="Gold.TButton", command=ver_sel).pack(side="left", padx=10)

        frame_tabla = tk.Frame(v_ev, bg=COLORES["fondo"])
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        cols_ev = ("id", "nombre", "fecha", "participantes", "descripcion")
        tabla_ev = ttk.Treeview(frame_tabla, columns=cols_ev, show="headings", style="IKA.Treeview")
        tabla_ev.heading("id",            text="ID")
        tabla_ev.heading("nombre",        text="Nombre del Evento")
        tabla_ev.heading("fecha",         text="Fecha")
        tabla_ev.heading("participantes", text="Participantes")
        tabla_ev.heading("descripcion",   text="Descripcion")
        tabla_ev.column("id",            width=44,  anchor="center")
        tabla_ev.column("nombre",        width=210)
        tabla_ev.column("fecha",         width=100, anchor="center")
        tabla_ev.column("participantes", width=110, anchor="center")
        tabla_ev.column("descripcion",   width=290)
        sc = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_ev.yview)
        tabla_ev.configure(yscrollcommand=sc.set)
        tabla_ev.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")

        tabla_ev.bind("<Double-1>", lambda e: ver_sel())

        def cargar_eventos():
            for item in tabla_ev.get_children(): tabla_ev.delete(item)
            if not _cache["cargado"]:
                _cargar_cache()
            for i, ev in enumerate(_cache["eventos"]):
                cant = len(_cache["participantes"].get(ev[0], set()))
                tag = "par" if i % 2 == 0 else "impar"
                tabla_ev.insert("", "end",
                                values=(ev[0], ev[1], _fmt_fecha(ev[2]), f"{cant} miembros", ev[3] or ""),
                                tags=(tag,))
            tabla_ev.tag_configure("par",   background=COLORES["superficie"])
            tabla_ev.tag_configure("impar", background=COLORES["superficie2"])

        bot_f = tk.Frame(v_ev, bg=COLORES["fondo"], pady=6)
        bot_f.pack()
        def eliminar_sel():
            sel = tabla_ev.selection()
            if not sel: return
            eid   = tabla_ev.item(sel)["values"][0]
            enomb = tabla_ev.item(sel)["values"][1]
            if messagebox.askyesno("Confirmar", f"Eliminar el evento \"{enomb}\"?\nSe eliminaran sus participantes."):
                conn = conectar_db()
                if conn is None:
                    messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                    return
                cur = conn.cursor()
                cur.execute("DELETE FROM evento_participantes WHERE evento_id=%s", (eid,))
                cur.execute("DELETE FROM eventos WHERE id=%s", (eid,))
                conn.commit(); liberar_db(conn)
                _invalidar_cache()
                cargar_eventos()
        ttk.Button(bot_f, text="🗑️  Eliminar Evento",
                   style="Danger.TButton", command=eliminar_sel).pack()

        cargar_eventos()
        return v_ev

    def ventana_crear_evento(self, callback_reload, evento_id=None):
        # Si viene evento_id es modo edicion
        modo_edicion = evento_id is not None
        titulo = "Editar Evento" if modo_edicion else "Crear Nuevo Evento"
        v_cr = hacer_ventana(self.root, titulo, 980, 720, modal=True)

        hdr = tk.Frame(v_cr, bg=COLORES["primario_dark"], pady=12)
        hdr.pack(fill="x")
        icono = "✏️" if modo_edicion else "🏆"
        tk.Label(hdr, text=f"{icono}  {titulo.upper()}", font=FUENTES["titulo"],
                 fg=COLORES["blanco"], bg=COLORES["primario_dark"]).pack()

        # ── Datos del evento ──
        form = tk.Frame(v_cr, bg=COLORES["fondo"], padx=20, pady=10)
        form.pack(fill="x")

        fila1 = tk.Frame(form, bg=COLORES["fondo"])
        fila1.pack(fill="x")

        col1 = tk.Frame(fila1, bg=COLORES["fondo"])
        col1.pack(side="left", fill="x", expand=True, padx=(0, 14))
        tk.Label(col1, text="NOMBRE DEL EVENTO", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_nombre = ttk.Entry(col1, font=FUENTES["normal"])
        ent_nombre.pack(fill="x", ipady=4, pady=(2, 0))

        col2 = tk.Frame(fila1, bg=COLORES["fondo"])
        col2.pack(side="left")
        tk.Label(col2, text="FECHA", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        cal_ev = DateEntry(col2, width=14, background=COLORES["primario"],
                           foreground=COLORES["blanco"], borderwidth=0,
                           date_pattern="dd/mm/yyyy", font=FUENTES["normal"])
        cal_ev.pack(anchor="w", pady=(2, 0))

        col3 = tk.Frame(fila1, bg=COLORES["fondo"])
        col3.pack(side="left", padx=(14, 0))
        tk.Label(col3, text="DESCRIPCION (opcional)", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        ent_desc = ttk.Entry(col3, font=FUENTES["normal"], width=28)
        ent_desc.pack(fill="x", ipady=4, pady=(2, 0))

        # Pre-cargar datos si es edicion
        if modo_edicion:
            conn = conectar_db()
            ev_data = None
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT nombre, fecha, descripcion FROM eventos WHERE id=%s", (evento_id,))
                ev_data = cur.fetchone()
                liberar_db(conn)
            if ev_data:
                ent_nombre.insert(0, ev_data[0])
                try:
                    if hasattr(ev_data[1], "day"):
                        cal_ev.set_date(ev_data[1])
                    else:
                        cal_ev.set_date(datetime.strptime(str(ev_data[1])[:10], "%Y-%m-%d"))
                except Exception:
                    pass
                if ev_data[2]: ent_desc.insert(0, ev_data[2])

        tk.Frame(v_cr, height=1, bg=COLORES["borde"]).pack(fill="x", padx=20, pady=6)

        # ── Panel principal dividido en dos columnas ──
        panel = tk.Frame(v_cr, bg=COLORES["fondo"])
        panel.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        # ── COLUMNA IZQUIERDA: lista de miembros con filtros ──
        col_izq = tk.Frame(panel, bg=COLORES["fondo"])
        col_izq.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(col_izq, text="MIEMBROS DISPONIBLES",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 4))

        # Filtros
        filtros_f = tk.Frame(col_izq, bg=COLORES["superficie"], padx=10, pady=8)
        filtros_f.pack(fill="x", pady=(0, 6))

        # ── Búsqueda por nombre ──
        fila_busq = tk.Frame(filtros_f, bg=COLORES["superficie"])
        fila_busq.pack(fill="x", pady=(0, 6))
        tk.Label(fila_busq, text="BUSCAR POR NOMBRE:", font=("Segoe UI", 7, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["superficie"]).pack(anchor="w")
        var_busq = tk.StringVar()
        ent_busq = ttk.Entry(fila_busq, textvariable=var_busq, font=FUENTES["normal"])
        ent_busq.pack(fill="x", ipady=4, pady=(2, 0))

        if not _cache["cargado"]:
            _cargar_cache()
        opciones_cat = ["— Todas —"] + sorted({m[4]  for m in _cache["miembros"] if m[4]})
        opciones_gen = ["— Todos —"] + sorted({m[11] for m in _cache["miembros"] if m[11]})
        opciones_ciu = ["— Todas —"] + sorted({m[5]  for m in _cache["miembros"] if m[5]})

        var_cat = tk.StringVar(value="— Todas —")
        var_gen = tk.StringVar(value="— Todos —")
        var_ciu = tk.StringVar(value="— Todas —")

        fila_cb = tk.Frame(filtros_f, bg=COLORES["superficie"])
        fila_cb.pack(fill="x")

        def bloque(parent, titulo, variable, opciones, ancho):
            b = tk.Frame(parent, bg=COLORES["superficie"])
            b.pack(side="left", padx=(0, 8))
            tk.Label(b, text=titulo, font=("Segoe UI", 7, "bold"),
                     fg=COLORES["texto_suave"], bg=COLORES["superficie"]).pack(anchor="w")
            ttk.Combobox(b, textvariable=variable, values=opciones,
                         state="readonly", width=ancho, font=FUENTES["normal"]).pack()

        bloque(fila_cb, "CATEGORÍA",  var_cat, opciones_cat, 16)
        bloque(fila_cb, "GÉNERO",     var_gen, opciones_gen, 10)
        bloque(fila_cb, "CIUDAD",     var_ciu, opciones_ciu, 13)

        fila_btns_f = tk.Frame(filtros_f, bg=COLORES["superficie"])
        fila_btns_f.pack(fill="x", pady=(6, 0))
        ttk.Button(fila_btns_f, text="🔍  Filtrar",
                   style="IKA.TButton", command=lambda: aplicar_filtros()).pack(side="left", padx=(0, 6))
        ttk.Button(fila_btns_f, text="✕  Limpiar",
                   style="Gold.TButton",
                   command=lambda: [var_cat.set("— Todas —"), var_gen.set("— Todos —"),
                                    var_ciu.set("— Todas —"), var_busq.set(""),
                                    aplicar_filtros()]).pack(side="left")

        # Tabla miembros disponibles
        cols_m = ("id", "nombre", "cedula", "categoria", "genero")
        lista_m = ttk.Treeview(col_izq, columns=cols_m, show="headings",
                                style="IKA.Treeview", height=12)
        lista_m.heading("id",        text="ID")
        lista_m.heading("nombre",    text="Nombre")
        lista_m.heading("cedula",    text="Cedula")
        lista_m.heading("categoria", text="Categoria")
        lista_m.heading("genero",    text="Genero")
        lista_m.column("id",        width=36, anchor="center")
        lista_m.column("nombre",    width=160)
        lista_m.column("cedula",    width=80, anchor="center")
        lista_m.column("categoria", width=90, anchor="center")
        lista_m.column("genero",    width=60, anchor="center")

        sc_izq = ttk.Scrollbar(col_izq, orient="vertical", command=lista_m.yview)
        lista_m.configure(yscrollcommand=sc_izq.set)
        sc_izq.pack(side="right", fill="y")
        lista_m.pack(side="left", fill="both", expand=True)

        # ── COLUMNA CENTRAL: botones accion ──
        col_mid = tk.Frame(panel, bg=COLORES["fondo"], padx=6)
        col_mid.pack(side="left", fill="y")

        # Spacer para centrar verticalmente
        tk.Frame(col_mid, bg=COLORES["fondo"]).pack(expand=True)
        tk.Label(col_mid, text="  o  ", font=("Segoe UI", 7),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(pady=(0,4))
        ttk.Button(col_mid, text="➕  Agregar", style="IKA.TButton",
                   command=lambda: agregar_seleccionado()).pack(pady=4, ipadx=4, ipady=6)
        tk.Frame(col_mid, height=20, bg=COLORES["fondo"]).pack()
        ttk.Button(col_mid, text="✕  Quitar", style="Danger.TButton",
                   command=lambda: quitar_seleccionado()).pack(pady=4, ipadx=4, ipady=6)
        tk.Frame(col_mid, bg=COLORES["fondo"]).pack(expand=True)

        # ── COLUMNA DERECHA: participantes agregados ──
        col_der = tk.Frame(panel, bg=COLORES["fondo"])
        col_der.pack(side="left", fill="both", expand=True, padx=(8, 0))

        lbl_cant = tk.Label(col_der, text="PARTICIPANTES AGREGADOS  (0)",
                             font=("Segoe UI", 8, "bold"),
                             fg=COLORES["acento"], bg=COLORES["fondo"])
        lbl_cant.pack(anchor="w", pady=(0, 4))

        cols_p = ("id", "nombre", "categoria", "genero")
        lista_p = ttk.Treeview(col_der, columns=cols_p, show="headings",
                                style="IKA.Treeview", height=12)
        lista_p.heading("id",        text="ID")
        lista_p.heading("nombre",    text="Nombre")
        lista_p.heading("categoria", text="Categoria")
        lista_p.heading("genero",    text="Genero")
        lista_p.column("id",        width=36, anchor="center")
        lista_p.column("nombre",    width=160)
        lista_p.column("categoria", width=90, anchor="center")
        lista_p.column("genero",    width=60, anchor="center")

        sc_der = ttk.Scrollbar(col_der, orient="vertical", command=lista_p.yview)
        lista_p.configure(yscrollcommand=sc_der.set)
        sc_der.pack(side="right", fill="y")
        lista_p.pack(side="left", fill="both", expand=True)

        # ── Estado ──
        seleccionados = {}  # id -> (nombre, categoria, genero)

        # Pre-cargar participantes si es edicion
        if modo_edicion:
            conn = conectar_db()
            if conn:
                cur = conn.cursor()
                cur.execute("""SELECT m.id, m.nombres, m.apellidos, m.categoria, m.genero
                               FROM miembros m
                               JOIN evento_participantes ep ON ep.socio_id = m.id
                               WHERE ep.evento_id=%s""", (evento_id,))
                for p in cur.fetchall():
                    sid = p[0]
                    nc  = f"{p[1]} {p[2]}"
                    seleccionados[sid] = (nc, p[3] or "", p[4] or "")
                liberar_db(conn)

        def refrescar_lista_p():
            for item in lista_p.get_children(): lista_p.delete(item)
            for i, (sid, (nc, cat, gen)) in enumerate(seleccionados.items()):
                tag = "par" if i % 2 == 0 else "impar"
                lista_p.insert("", "end", values=(sid, nc, cat, gen), tags=(tag,))
            lista_p.tag_configure("par",   background=COLORES["superficie"])
            lista_p.tag_configure("impar", background=COLORES["superficie2"])
            lbl_cant.config(text=f"PARTICIPANTES AGREGADOS  ({len(seleccionados)})")

        def normalizar(texto):
            """Normaliza texto removiendo acentos para búsqueda flexible"""
            import unicodedata
            return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('ascii').lower()

        def aplicar_filtros():
            f_cat  = var_cat.get()
            f_gen  = var_gen.get()
            f_ciu  = var_ciu.get()
            f_busq = var_busq.get().strip()
            for item in lista_m.get_children(): lista_m.delete(item)
            if not _cache["cargado"]:
                _cargar_cache()
            i = 0
            for m in _cache["miembros"]:
                nc  = f"{m[1]} {m[2]}"
                cat = m[4]  or ""
                gen = m[11] or ""
                ciu = m[5]  or ""
                if f_cat != "— Todas —" and cat != f_cat: continue
                if f_gen != "— Todos —" and gen != f_gen: continue
                if f_ciu != "— Todas —" and ciu != f_ciu: continue
                if f_busq:
                    busq_norm = normalizar(f_busq)
                    nc_norm   = normalizar(nc)
                    if not nc_norm.startswith(busq_norm) and busq_norm not in nc_norm:
                        continue
                tag = "par" if i % 2 == 0 else "impar"
                lista_m.insert("", "end",
                               values=(m[0], nc, m[3] or "", cat, gen),
                               tags=(tag,))
                i += 1
            lista_m.tag_configure("par",   background=COLORES["superficie"])
            lista_m.tag_configure("impar", background=COLORES["superficie2"])

        def agregar_seleccionado():
            sel = lista_m.selection()
            if not sel:
                messagebox.showinfo("Atencion", "Selecciona un miembro de la lista de la izquierda.")
                return
            vals = lista_m.item(sel[0])["values"]
            sid  = int(vals[0])
            if sid in seleccionados:
                messagebox.showinfo("Ya agregado",
                    f"{vals[1]} ya fue agregado a este evento.")
                return
            seleccionados[sid] = (vals[1], vals[3], vals[4])
            refrescar_lista_p()

        def quitar_seleccionado():
            sel = lista_p.selection()
            if not sel: return
            sid = int(lista_p.item(sel[0])["values"][0])
            seleccionados.pop(sid, None)
            refrescar_lista_p()

        def doble_clic_m(event):
            item = lista_m.identify_row(event.y)
            if not item: return
            vals = lista_m.item(item)["values"]
            sid  = int(vals[0])
            if sid in seleccionados:
                messagebox.showinfo("Ya agregado",
                    f"{vals[1]} ya fue agregado a este evento.")
                return
            seleccionados[sid] = (vals[1], vals[3], vals[4])
            refrescar_lista_p()

        def doble_clic_p(event):
            item = lista_p.identify_row(event.y)
            if not item: return
            vals = lista_p.item(item)["values"]
            if messagebox.askyesno("Quitar", f"¿Quitar a {vals[1]} del evento?"):
                seleccionados.pop(int(vals[0]), None)
                refrescar_lista_p()

        lista_m.bind("<Double-1>", doble_clic_m)
        lista_p.bind("<Double-1>", doble_clic_p)

        # Búsqueda reactiva por nombre
        var_busq.trace_add("write", lambda *a: aplicar_filtros())

        # ── Botón guardar ──
        def guardar_evento():
            nombre = ent_nombre.get().strip()
            fecha  = cal_ev.get()
            desc   = ent_desc.get().strip()
            if not nombre:
                messagebox.showwarning("Atencion", "El nombre del evento es obligatorio.")
                return
            if not seleccionados:
                messagebox.showwarning("Atencion", "Agrega al menos un participante.")
                return
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión",
                    "No hay conexión a PostgreSQL.\n"
                    "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                return
            cur = conn.cursor()
            if modo_edicion:
                cur.execute("UPDATE eventos SET nombre=%s, fecha=%s, descripcion=%s WHERE id=%s",
                            (nombre, _parsear_fecha(fecha), desc, evento_id))
                cur.execute("DELETE FROM evento_participantes WHERE evento_id=%s", (evento_id,))
                eid = evento_id
            else:
                cur.execute("INSERT INTO eventos (nombre, fecha, descripcion) VALUES (%s,%s,%s) RETURNING id",
                            (nombre, _parsear_fecha(fecha), desc))
                eid = cur.fetchone()[0]
            for sid in seleccionados:
                cur.execute("INSERT INTO evento_participantes (evento_id, socio_id) VALUES (%s,%s)", (eid, sid))
            conn.commit(); liberar_db(conn)
            accion = "actualizado" if modo_edicion else "creado"
            messagebox.showinfo("Exito", f"Evento {accion} con {len(seleccionados)} participante(s).")
            callback_reload()
            v_cr.destroy()

        btn_guardar_txt = "💾  GUARDAR CAMBIOS" if modo_edicion else "💾  GUARDAR EVENTO"
        ttk.Button(v_cr, text=btn_guardar_txt, style="IKA.TButton",
                   command=guardar_evento).pack(pady=(4, 12), padx=20, fill="x")

        aplicar_filtros()
        refrescar_lista_p()
        return v_cr

    def ventana_detalle_evento(self, evento_id, callback_reload=None):
        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, fecha, descripcion FROM eventos WHERE id=%s", (evento_id,))
        ev = cur.fetchone()
        if not ev: liberar_db(conn); return
        cur.execute("""SELECT m.id, m.nombres, m.apellidos, m.cedula, m.categoria, m.genero
                       FROM miembros m
                       JOIN evento_participantes ep ON ep.socio_id = m.id
                       WHERE ep.evento_id=%s ORDER BY m.apellidos""", (evento_id,))
        participantes = cur.fetchall(); liberar_db(conn)

        v_det = hacer_ventana(self.root, f"Evento: {ev[1]}", 700, 580)

        hdr = tk.Frame(v_det, bg=COLORES["primario"], pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🏆", font=("Segoe UI Emoji", 22), bg=COLORES["primario"]).pack()
        tk.Label(hdr, text=ev[1].upper(), font=FUENTES["titulo"],
                 fg=COLORES["blanco"], bg=COLORES["primario"]).pack()
        badge_f = tk.Frame(hdr, bg=COLORES["acento"], padx=10, pady=3)
        badge_f.pack(pady=(6, 0))
        tk.Label(badge_f, text=f"Fecha: {_fmt_fecha(ev[2])}   |   Participantes: {len(participantes)}",
                 font=("Segoe UI", 8, "bold"), fg=COLORES["blanco"], bg=COLORES["acento"]).pack()

        if ev[3]:
            desc_f = tk.Frame(v_det, bg=COLORES["superficie"], pady=8, padx=20)
            desc_f.pack(fill="x", padx=20, pady=(12, 0))
            tk.Label(desc_f, text=ev[3], font=FUENTES["normal"],
                     fg=COLORES["texto"], bg=COLORES["superficie"],
                     wraplength=580, justify="left").pack(anchor="w")

        # Botón editar
        btn_bar = tk.Frame(v_det, bg=COLORES["fondo"], pady=8)
        btn_bar.pack(fill="x", padx=20)

        def abrir_edicion():
            def recargar():
                v_det.destroy()
                if callback_reload: callback_reload()
            self.ventana_crear_evento(recargar, evento_id=evento_id)

        ttk.Button(btn_bar, text="✏️  EDITAR EVENTO",
                   style="Gold.TButton", command=abrir_edicion).pack(side="left")
        ttk.Button(btn_bar, text="🗂️  JERARQUIZAR",
                   style="IKA.TButton",
                   command=lambda: self.ventana_jerarquia(evento_id, ev[1])).pack(side="left", padx=10)
        ttk.Button(btn_bar, text="📊  SEGUIMIENTO",
                   style="IKA.TButton",
                   command=lambda: self.ventana_seguimiento(evento_id, ev[1])).pack(side="left")

        tk.Label(v_det, text="PARTICIPANTES",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", padx=24, pady=(4, 4))

        frame_p = tk.Frame(v_det, bg=COLORES["fondo"])
        frame_p.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        cols_p = ("id", "nombre", "cedula", "categoria", "genero")
        tabla_p = ttk.Treeview(frame_p, columns=cols_p, show="headings", style="IKA.Treeview")
        tabla_p.heading("id",        text="ID")
        tabla_p.heading("nombre",    text="Nombre Completo")
        tabla_p.heading("cedula",    text="Cedula")
        tabla_p.heading("categoria", text="Categoria")
        tabla_p.heading("genero",    text="Genero")
        tabla_p.column("id",        width=44,  anchor="center")
        tabla_p.column("nombre",    width=220)
        tabla_p.column("cedula",    width=110, anchor="center")
        tabla_p.column("categoria", width=140, anchor="center")
        tabla_p.column("genero",    width=80,  anchor="center")

        sc_p = ttk.Scrollbar(frame_p, orient="vertical", command=tabla_p.yview)
        tabla_p.configure(yscrollcommand=sc_p.set)
        sc_p.pack(side="right", fill="y")
        tabla_p.pack(side="left", fill="both", expand=True)

        for i, p in enumerate(participantes):
            tag = "par" if i % 2 == 0 else "impar"
            tabla_p.insert("", "end",
                           values=(p[0], f"{p[1]} {p[2]}", p[3], p[4] or "—", p[5] or "—"),
                           tags=(tag,))
        tabla_p.tag_configure("par",   background=COLORES["superficie"])
        tabla_p.tag_configure("impar", background=COLORES["superficie2"])
        return v_det


    # ── SEGUIMIENTO ──────────────────────────────────────────────────────────
    def ventana_seguimiento(self, evento_id, nombre_evento):
        v = hacer_ventana(self.root, f"Seguimiento · {nombre_evento}", 1200, 740)
        v.resizable(True, True)

        hdr = tk.Frame(v, bg=COLORES["primario"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📊  SEGUIMIENTO  —  {nombre_evento.upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        # ── PanedWindow horizontal: organigrama | chat ──
        paned = tk.PanedWindow(v, orient="horizontal",
                                bg=COLORES["borde"], sashwidth=6,
                                sashrelief="flat", handlesize=0)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        # ── PANEL IZQUIERDO: organigrama solo lectura ──
        panel_izq = tk.Frame(paned, bg=COLORES["fondo"])
        paned.add(panel_izq, minsize=300, width=420, stretch="always")

        tk.Label(panel_izq, text="ORGANIGRAMA  (solo visualización)",
                 font=FUENTES["small"],
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(4, 2), padx=4)

        canvas_frame = tk.Frame(panel_izq, bg=COLORES["superficie"], relief="flat", bd=1)
        canvas_frame.pack(fill="both", expand=True)

        canvas_org = tk.Canvas(canvas_frame, bg=COLORES["superficie"],
                                highlightthickness=0, cursor="hand2")
        sc_org_y = ttk.Scrollbar(canvas_frame, orient="vertical",   command=canvas_org.yview)
        sc_org_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas_org.xview)
        canvas_org.configure(yscrollcommand=sc_org_y.set, xscrollcommand=sc_org_x.set)
        sc_org_x.pack(side="bottom", fill="x")
        sc_org_y.pack(side="right",  fill="y")
        canvas_org.pack(side="left", fill="both", expand=True)

        # Referencia al frame de detalle para actualizar desde el organigrama
        self._seg_det_frame = None

        # ── PANEL DERECHO: detalle + chat ──
        panel_der = tk.Frame(paned, bg=COLORES["fondo"])
        paned.add(panel_der, minsize=340, stretch="always")

        # Sub-paned vertical: detalle arriba | chat abajo
        paned_v = tk.PanedWindow(panel_der, orient="vertical",
                                  bg=COLORES["borde"], sashwidth=6,
                                  sashrelief="flat", handlesize=0)
        paned_v.pack(fill="both", expand=True)

        # ── Sub-panel superior: detalle de persona (solo lectura) ──
        panel_det = tk.Frame(paned_v, bg=COLORES["fondo"])
        paned_v.add(panel_det, minsize=140, height=200, stretch="always")

        lbl_hint = tk.Label(panel_det,
                             text="← Hacé clic en un nodo\npara ver el detalle de avance",
                             font=FUENTES["normal"], fg=COLORES["texto_suave"],
                             bg=COLORES["fondo"], justify="center")
        lbl_hint.pack(expand=True)

        def on_click_nodo(sid, nombre_nodo, rol):
            self._mostrar_detalle_seguimiento(panel_det, evento_id, sid, nombre_nodo, rol)

        # Dibujar organigrama (reutiliza el método existente con on_click de solo lectura)
        self._dibujar_organigrama(canvas_org, evento_id, on_click_nodo)

        # ── Sub-panel inferior: chat tipo WhatsApp ──
        panel_chat = tk.Frame(paned_v, bg=COLORES["fondo"])
        paned_v.add(panel_chat, minsize=200, height=420, stretch="always")

        self._construir_chat(panel_chat, evento_id, nombre_evento)
        return v

    def _mostrar_detalle_seguimiento(self, panel, evento_id, socio_id, nombre, rol):
        """Detalle de avance de una persona — solo lectura (sin botones de edición)."""
        for w in panel.winfo_children(): w.destroy()
        _fs = _config.get("font_scale", 1.0)
        def _sz(n): return max(7, round(n * _fs))

        hdr = tk.Frame(panel, bg=COLORES["primario"], pady=8)
        hdr.pack(fill="x")
        icono = "🎖️" if rol == "Director" else "🔷" if rol == "Coordinador" else "👤"
        tk.Label(hdr, text=f"{icono}  {nombre.upper()}",
                 font=FUENTES["subtitulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()
        tk.Label(hdr, text=rol.upper(), font=("Segoe UI", _sz(7), "bold"),
                 fg=COLORES["acento"], bg=COLORES["primario"]).pack()

        pct_global = self._calcular_pct_global(evento_id, socio_id)
        pct_frame = tk.Frame(panel, bg=COLORES["superficie"], pady=5, padx=12)
        pct_frame.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(pct_frame, text=f"Avance global: {pct_global}%",
                 font=FUENTES["bold"], fg=COLORES["acento"],
                 bg=COLORES["superficie"]).pack(side="left")
        barra_bg = tk.Frame(pct_frame, bg=COLORES["borde"], height=10, width=160)
        barra_bg.pack(side="left", padx=10, pady=2)
        barra_bg.pack_propagate(False)
        ancho_fill = max(2, int(160 * pct_global / 100))
        tk.Frame(barra_bg,
                 bg=COLORES["exito"] if pct_global >= 50 else COLORES["peligro"],
                 height=10, width=ancho_fill).place(x=0, y=0)

        tk.Frame(panel, height=1, bg=COLORES["borde"]).pack(fill="x", padx=8, pady=4)

        lista_frame = tk.Frame(panel, bg=COLORES["fondo"])
        lista_frame.pack(fill="both", expand=True, padx=8, pady=4)
        canv = tk.Canvas(lista_frame, bg=COLORES["fondo"], highlightthickness=0)
        sc   = ttk.Scrollbar(lista_frame, orient="vertical", command=canv.yview)
        inner = tk.Frame(canv, bg=COLORES["fondo"])
        inner.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.create_window((0, 0), window=inner, anchor="nw")
        canv.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        canv.pack(side="left", fill="both", expand=True)

        conn = conectar_db()
        if conn is None:
            tk.Label(inner, text="Sin conexión a PostgreSQL.",
                     font=("Segoe UI", 9), fg=COLORES["peligro"],
                     bg=COLORES["fondo"]).pack(pady=16)
            return
        cur = conn.cursor()
        cur.execute("""SELECT id, descripcion, fecha_limite, estado
                       FROM responsabilidades WHERE evento_id=%s AND socio_id=%s ORDER BY id""",
                    (evento_id, socio_id))
        resps = cur.fetchall(); liberar_db(conn)

        ESTADO_COLORES = {
            "Pendiente":  COLORES["texto_suave"],
            "En curso":   COLORES["acento"],
            "Completado": COLORES["exito"],
        }

        for resp_id, desc, fecha_lim, estado in resps:
            conn2 = conectar_db()
            if conn2 is None: return
            cur2 = conn2.cursor()
            cur2.execute("SELECT COUNT(*), SUM(CASE WHEN completado THEN 1 ELSE 0 END) FROM checklist_items WHERE responsabilidad_id=%s",
                         (resp_id,))
            row_c = cur2.fetchone()
            tot_c = row_c[0] or 0; com_c = row_c[1] or 0
            pct_r = round((com_c / tot_c * 100) if tot_c > 0 else 0)
            cur2.execute("SELECT texto, completado FROM checklist_items WHERE responsabilidad_id=%s ORDER BY id",
                         (resp_id,))
            items = cur2.fetchall(); liberar_db(conn2)

            card = tk.Frame(inner, bg=COLORES["superficie"], relief="flat", bd=1, padx=10, pady=6)
            card.pack(fill="x", pady=3)

            # Título + estado (solo texto, no editable)
            top_row = tk.Frame(card, bg=COLORES["superficie"])
            top_row.pack(fill="x")
            tk.Label(top_row, text=f"📌  {desc[:55]}{'…' if len(desc)>55 else ''}",
                     font=FUENTES["bold"], fg=COLORES["texto"],
                     bg=COLORES["superficie"], anchor="w", justify="left",
                     wraplength=300).pack(side="left", fill="x", expand=True)
            tk.Label(top_row, text=estado,
                     font=("Segoe UI", _sz(7), "bold"),
                     fg=ESTADO_COLORES.get(estado, COLORES["texto_suave"]),
                     bg=COLORES["superficie"]).pack(side="right", padx=4)

            info_row = tk.Frame(card, bg=COLORES["superficie"])
            info_row.pack(fill="x", pady=(2, 4))
            tk.Label(info_row, text=f"📅 {_fmt_fecha(fecha_lim)}",
                     font=("Segoe UI", _sz(7)), fg=COLORES["texto_suave"],
                     bg=COLORES["superficie"]).pack(side="left")
            tk.Label(info_row, text=f"  {pct_r}% checklist",
                     font=("Segoe UI", _sz(7), "bold"),
                     fg=COLORES["exito"] if pct_r >= 50 else COLORES["peligro"],
                     bg=COLORES["superficie"]).pack(side="left")

            # Checklist: solo lectura
            for texto_item, completado in items:
                chk_row = tk.Frame(card, bg=COLORES["superficie2"])
                chk_row.pack(fill="x", pady=1, padx=4)
                marca = "✅" if completado else "⬜"
                col_txt = COLORES["exito"] if completado else COLORES["texto"]
                tk.Label(chk_row, text=f"  {marca}  {texto_item}",
                         font=("Segoe UI", _sz(8)), fg=col_txt,
                         bg=COLORES["superficie2"], anchor="w").pack(anchor="w")

        if not resps:
            tk.Label(inner, text="Sin responsabilidades asignadas.",
                     font=("Segoe UI", _sz(9)), fg=COLORES["texto_suave"],
                     bg=COLORES["fondo"], justify="center").pack(pady=16)

    def _construir_chat(self, parent, evento_id, nombre_evento):
        """Chat tipo WhatsApp con conversación grupal y por persona."""
        from datetime import datetime as _dt
        _fs = _config.get("font_scale", 1.0)
        def _sz(n): return max(7, round(n * _fs))

        # Admin que envía mensajes
        admin_nombre   = _config.get("admin_nombre", "Admin")
        admin_apellido = _config.get("admin_apellido", "")
        remitente_nombre = f"{admin_nombre} {admin_apellido}".strip()

        # ── Obtener o crear conversación grupal ──
        def obtener_conv_grupal():
            conn = conectar_chat_db()
            if conn is None: return
            cur = conn.cursor()
            cur.execute("""SELECT id FROM conversaciones
                           WHERE evento_id=%s AND tipo_conv='grupal'""", (evento_id,))
            row = cur.fetchone()
            if row:
                liberar_db(conn); return row[0]
            cur.execute("""INSERT INTO conversaciones
                           (evento_id, nombre_conv, tipo_conv, participante_a, participante_b)
                           VALUES (%s, %s, 'grupal', 0, NULL) RETURNING id""",
                        (evento_id, nombre_evento))
            cid = cur.fetchone()[0]
            conn.commit(); liberar_chat(conn); return cid

        def obtener_conv_individual(socio_id, nombre_socio):
            conn = conectar_chat_db()
            if conn is None: return
            cur = conn.cursor()
            cur.execute("""SELECT id FROM conversaciones
                           WHERE evento_id=%s AND tipo_conv='individual'
                           AND participante_b=%s""", (evento_id, socio_id))
            row = cur.fetchone()
            if row:
                liberar_chat(conn); return row[0]
            cur.execute("""INSERT INTO conversaciones
                           (evento_id, nombre_conv, tipo_conv, participante_a, participante_b)
                           VALUES (%s, %s, 'individual', 0, %s) RETURNING id""",
                        (evento_id, nombre_socio, socio_id))
            cid = cur.fetchone()[0]
            conn.commit(); liberar_chat(conn); return cid

        # ── Cargar participantes del evento ──
        conn_m = conectar_db()
        if conn_m is None: return
        if conn_m is None: return
        cur_m = conn_m.cursor()
        cur_m.execute("""SELECT m.id, m.nombres, m.apellidos
                         FROM miembros m
                         JOIN evento_participantes ep ON ep.socio_id = m.id
                         WHERE ep.evento_id=%s ORDER BY m.apellidos""", (evento_id,))
        participantes = cur_m.fetchall(); liberar_db(conn_m)

        # ── Estructura del chat ──
        # Panel izquierdo: lista de conversaciones
        # Panel derecho:   burbujas + input
        chat_paned = tk.PanedWindow(parent, orient="horizontal",
                                     bg=COLORES["borde"], sashwidth=4,
                                     sashrelief="flat", handlesize=0)
        chat_paned.pack(fill="both", expand=True)

        # ── Lista de conversaciones ──
        lista_conv_f = tk.Frame(chat_paned, bg=COLORES["superficie"], width=180)
        chat_paned.add(lista_conv_f, minsize=160, width=200, stretch="never")

        tk.Label(lista_conv_f, text="💬  CHATS",
                 font=("Segoe UI", _sz(9), "bold"), fg=COLORES["blanco"],
                 bg=COLORES["primario"], pady=8).pack(fill="x")

        conv_scroll_f = tk.Frame(lista_conv_f, bg=COLORES["superficie"])
        conv_scroll_f.pack(fill="both", expand=True)

        conv_canvas = tk.Canvas(conv_scroll_f, bg=COLORES["superficie"],
                                 highlightthickness=0, width=180)
        conv_sc = ttk.Scrollbar(conv_scroll_f, orient="vertical", command=conv_canvas.yview)
        conv_inner = tk.Frame(conv_canvas, bg=COLORES["superficie"])
        conv_inner.bind("<Configure>", lambda e: conv_canvas.configure(scrollregion=conv_canvas.bbox("all")))
        conv_canvas.create_window((0, 0), window=conv_inner, anchor="nw")
        conv_canvas.configure(yscrollcommand=conv_sc.set)
        conv_sc.pack(side="right", fill="y")
        conv_canvas.pack(side="left", fill="both", expand=True)

        # ── Panel de burbujas ──
        burbuja_f = tk.Frame(chat_paned, bg=COLORES["fondo"])
        chat_paned.add(burbuja_f, minsize=220, stretch="always")

        # Header del chat activo
        chat_hdr = tk.Frame(burbuja_f, bg=COLORES["primario_dark"], pady=6)
        chat_hdr.pack(fill="x")
        lbl_chat_titulo = tk.Label(chat_hdr, text="Seleccioná una conversación",
                                    font=FUENTES["bold"], fg=COLORES["blanco"],
                                    bg=COLORES["primario_dark"])
        lbl_chat_titulo.pack(side="left", padx=10)

        # Área de mensajes scrollable
        msg_outer = tk.Frame(burbuja_f, bg=COLORES["fondo"])
        msg_outer.pack(fill="both", expand=True)

        msg_canvas = tk.Canvas(msg_outer, bg=COLORES["fondo"], highlightthickness=0)
        msg_sc = ttk.Scrollbar(msg_outer, orient="vertical", command=msg_canvas.yview)
        msg_inner = tk.Frame(msg_canvas, bg=COLORES["fondo"])
        msg_inner.bind("<Configure>", lambda e: msg_canvas.configure(scrollregion=msg_canvas.bbox("all")))
        msg_canvas.create_window((0, 0), window=msg_inner, anchor="nw")
        msg_canvas.configure(yscrollcommand=msg_sc.set)
        msg_sc.pack(side="right", fill="y")
        msg_canvas.pack(side="left", fill="both", expand=True)

        # Input de texto
        input_f = tk.Frame(burbuja_f, bg=COLORES["superficie"], pady=6, padx=6)
        input_f.pack(fill="x", side="bottom")
        ent_msg = ttk.Entry(input_f, font=FUENTES["normal"])
        ent_msg.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

        # Estado actual del chat
        _estado = {"conv_id": None}

        def cargar_mensajes(conv_id):
            """Renderiza las burbujas de la conversación activa."""
            for w in msg_inner.winfo_children(): w.destroy()
            conn = conectar_chat_db()
            if conn is None: return
            cur = conn.cursor()
            cur.execute("""SELECT id, remitente_nombre, texto, timestamp, leido, borrado, borrado_en
                           FROM mensajes
                           WHERE conversacion_id=%s AND borrado=0
                           ORDER BY timestamp ASC""", (conv_id,))
            mensajes = cur.fetchall()
            # Marcar como leídos los mensajes que no son del admin
            cur.execute("""UPDATE mensajes SET leido=1
                           WHERE conversacion_id=%s AND remitente_nombre != %s AND leido=0""",
                        (conv_id, remitente_nombre))
            conn.commit(); liberar_db(conn)

            for msg_id, rem_nom, texto, ts, leido, borrado, borrado_en in mensajes:
                es_mio = (rem_nom == remitente_nombre)
                alinear = "e" if es_mio else "w"
                bg_burbuja = COLORES["primario"] if es_mio else COLORES["superficie"]
                fg_burbuja = COLORES["blanco"]   if es_mio else COLORES["texto"]

                fila = tk.Frame(msg_inner, bg=COLORES["fondo"])
                fila.pack(fill="x", padx=8, pady=3, anchor=alinear)

                burbuja = tk.Frame(fila, bg=bg_burbuja, padx=10, pady=6)
                burbuja.pack(side="right" if es_mio else "left")

                if not es_mio:
                    tk.Label(burbuja, text=rem_nom,
                             font=("Segoe UI", _sz(7), "bold"),
                             fg=COLORES["acento"], bg=bg_burbuja).pack(anchor="w")

                tk.Label(burbuja, text=texto,
                         font=FUENTES["normal"], fg=fg_burbuja,
                         bg=bg_burbuja, wraplength=240,
                         justify="left" if not es_mio else "right").pack(anchor="w" if not es_mio else "e")

                # Hora + estado leído
                try:
                    # PG devuelve datetime objects; strings vienen del legado
                    if hasattr(ts, "strftime"):
                        ts_fmt = ts.strftime("%d/%m  %H:%M")
                    else:
                        ts_fmt = _dt.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m  %H:%M")
                except Exception:
                    ts_fmt = str(ts)

                leido_ico = "  ●" if not leido else "  ✔"
                leido_col = COLORES["texto_suave"] if not leido else COLORES["exito"]
                info_txt  = f"{ts_fmt}{leido_ico if es_mio else ''}"
                tk.Label(burbuja, text=info_txt,
                         font=("Segoe UI", _sz(6)), fg=leido_col if es_mio else COLORES["texto_suave"],
                         bg=bg_burbuja).pack(anchor="e")

                # Botón eliminar (solo si tiene menos de 30 min)
                if es_mio:
                    try:
                        if hasattr(ts, "strftime"):
                            ts_dt = ts
                        else:
                            ts_dt = _dt.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S")
                        diff  = (_dt.now() - ts_dt).total_seconds()
                        puede_borrar = diff < 1800
                    except Exception:
                        puede_borrar = False

                    if puede_borrar:
                        def borrar_msg(mid=msg_id):
                            conn2 = conectar_chat_db()
                            if conn2 is None: return
                            cur2 = conn2.cursor()
                            now_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
                            cur2.execute("""UPDATE mensajes SET borrado=1, borrado_en=%s
                                           WHERE id=%s""", (now_str, mid))
                            conn2.commit(); liberar_db(conn2)
                            cargar_mensajes(_estado["conv_id"])

                        tk.Button(burbuja, text="🗑", font=("Segoe UI", _sz(6)),
                                   fg=COLORES["texto_suave"], bg=bg_burbuja,
                                   relief="flat", bd=0, cursor="hand2",
                                   command=borrar_msg).pack(anchor="e")

            # Scroll al final
            msg_canvas.update_idletasks()
            msg_canvas.yview_moveto(1.0)

        def activar_conv(conv_id, titulo):
            _estado["conv_id"] = conv_id
            lbl_chat_titulo.config(text=titulo)
            cargar_mensajes(conv_id)
            construir_lista_conv()  # refrescar puntos de no leído

        def enviar_mensaje(event=None):
            texto = ent_msg.get().strip()
            if not texto or not _estado["conv_id"]: return
            now_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = conectar_chat_db()
            if conn is None:
                messagebox.showwarning("Sin conexión", "No hay conexión al servidor de chat.")
                return
            cur = conn.cursor()
            cur.execute("""INSERT INTO mensajes
                           (conversacion_id, evento_id, remitente_nombre,
                            destinatario_id, texto, timestamp, leido, borrado)
                           VALUES (%s, %s, %s, NULL, %s, %s, 0, 0)""",
                        (_estado["conv_id"], evento_id, remitente_nombre, texto, now_str))
            conn.commit(); liberar_db(conn)
            ent_msg.delete(0, "end")
            cargar_mensajes(_estado["conv_id"])

        ent_msg.bind("<Return>", enviar_mensaje)
        ttk.Button(input_f, text="➤  Enviar",
                   style="IKA.TButton", command=enviar_mensaje).pack(side="right")

        def no_leidos_conv(conv_id):
            conn = conectar_chat_db()
            if conn is None: return
            cur = conn.cursor()
            cur.execute("""SELECT COUNT(*) FROM mensajes
                           WHERE conversacion_id=%s AND leido=0
                           AND remitente_nombre != %s AND borrado=0""",
                        (conv_id, remitente_nombre))
            n = cur.fetchone()[0]; liberar_db(conn); return n

        def construir_lista_conv():
            """Renderiza la lista lateral de conversaciones."""
            for w in conv_inner.winfo_children(): w.destroy()

            # ── Grupo ──
            cid_grupo = obtener_conv_grupal()
            n_grupo   = no_leidos_conv(cid_grupo)
            activo_g  = (_estado["conv_id"] == cid_grupo)
            bg_g = COLORES["primario"] if activo_g else COLORES["superficie2"]
            fg_g = COLORES["blanco"]   if activo_g else COLORES["texto"]

            row_g = tk.Frame(conv_inner, bg=bg_g, pady=8, padx=8, cursor="hand2")
            row_g.pack(fill="x")
            lbl_g = tk.Label(row_g, text=f"👥  {nombre_evento[:18]}",
                              font=("Segoe UI", _sz(8), "bold"), fg=fg_g, bg=bg_g, anchor="w")
            lbl_g.pack(side="left", fill="x", expand=True)
            if n_grupo > 0:
                badge_g = tk.Label(row_g, text=str(n_grupo),
                                    font=("Segoe UI", _sz(7), "bold"),
                                    fg=COLORES["blanco"], bg=COLORES["peligro"],
                                    padx=5, pady=1)
                badge_g.pack(side="right")
            for w in (row_g, lbl_g):
                w.bind("<Button-1>", lambda e, c=cid_grupo, t=f"👥 {nombre_evento}": activar_conv(c, t))

            # Separador
            tk.Frame(conv_inner, height=1, bg=COLORES["borde"]).pack(fill="x")
            tk.Label(conv_inner, text="  PERSONAS",
                     font=("Segoe UI", _sz(7), "bold"),
                     fg=COLORES["texto_suave"], bg=COLORES["superficie"],
                     anchor="w").pack(fill="x", pady=(4, 2))

            # ── Individual por participante ──
            for sid, nom, ape in participantes:
                nombre_p = f"{nom} {ape}"
                cid_p    = obtener_conv_individual(sid, nombre_p)
                n_p      = no_leidos_conv(cid_p)
                activo_p = (_estado["conv_id"] == cid_p)
                bg_p = COLORES["primario"] if activo_p else COLORES["superficie"]
                fg_p = COLORES["blanco"]   if activo_p else COLORES["texto"]

                row_p = tk.Frame(conv_inner, bg=bg_p, pady=6, padx=8, cursor="hand2")
                row_p.pack(fill="x")
                lbl_p = tk.Label(row_p, text=f"👤  {nombre_p[:18]}",
                                  font=("Segoe UI", _sz(8)), fg=fg_p, bg=bg_p, anchor="w")
                lbl_p.pack(side="left", fill="x", expand=True)
                if n_p > 0:
                    badge_p = tk.Label(row_p, text=str(n_p),
                                        font=("Segoe UI", _sz(7), "bold"),
                                        fg=COLORES["blanco"], bg=COLORES["peligro"],
                                        padx=5, pady=1)
                    badge_p.pack(side="right")
                titulo_p = f"👤 {nombre_p}"
                for w in (row_p, lbl_p):
                    w.bind("<Button-1>", lambda e, c=cid_p, t=titulo_p: activar_conv(c, t))

        # Inicializar lista de conversaciones
        construir_lista_conv()

    # ── JERARQUÍA ────────────────────────────────────────────────────────────
    def ventana_jerarquia(self, evento_id, nombre_evento):
        v = hacer_ventana(self.root, f"Jerarquía · {nombre_evento}", 1100, 720)
        v.resizable(True, True)

        hdr = tk.Frame(v, bg=COLORES["primario"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🗂️  JERARQUÍA DEL EVENTO  —  {nombre_evento.upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        # PanedWindow para que el usuario pueda arrastrar el divisor
        paned = tk.PanedWindow(v, orient="horizontal",
                                bg=COLORES["borde"],
                                sashwidth=6, sashrelief="flat",
                                handlesize=0)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        # ── PANEL IZQUIERDO: organigrama ──
        panel_izq = tk.Frame(paned, bg=COLORES["fondo"])
        paned.add(panel_izq, minsize=300, width=480, stretch="always")

        tk.Label(panel_izq, text="ORGANIGRAMA", font=FUENTES["small"],
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(4, 2), padx=4)

        btn_asignar = ttk.Button(panel_izq, text="⚙️  Asignar Roles",
                                  style="Gold.TButton",
                                  command=lambda: self._ventana_asignar_roles(evento_id, lambda: redibujar()))
        btn_asignar.pack(anchor="w", pady=(0, 6), padx=4)

        canvas_frame = tk.Frame(panel_izq, bg=COLORES["superficie"], relief="flat", bd=1)
        canvas_frame.pack(fill="both", expand=True)

        canvas_org = tk.Canvas(canvas_frame, bg=COLORES["superficie"],
                                highlightthickness=0, cursor="hand2")
        sc_org_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas_org.yview)
        sc_org_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas_org.xview)
        canvas_org.configure(yscrollcommand=sc_org_y.set, xscrollcommand=sc_org_x.set)
        sc_org_x.pack(side="bottom", fill="x")
        sc_org_y.pack(side="right", fill="y")
        canvas_org.pack(side="left", fill="both", expand=True)

        # ── PANEL DERECHO: detalle persona ──
        panel_der = tk.Frame(paned, bg=COLORES["fondo"])
        paned.add(panel_der, minsize=280, stretch="always")

        self._det_frame = tk.Frame(panel_der, bg=COLORES["fondo"])
        self._det_frame.pack(fill="both", expand=True)

        lbl_hint = tk.Label(self._det_frame,
                             text="← Hacé clic en un nodo del organigrama\npara ver el detalle",
                             font=FUENTES["normal"], fg=COLORES["texto_suave"],
                             bg=COLORES["fondo"], justify="center")
        lbl_hint.pack(expand=True)

        def redibujar():
            self._dibujar_organigrama(canvas_org, evento_id,
                                       lambda sid, nombre, rol: self._mostrar_detalle_persona(
                                           panel_der, evento_id, sid, nombre, rol, redibujar))

        redibujar()
        return v

    def _dibujar_organigrama(self, canvas, evento_id, on_click):
        canvas.delete("all")
        conn = conectar_db()
        if conn is None: return
        cur = conn.cursor()

        cur.execute("""SELECT jr.socio_id, m.nombres, m.apellidos, jr.rol, jr.coordinador_id
                       FROM jerarquia_roles jr
                       JOIN miembros m ON m.id = jr.socio_id
                       WHERE jr.evento_id=%s""", (evento_id,))
        rows = cur.fetchall()
        liberar_db(conn)

        if not rows:
            canvas.create_text(200, 120, text="Sin roles asignados.\nUsá '⚙️ Asignar Roles'.",
                                font=("Segoe UI", 10), fill=COLORES["texto_suave"], justify="center")
            return

        # Organizar datos por rol
        directores      = []         # [(sid, nombre)]
        coords_by_dir   = {}         # dir_sid -> [(csid, cnombre)]
        colabs_by_coord = {}         # coord_sid -> [(lsid, lnombre)]
        sin_dir         = []         # coordinadores sin director
        sin_coord       = []         # colaboradores sin coordinador

        dir_ids   = set()
        coord_ids = set()

        for r in rows:
            sid, nom, ape, rol, dep_id = r
            nombre = f"{nom} {ape}"
            if rol == "Director":
                directores.append((sid, nombre))
                dir_ids.add(sid)
                coords_by_dir[sid] = []
            elif rol == "Coordinador":
                coord_ids.add(sid)
                colabs_by_coord[sid] = []

        for r in rows:
            sid, nom, ape, rol, dep_id = r
            nombre = f"{nom} {ape}"
            if rol == "Coordinador":
                if dep_id and dep_id in dir_ids:
                    coords_by_dir[dep_id].append((sid, nombre))
                else:
                    sin_dir.append((sid, nombre))
            elif rol == "Colaborador":
                if dep_id and dep_id in coord_ids:
                    colabs_by_coord[dep_id].append((sid, nombre))
                else:
                    sin_coord.append((sid, nombre))

        col_dir   = COLORES["primario"]
        col_coord = COLORES["acento"]
        col_colab = COLORES["superficie2"]
        txt_dir   = COLORES["blanco"]
        txt_coord = COLORES["texto"]
        txt_colab = COLORES["texto"]

        _fs = _config.get("font_scale", 1.0)
        def _sz(n): return max(7, round(n * _fs))

        NODE_W    = max(160, round(160 * _fs))
        NODE_H    = max(54,  round(54  * _fs))
        PAD_X     = max(40,  round(40  * _fs))
        PAD_Y     = max(60,  round(60  * _fs))
        COLAB_GAP = max(24,  round(24  * _fs))
        START_X   = 30
        START_Y   = 20
        PCT_H     = max(18,  round(18  * _fs))

        def nodo(x, y, texto, bg, fg, sid, rol_n):
            rx1, ry1, rx2, ry2 = x, y, x + NODE_W, y + NODE_H
            canvas.create_rectangle(rx1+3, ry1+3, rx2+3, ry2+3,
                                     fill="#BBBBBB", outline="", tags="sombra")
            r_id = canvas.create_rectangle(rx1, ry1, rx2, ry2,
                                            fill=bg, outline=COLORES["borde"],
                                            width=2, tags=f"nodo_{sid}")
            canvas.create_rectangle(rx1, ry1, rx1+6, ry2,
                                     fill=COLORES["primario_dark"] if bg == col_dir else COLORES["primario"],
                                     outline="", tags=f"nodo_{sid}")
            nombre_corto = texto if len(texto) <= 22 else texto[:20] + "…"
            canvas.create_text(rx1 + NODE_W // 2, ry1 + round(NODE_H * 0.33),
                                text=nombre_corto,
                                font=("Segoe UI", _sz(9), "bold"),
                                fill=fg, tags=f"nodo_{sid}")
            canvas.create_text(rx1 + NODE_W // 2, ry1 + round(NODE_H * 0.67),
                                text=rol_n.upper(),
                                font=("Segoe UI", _sz(8)),
                                fill=fg if bg == col_dir else COLORES["texto_suave"],
                                tags=f"nodo_{sid}")

            def click_handler(e, s=sid, n=texto, r=rol_n):
                on_click(s, n, r)
            canvas.tag_bind(f"nodo_{sid}", "<Button-1>", click_handler)
            canvas.tag_bind(f"nodo_{sid}", "<Enter>",
                             lambda e, rid=r_id: canvas.itemconfig(rid, width=3))
            canvas.tag_bind(f"nodo_{sid}", "<Leave>",
                             lambda e, rid=r_id: canvas.itemconfig(rid, width=2))
            # retorna: centro_x, bottom_y, top_y
            return rx1 + NODE_W // 2, ry2, ry1

        def linea(x1, y1, x2, y2):
            # Línea en codo: baja vertical, luego horizontal, luego baja
            mid_y = (y1 + y2) // 2
            canvas.create_line(x1, y1, x1, mid_y,
                                fill=COLORES["acento"], width=2, dash=(5, 3))
            canvas.create_line(x1, mid_y, x2, mid_y,
                                fill=COLORES["acento"], width=2, dash=(5, 3))
            canvas.create_line(x2, mid_y, x2, y2,
                                fill=COLORES["acento"], width=2, dash=(5, 3))

        # ── Calcular ancho de cada columna de coordinador ──
        # Cada columna ocupa NODE_W, centrada sobre sus colaboradores
        # (todos los colaboradores tienen el mismo ancho NODE_W, así que la columna = NODE_W)

        col_width = NODE_W + PAD_X
        dir_y     = START_Y
        cur_x     = START_X  # cursor X global para ir posicionando árboles

        # ── Dibujar un árbol por director ──
        for dsid, dnombre in directores:
            mis_coords = coords_by_dir.get(dsid, [])

            # Cuántas columnas ocupa este árbol
            n_cols = max(len(mis_coords), 1)
            arbol_w = n_cols * col_width - PAD_X

            # Director centrado sobre sus coordinadores
            dir_cx = cur_x + arbol_w // 2
            dir_x  = dir_cx - NODE_W // 2
            cx_d, bot_d, _ = nodo(dir_x, dir_y, dnombre,
                                   col_dir, txt_dir, dsid, "Director")
            pct_d = self._calcular_pct_global(evento_id, dsid)
            canvas.create_text(dir_cx, dir_y + NODE_H + 10,
                                text=f"{pct_d}% completado",
                                font=("Segoe UI", _sz(8)), fill=COLORES["texto_suave"])

            coord_y = dir_y + NODE_H + PCT_H + PAD_Y

            # Coordinadores de este director
            for i, (csid, cnombre) in enumerate(mis_coords):
                col_cx = cur_x + i * col_width + NODE_W // 2
                col_x  = col_cx - NODE_W // 2

                cx_c, bot_c, top_c = nodo(col_x, coord_y, cnombre,
                                           col_coord, txt_coord, csid, "Coordinador")
                pct_c = self._calcular_pct_global(evento_id, csid)
                canvas.create_text(col_cx, coord_y + NODE_H + 10,
                                    text=f"{pct_c}% completado",
                                    font=("Segoe UI", _sz(8)), fill=COLORES["texto_suave"])

                # Línea director → coordinador
                linea(dir_cx, bot_d, col_cx, top_c)

                # Colaboradores de este coordinador
                colabs = colabs_by_coord.get(csid, [])
                colab_start_y = coord_y + NODE_H + PCT_H + PAD_Y
                for j, (lsid, lnombre) in enumerate(colabs):
                    ly = colab_start_y + j * (NODE_H + COLAB_GAP + PCT_H)
                    lx = col_cx - NODE_W // 2
                    cx_l, bot_l, top_l = nodo(lx, ly, lnombre,
                                               col_colab, txt_colab, lsid, "Colaborador")
                    pct_l = self._calcular_pct_global(evento_id, lsid)
                    canvas.create_text(col_cx, ly + NODE_H + 10,
                                        text=f"{pct_l}% completado",
                                        font=("Segoe UI", _sz(8)), fill=COLORES["texto_suave"])
                    prev_y = bot_c if j == 0 else colab_start_y + (j-1)*(NODE_H+COLAB_GAP+PCT_H) + NODE_H
                    canvas.create_line(col_cx, prev_y, col_cx, top_l,
                                        fill=COLORES["acento"], width=2, dash=(5, 3))

            # Avanzar cursor X para el próximo árbol (separador extra entre árboles)
            cur_x += arbol_w + PAD_X * 3

        # ── Coordinadores sin director ──
        coord_y_sd = dir_y + NODE_H + PCT_H + PAD_Y
        for csid, cnombre in sin_dir:
            col_cx = cur_x + NODE_W // 2
            col_x  = cur_x
            cx_c, bot_c, top_c = nodo(col_x, coord_y_sd, cnombre,
                                       col_coord, txt_coord, csid, "Coordinador")
            canvas.create_text(col_cx, coord_y_sd + NODE_H + 10,
                                text="Sin director",
                                font=("Segoe UI", _sz(8)), fill=COLORES["peligro"])
            colabs = colabs_by_coord.get(csid, [])
            colab_y = coord_y_sd + NODE_H + PCT_H + PAD_Y
            for j, (lsid, lnombre) in enumerate(colabs):
                ly = colab_y + j * (NODE_H + COLAB_GAP + PCT_H)
                nodo(col_x, ly, lnombre, col_colab, txt_colab, lsid, "Colaborador")
                prev_y = bot_c if j == 0 else colab_y + (j-1)*(NODE_H+COLAB_GAP+PCT_H) + NODE_H
                canvas.create_line(col_cx, prev_y, col_cx, ly,
                                    fill=COLORES["acento"], width=2, dash=(5, 3))
            cur_x += col_width

        # ── Colaboradores sin coordinador ──
        sc_y = dir_y + NODE_H + PCT_H + PAD_Y * 2 + NODE_H + PCT_H
        for k, (lsid, lnombre) in enumerate(sin_coord):
            lx = cur_x + k * col_width
            nodo(lx, sc_y, lnombre, col_colab, txt_colab, lsid, "Colaborador")
            canvas.create_text(lx + NODE_W // 2, sc_y + NODE_H + 10,
                                text="Sin coordinador",
                                font=("Segoe UI", _sz(8)), fill=COLORES["peligro"])

        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=(bbox[0]-10, bbox[1]-10,
                                            bbox[2]+10, bbox[3]+10))

    def _calcular_pct_global(self, evento_id, socio_id):
        """Porcentaje global de avance de una persona en el evento"""
        conn = conectar_db()
        if conn is None: return
        cur = conn.cursor()
        cur.execute("SELECT id FROM responsabilidades WHERE evento_id=%s AND socio_id=%s",
                    (evento_id, socio_id))
        resp_ids = [r[0] for r in cur.fetchall()]
        if not resp_ids:
            liberar_db(conn); return 0
        totales = 0; completados = 0
        for rid in resp_ids:
            cur.execute("SELECT COUNT(*), SUM(CASE WHEN completado THEN 1 ELSE 0 END) FROM checklist_items WHERE responsabilidad_id=%s", (rid,))
            row = cur.fetchone()
            t = row[0] or 0
            c = row[1] or 0
            if t > 0:
                totales += t; completados += c
        liberar_db(conn)
        return round((completados / totales * 100) if totales > 0 else 0)

    def _ventana_asignar_roles(self, evento_id, callback):
        v = hacer_ventana(self.root, "Asignar Roles", 560, 580, modal=True)
        hdr = tk.Frame(v, bg=COLORES["primario_dark"], pady=10)
        _fs = _config.get("font_scale", 1.0)
        def _sz(n): return max(7, round(n * _fs))
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙️  ASIGNAR ROLES AL EVENTO",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario_dark"]).pack()

        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            v.destroy()
            return
        cur = conn.cursor()
        cur.execute("""SELECT m.id, m.nombres, m.apellidos
                       FROM miembros m
                       JOIN evento_participantes ep ON ep.socio_id = m.id
                       WHERE ep.evento_id=%s ORDER BY m.apellidos""", (evento_id,))
        participantes = cur.fetchall()

        cur.execute("SELECT socio_id, rol, coordinador_id FROM jerarquia_roles WHERE evento_id=%s",
                    (evento_id,))
        roles_existentes = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        liberar_db(conn)

        body = tk.Frame(v, bg=COLORES["fondo"], padx=20, pady=10)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Asigná un rol a cada participante. Solo uno por persona.",
                 font=("Segoe UI", _sz(8)), fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(0, 8))

        # Scroll
        c_frame = tk.Frame(body, bg=COLORES["fondo"])
        c_frame.pack(fill="both", expand=True)
        canv = tk.Canvas(c_frame, bg=COLORES["fondo"], highlightthickness=0)
        sc = ttk.Scrollbar(c_frame, orient="vertical", command=canv.yview)
        inner = tk.Frame(canv, bg=COLORES["fondo"])
        inner.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.create_window((0, 0), window=inner, anchor="nw")
        canv.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        canv.pack(side="left", fill="both", expand=True)

        roles_vars    = {}   # socio_id -> StringVar(rol)
        dep_vars      = {}   # socio_id -> StringVar(nombre del superior)
        combos_rol    = {}   # socio_id -> Combobox rol
        filas_widgets = {}   # socio_id -> (lbl, combo_dep)

        # Mapa id->nombre para lookup rápido
        nombre_por_id = {p[0]: f"{p[1]} {p[2]}" for p in participantes}

        # ── Construir todas las filas primero ──
        for i, (sid, nom, ape) in enumerate(participantes):
            bg = COLORES["superficie"] if i % 2 == 0 else COLORES["superficie2"]
            row = tk.Frame(inner, bg=bg, pady=6, padx=10)
            row.pack(fill="x", pady=1)

            tk.Label(row, text=f"{nom} {ape}", font=FUENTES["bold"],
                     fg=COLORES["texto"], bg=bg, width=22, anchor="w").pack(side="left")

            rol_existente, dep_existente = roles_existentes.get(sid, ("—", None))
            var_rol = tk.StringVar(value=rol_existente)
            roles_vars[sid] = var_rol

            combo_rol = ttk.Combobox(row, textvariable=var_rol,
                                      values=["—", "Director", "Coordinador", "Colaborador"],
                                      state="readonly", width=13, font=FUENTES["normal"])
            combo_rol.pack(side="left", padx=6)
            combos_rol[sid] = combo_rol

            var_dep = tk.StringVar(value="—")
            dep_vars[sid] = var_dep

            # Pre-cargar nombre del superior si existe
            if dep_existente and dep_existente in nombre_por_id:
                var_dep.set(nombre_por_id[dep_existente])

            lbl_dep   = tk.Label(row, text="", font=("Segoe UI", _sz(7)),
                                  fg=COLORES["texto_suave"], bg=bg)
            combo_dep = ttk.Combobox(row, textvariable=var_dep,
                                      values=["—"], state="readonly",
                                      width=18, font=("Segoe UI", _sz(8)))
            filas_widgets[sid] = (lbl_dep, combo_dep)

        def actualizar_dep(s, evento=None):
            rol_sel = roles_vars[s].get()
            lbl, cb = filas_widgets[s]
            lbl.pack_forget(); cb.pack_forget()
            if rol_sel == "Coordinador":
                dirs = [nombre_por_id[p[0]] for p in participantes
                        if roles_vars[p[0]].get() == "Director" and p[0] != s]
                cb.config(values=["—"] + dirs)
                if dep_vars[s].get() not in dirs:
                    dep_vars[s].set("—")
                lbl.config(text="Director:")
                lbl.pack(side="left")
                cb.pack(side="left", padx=4)
            elif rol_sel == "Colaborador":
                coords = [nombre_por_id[p[0]] for p in participantes
                          if roles_vars[p[0]].get() == "Coordinador" and p[0] != s]
                cb.config(values=["—"] + coords)
                if dep_vars[s].get() not in coords:
                    dep_vars[s].set("—")
                lbl.config(text="Coordinador:")
                lbl.pack(side="left")
                cb.pack(side="left", padx=4)
            else:
                dep_vars[s].set("—")

        # Bind cambio de rol
        for sid, cb_rol in combos_rol.items():
            cb_rol.bind("<<ComboboxSelected>>", lambda e, s=sid: actualizar_dep(s))

        # ── Actualizar selectores DESPUÉS de construir todas las filas ──
        # Orden importa: directores → coordinadores → colaboradores
        for orden_rol in ["Director", "Coordinador", "Colaborador", "—"]:
            for sid in roles_vars:
                if roles_vars[sid].get() == orden_rol:
                    actualizar_dep(sid)

        def guardar_roles():
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión",
                    "No hay conexión a PostgreSQL.\n"
                    "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                return
            cur = conn.cursor()
            cur.execute("DELETE FROM jerarquia_roles WHERE evento_id=%s", (evento_id,))
            for sid, var_rol in roles_vars.items():
                rol = var_rol.get()
                if rol == "—": continue
                dep_nombre = dep_vars[sid].get()
                dep_id = None
                if dep_nombre != "—":
                    match = next((p[0] for p in participantes
                                  if f"{p[1]} {p[2]}" == dep_nombre), None)
                    dep_id = match
                cur.execute("""INSERT INTO jerarquia_roles
                               (evento_id, socio_id, rol, coordinador_id) VALUES (%s,%s,%s,%s)
                               ON CONFLICT (evento_id, socio_id) DO UPDATE
                               SET rol=EXCLUDED.rol, coordinador_id=EXCLUDED.coordinador_id""",
                            (evento_id, sid, rol, dep_id))
            conn.commit(); liberar_db(conn)
            callback()
            v.destroy()

        def resetear_roles():
            if messagebox.askyesno("Resetear",
                "¿Borrar todos los roles, responsabilidades y checklists del evento?\n\nEsta acción no se puede deshacer."):
                conn = conectar_db()
                if conn is None:
                    messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                    return
                cur = conn.cursor()
                # Obtener IDs de responsabilidades del evento para borrar sus checklist items
                cur.execute("SELECT id FROM responsabilidades WHERE evento_id=%s", (evento_id,))
                resp_ids = [r[0] for r in cur.fetchall()]
                for rid in resp_ids:
                    cur.execute("DELETE FROM checklist_items WHERE responsabilidad_id=%s", (rid,))
                cur.execute("DELETE FROM responsabilidades WHERE evento_id=%s", (evento_id,))
                cur.execute("DELETE FROM jerarquia_roles WHERE evento_id=%s", (evento_id,))
                conn.commit(); liberar_db(conn)
                for sid in roles_vars:
                    roles_vars[sid].set("—")
                    dep_vars[sid].set("—")
                    actualizar_dep(sid)

        btn_row = tk.Frame(v, bg=COLORES["fondo"])
        btn_row.pack(pady=10, padx=20, fill="x")
        ttk.Button(btn_row, text="💾  GUARDAR ROLES",
                   style="IKA.TButton", command=guardar_roles).pack(side="left", fill="x", expand=True, padx=(0,8))
        ttk.Button(btn_row, text="🗑️  RESETEAR TODO",
                   style="Danger.TButton", command=resetear_roles).pack(side="left")

    def _mostrar_detalle_persona(self, panel, evento_id, socio_id, nombre, rol, redibujar):
        # Limpiar panel derecho
        for w in panel.winfo_children(): w.destroy()
        _fs = _config.get("font_scale", 1.0)
        def _sz(n): return max(7, round(n * _fs))

        hdr = tk.Frame(panel, bg=COLORES["primario"], pady=10)
        hdr.pack(fill="x")
        icono = "🎖️" if rol == "Director" else "🔷" if rol == "Coordinador" else "👤"
        tk.Label(hdr, text=f"{icono}  {nombre.upper()}",
                 font=FUENTES["subtitulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()
        tk.Label(hdr, text=rol.upper(), font=("Segoe UI", _sz(7), "bold"),
                 fg=COLORES["acento"], bg=COLORES["primario"]).pack()

        # Porcentaje global
        pct_global = self._calcular_pct_global(evento_id, socio_id)
        pct_frame = tk.Frame(panel, bg=COLORES["superficie"], pady=6, padx=12)
        pct_frame.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(pct_frame, text=f"Avance global: {pct_global}%",
                 font=FUENTES["bold"], fg=COLORES["acento"],
                 bg=COLORES["superficie"]).pack(side="left")

        # Barra de progreso
        barra_bg = tk.Frame(pct_frame, bg=COLORES["borde"], height=10, width=160)
        barra_bg.pack(side="left", padx=10, pady=2)
        barra_bg.pack_propagate(False)
        ancho_fill = max(2, int(160 * pct_global / 100))
        tk.Frame(barra_bg, bg=COLORES["exito"] if pct_global >= 50 else COLORES["peligro"],
                 height=10, width=ancho_fill).place(x=0, y=0)

        # Botón agregar responsabilidad
        tk.Frame(panel, height=1, bg=COLORES["borde"]).pack(fill="x", padx=10, pady=6)
        top_btns = tk.Frame(panel, bg=COLORES["fondo"])
        top_btns.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Button(top_btns, text="➕  Agregar Responsabilidad",
                   style="IKA.TButton",
                   command=lambda: self._ventana_agregar_resp(
                       evento_id, socio_id, nombre, rol,
                       lambda: self._mostrar_detalle_persona(panel, evento_id, socio_id, nombre, rol, redibujar)
                   )).pack(side="left")

        # Lista de responsabilidades
        lista_frame = tk.Frame(panel, bg=COLORES["fondo"])
        lista_frame.pack(fill="both", expand=True, padx=10, pady=4)

        canv = tk.Canvas(lista_frame, bg=COLORES["fondo"], highlightthickness=0)
        sc = ttk.Scrollbar(lista_frame, orient="vertical", command=canv.yview)
        inner = tk.Frame(canv, bg=COLORES["fondo"])
        inner.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.create_window((0, 0), window=inner, anchor="nw")
        canv.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        canv.pack(side="left", fill="both", expand=True)

        conn = conectar_db()
        if conn is None:
            tk.Label(inner, text="Sin conexión a PostgreSQL.",
                     font=("Segoe UI", 9), fg=COLORES["peligro"],
                     bg=COLORES["fondo"]).pack(pady=16)
            return
        cur = conn.cursor()
        cur.execute("""SELECT id, descripcion, fecha_limite, estado
                       FROM responsabilidades WHERE evento_id=%s AND socio_id=%s ORDER BY id""",
                    (evento_id, socio_id))
        resps = cur.fetchall(); liberar_db(conn)

        ESTADOS = ["Pendiente", "En curso", "Completado"]
        ESTADO_COLORES = {
            "Pendiente":  COLORES["texto_suave"],
            "En curso":   COLORES["acento"],
            "Completado": COLORES["exito"],
        }

        def refrescar_det():
            self._mostrar_detalle_persona(panel, evento_id, socio_id, nombre, rol, redibujar)
            redibujar()

        for resp_id, desc, fecha_lim, estado in resps:
            # Calcular % de esta responsabilidad
            conn2 = conectar_db()
            if conn2 is None: return
            cur2 = conn2.cursor()
            cur2.execute("SELECT COUNT(*), SUM(CASE WHEN completado THEN 1 ELSE 0 END) FROM checklist_items WHERE responsabilidad_id=%s",
                         (resp_id,))
            row_c = cur2.fetchone()
            tot_c = row_c[0] or 0
            com_c = row_c[1] or 0
            pct_r = round((com_c / tot_c * 100) if tot_c > 0 else 0)
            cur2.execute("SELECT id, texto, completado FROM checklist_items WHERE responsabilidad_id=%s ORDER BY id",
                         (resp_id,))
            items = cur2.fetchall(); liberar_db(conn2)

            card = tk.Frame(inner, bg=COLORES["superficie"],
                             relief="flat", bd=1, padx=10, pady=8)
            card.pack(fill="x", pady=4)

            # Cabecera de la tarjeta
            card_top = tk.Frame(card, bg=COLORES["superficie"])
            card_top.pack(fill="x")

            tk.Label(card_top, text=f"📌  {desc[:60]}{'…' if len(desc)>60 else ''}",
                     font=FUENTES["bold"], fg=COLORES["texto"],
                     bg=COLORES["superficie"], anchor="w", wraplength=340,
                     justify="left").pack(side="left", fill="x", expand=True)

            # Estado combobox inline
            var_est = tk.StringVar(value=estado)
            combo_est = ttk.Combobox(card_top, textvariable=var_est,
                                      values=ESTADOS, state="readonly",
                                      width=11, font=("Segoe UI", _sz(8)))
            combo_est.pack(side="right", padx=4)

            def cambiar_estado(event=None, rid=resp_id, var=var_est):
                conn3 = conectar_db()
                if conn3 is None: return
                cur3 = conn3.cursor()
                cur3.execute("UPDATE responsabilidades SET estado=%s WHERE id=%s", (var.get(), rid))
                conn3.commit(); liberar_db(conn3)
                refrescar_det()

            combo_est.bind("<<ComboboxSelected>>", cambiar_estado)

            # Fecha y %
            info_row = tk.Frame(card, bg=COLORES["superficie"])
            info_row.pack(fill="x", pady=(2, 4))
            tk.Label(info_row, text=f"📅 Límite: {_fmt_fecha(fecha_lim)}",
                     font=("Segoe UI", _sz(7)), fg=COLORES["texto_suave"],
                     bg=COLORES["superficie"]).pack(side="left")
            tk.Label(info_row, text=f"  |  {pct_r}% del checklist",
                     font=("Segoe UI", _sz(7), "bold"),
                     fg=COLORES["exito"] if pct_r >= 50 else COLORES["peligro"],
                     bg=COLORES["superficie"]).pack(side="left")

            # Barra de progreso de esta responsabilidad
            if tot_c > 0:
                bbar = tk.Frame(card, bg=COLORES["borde"], height=6)
                bbar.pack(fill="x", pady=(0, 4))
                bbar.pack_propagate(False)
                ancho_b = max(2, int(bbar.winfo_reqwidth() * pct_r / 100)) if pct_r > 0 else 2
                # Usamos after para obtener ancho real
                def fill_bar(b=bbar, p=pct_r):
                    b.update_idletasks()
                    w = b.winfo_width()
                    fill_w = max(2, int(w * p / 100))
                    tk.Frame(b, bg=COLORES["exito"] if p >= 50 else COLORES["acento"],
                              height=6, width=fill_w).place(x=0, y=0)
                card.after(50, fill_bar)

            # Checklist para todos los roles
            if rol in ("Director", "Coordinador", "Colaborador"):
                check_frame = tk.Frame(card, bg=COLORES["superficie2"], padx=6, pady=4)
                check_frame.pack(fill="x", pady=(2, 4))

                for item_id, texto, completado in items:
                    item_row = tk.Frame(check_frame, bg=COLORES["superficie2"])
                    item_row.pack(fill="x", pady=1)
                    var_chk = tk.IntVar(value=completado)

                    def toggle_item(iid=item_id, var=var_chk):
                        conn4 = conectar_db()
                        if conn4 is None: return
                        cur4 = conn4.cursor()
                        cur4.execute("UPDATE checklist_items SET completado=%s WHERE id=%s",
                                     (var.get(), iid))
                        conn4.commit(); liberar_db(conn4)
                        refrescar_det()

                    chk = tk.Checkbutton(item_row, variable=var_chk,
                                          text=texto, command=toggle_item,
                                          font=("Segoe UI", _sz(8)),
                                          fg=COLORES["exito"] if completado else COLORES["texto"],
                                          bg=COLORES["superficie2"],
                                          activebackground=COLORES["superficie2"],
                                          selectcolor=COLORES["superficie"],
                                          anchor="w")
                    chk.pack(side="left", fill="x", expand=True)

                    def borrar_item(iid=item_id):
                        conn5 = conectar_db()
                        if conn5 is None: return
                        cur5 = conn5.cursor()
                        cur5.execute("DELETE FROM checklist_items WHERE id=%s", (iid,))
                        conn5.commit(); liberar_db(conn5); refrescar_det()

                    tk.Button(item_row, text="✕", font=("Segoe UI", _sz(7)),
                               fg=COLORES["peligro"], bg=COLORES["superficie2"],
                               relief="flat", bd=0, cursor="hand2",
                               command=borrar_item).pack(side="right")

                # Agregar ítem al checklist
                add_chk_row = tk.Frame(check_frame, bg=COLORES["superficie2"])
                add_chk_row.pack(fill="x", pady=(4, 0))
                ent_chk = ttk.Entry(add_chk_row, font=("Segoe UI", _sz(8)))
                ent_chk.pack(side="left", fill="x", expand=True, ipady=3)

                def agregar_item(rid=resp_id, ent=ent_chk):
                    txt = ent.get().strip()
                    if not txt: return
                    conn6 = conectar_db()
                    if conn6 is None: return
                    cur6 = conn6.cursor()
                    cur6.execute("INSERT INTO checklist_items (responsabilidad_id, texto) VALUES (%s,%s)",
                                 (rid, txt))
                    conn6.commit(); liberar_db(conn6)
                    refrescar_det()

                ent_chk.bind("<Return>", lambda e, rid=resp_id, ent=ent_chk: agregar_item(rid, ent))
                tk.Button(add_chk_row, text="＋", font=("Segoe UI", _sz(9), "bold"),
                           fg=COLORES["blanco"], bg=COLORES["primario"],
                           relief="flat", padx=6, cursor="hand2",
                           command=agregar_item).pack(side="right")

            # Botón eliminar responsabilidad
            def borrar_resp(rid=resp_id):
                if messagebox.askyesno("Confirmar", "¿Eliminar esta responsabilidad y su checklist?"):
                    conn7 = conectar_db()
                    if conn7 is None: return
                    cur7 = conn7.cursor()
                    cur7.execute("DELETE FROM checklist_items WHERE responsabilidad_id=%s", (rid,))
                    cur7.execute("DELETE FROM responsabilidades WHERE id=%s", (rid,))
                    conn7.commit(); liberar_db(conn7); refrescar_det()

            tk.Button(card, text="🗑️ Eliminar responsabilidad",
                       font=("Segoe UI", _sz(7)), fg=COLORES["peligro"],
                       bg=COLORES["superficie"], relief="flat", bd=0,
                       cursor="hand2", command=borrar_resp).pack(anchor="e")

        if not resps:
            tk.Label(inner, text="Sin responsabilidades asignadas.\nUsá el botón ➕ para agregar.",
                     font=("Segoe UI", _sz(9)), fg=COLORES["texto_suave"],
                     bg=COLORES["fondo"], justify="center").pack(pady=20)

    def _ventana_agregar_resp(self, evento_id, socio_id, nombre, rol, callback):
        v = hacer_ventana(self.root, f"Nueva Responsabilidad · {nombre}", 460, 420, modal=True)

        hdr = tk.Frame(v, bg=COLORES["primario"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📌  NUEVA RESPONSABILIDAD",
                 font=FUENTES["subtitulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()
        tk.Label(hdr, text=nombre, font=("Segoe UI", 8),
                 fg=COLORES["acento"], bg=COLORES["primario"]).pack()

        body = tk.Frame(v, bg=COLORES["fondo"], padx=28, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="DESCRIPCIÓN:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        txt_desc = tk.Text(body, height=5, font=FUENTES["normal"],
                            bg=COLORES["superficie2"], fg=COLORES["texto"],
                            insertbackground=COLORES["primario"],
                            relief="flat", padx=8, pady=6, bd=1,
                            highlightbackground=COLORES["borde"],
                            highlightthickness=1)
        txt_desc.pack(fill="x", pady=(4, 12))

        tk.Label(body, text="FECHA LÍMITE:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        cal_lim = DateEntry(body, width=14,
                             background=COLORES["primario"],
                             foreground=COLORES["blanco"],
                             borderwidth=0, date_pattern="dd/mm/yyyy",
                             font=FUENTES["normal"])
        cal_lim.pack(anchor="w", pady=(4, 12))

        tk.Label(body, text="ESTADO INICIAL:", font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w")
        var_est = tk.StringVar(value="Pendiente")
        ttk.Combobox(body, textvariable=var_est,
                     values=["Pendiente", "En curso", "Completado"],
                     state="readonly", font=FUENTES["normal"]).pack(anchor="w", pady=(4, 14))

        def guardar():
            desc = txt_desc.get("1.0", "end-1c").strip()
            if not desc:
                messagebox.showwarning("⚠️", "La descripción es obligatoria.", parent=v)
                return
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión",
                    "No hay conexión a PostgreSQL.\n"
                    "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                return
            cur = conn.cursor()
            cur.execute("""INSERT INTO responsabilidades
                           (evento_id, socio_id, descripcion, fecha_limite, estado)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (evento_id, socio_id, desc, _parsear_fecha(cal_lim.get()), var_est.get()))
            conn.commit(); liberar_db(conn)
            callback(); v.destroy()

        ttk.Button(v, text="✅  GUARDAR RESPONSABILIDAD",
                   style="IKA.TButton", command=guardar).pack(pady=(0, 12), padx=28, fill="x")

    # ── EXPORTAR EXCEL ───────────────────────────────────────────────────────
    def exportar_excel(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            messagebox.showerror("Excel no disponible",
                "openpyxl no está disponible.\n\n"
                "Ejecutá: pip install openpyxl\n"
                "Y recompilá: pyinstaller --windowed --collect-all openpyxl BlackBelt.py")
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Guardar Base de Datos como Excel",
            initialfile="IKA_Afiliados.xlsx"
        )
        if not ruta: return

        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        cur.execute("""SELECT id, nombres, apellidos, cedula, telefono, direccion, correo,
                       fecha_ingreso, categoria, ciudad_nacimiento, fecha_nacimiento, genero
                       FROM miembros ORDER BY apellidos, nombres""")
        filas = cur.fetchall(); liberar_db(conn)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Afiliados IKA"

        headers = ["ID", "Nombres", "Apellidos", "Cedula", "Telefono", "Direccion",
                   "Correo", "Fecha Ingreso", "Categoria", "Ciudad Nacimiento",
                   "Fecha Nacimiento", "Genero"]

        header_fill = PatternFill("solid", fgColor="7B2535")
        header_font = Font(bold=True, color="FFFFFF", name="Segoe UI", size=10)

        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        fill_par  = PatternFill("solid", fgColor="F4F1EC")
        fill_impar= PatternFill("solid", fgColor="EDEAE4")
        for row_idx, fila in enumerate(filas, 2):
            fill = fill_par if row_idx % 2 == 0 else fill_impar
            for col_idx, val in enumerate(fila, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.fill = fill
                cell.font = Font(name="Segoe UI", size=9)
                cell.alignment = Alignment(vertical="center")

        anchos = [8, 18, 18, 14, 14, 22, 24, 14, 18, 18, 16, 10]
        for col, ancho in enumerate(anchos, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = ancho

        ws.row_dimensions[1].height = 20
        ws.freeze_panes = "A2"

        wb.save(ruta)
        messagebox.showinfo("✅ Exportado",
            f"Base exportada correctamente.\n{len(filas)} afiliados guardados en:\n{ruta}")

    # ── IMPORTAR EXCEL ───────────────────────────────────────────────────────
    def importar_excel(self, callback_reload):
        try:
            import openpyxl
        except ImportError:
            messagebox.showerror("Excel no disponible",
                "openpyxl no está disponible.\n\n"
                "Ejecutá: pip install openpyxl\n"
                "Y recompilá: pyinstaller --windowed --collect-all openpyxl BlackBelt.py")
            return
        ruta = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx *.xls")],
            title="Seleccionar archivo Excel para importar"
        )
        if not ruta: return

        try:
            wb = openpyxl.load_workbook(ruta, data_only=True)
            ws = wb.active
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
            return

        # Leer encabezados (fila 1)
        headers_excel = []
        for cell in ws[1]:
            val = cell.value
            headers_excel.append(str(val).strip() if val else "")

        # Mapeo flexible por nombre de columna
        campos_esperados = {
            "nombres":           ["nombres", "nombre"],
            "apellidos":         ["apellidos", "apellido"],
            "cedula":            ["cedula", "cédula", "ci"],
            "telefono":          ["telefono", "teléfono", "tel"],
            "direccion":         ["direccion", "dirección"],
            "correo":            ["correo", "email", "mail"],
            "fecha_ingreso":     ["fecha ingreso", "fecha_ingreso", "ingreso"],
            "categoria":         ["categoria", "categoría", "rol"],
            "ciudad_nacimiento": ["ciudad nacimiento", "ciudad_nacimiento", "ciudad"],
            "fecha_nacimiento":  ["fecha nacimiento", "fecha_nacimiento", "nacimiento"],
            "genero":            ["genero", "género", "sexo"],
        }

        col_map = {}  # campo_db -> indice_excel (0-based)
        headers_lower = [h.lower() for h in headers_excel]
        for campo, aliases in campos_esperados.items():
            for alias in aliases:
                if alias in headers_lower:
                    col_map[campo] = headers_lower.index(alias)
                    break

        if "cedula" not in col_map:
            messagebox.showerror("Error",
                "El Excel no tiene columna 'Cedula'.\nVerificá los encabezados.")
            return

        obligatorios = ["nombres", "apellidos", "cedula"]
        faltantes = [c for c in obligatorios if c not in col_map]
        if faltantes:
            messagebox.showerror("Error",
                f"Faltan columnas obligatorias:\n{', '.join(faltantes)}")
            return

        # Leer filas
        registros_excel = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row): continue  # fila vacía
            reg = {}
            for campo, idx in col_map.items():
                val = row[idx] if idx < len(row) else None
                reg[campo] = str(val).strip() if val is not None else ""
            if reg.get("cedula"):
                registros_excel.append(reg)

        if not registros_excel:
            messagebox.showinfo("Aviso", "El archivo no tiene registros para importar.")
            return

        # ── Detectar categorías nuevas ──
        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM categorias")
        cats_existentes = set(r[0] for r in cur.fetchall())
        liberar_db(conn)

        cats_nuevas = set()
        for reg in registros_excel:
            cat = reg.get("categoria", "").strip()
            if cat and cat not in cats_existentes:
                cats_nuevas.add(cat)

        if cats_nuevas:
            self._confirmar_categorias_nuevas(
                cats_nuevas, cats_existentes,
                lambda: self._procesar_importacion(registros_excel, callback_reload)
            )
        else:
            self._procesar_importacion(registros_excel, callback_reload)

    def _confirmar_categorias_nuevas(self, cats_nuevas, cats_existentes, continuar_fn):
        v_cat = hacer_ventana(self.root, "Categorías Nuevas Detectadas", 520, 480, modal=True)

        hdr = tk.Frame(v_cat, bg=COLORES["primario"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚠️  CATEGORÍAS NUEVAS",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        tk.Label(v_cat,
                 text="Se encontraron estas categorías nuevas en el Excel.\nPodés editar los nombres antes de confirmar:",
                 font=FUENTES["normal"], fg=COLORES["texto"],
                 bg=COLORES["fondo"], justify="center").pack(pady=(14, 6))

        scroll_f = tk.Frame(v_cat, bg=COLORES["fondo"])
        scroll_f.pack(fill="both", expand=True, padx=30)

        canvas = tk.Canvas(scroll_f, bg=COLORES["fondo"], highlightthickness=0)
        sc = ttk.Scrollbar(scroll_f, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORES["fondo"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        entradas_cat = {}
        for i, cat in enumerate(sorted(cats_nuevas)):
            bg = COLORES["superficie"] if i % 2 == 0 else COLORES["superficie2"]
            row = tk.Frame(inner, bg=bg, pady=6, padx=10)
            row.pack(fill="x", pady=1)
            tk.Label(row, text="Nueva:", font=FUENTES["bold"],
                     fg=COLORES["texto_suave"], bg=bg, width=8).pack(side="left")
            ent = tk.Entry(row, font=FUENTES["normal"],
                           fg=COLORES["texto"], bg=COLORES["blanco"],
                           relief="flat", bd=1)
            ent.pack(side="left", fill="x", expand=True, ipady=3)
            ent.insert(0, cat)
            entradas_cat[cat] = ent

        def confirmar():
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                return
            cur = conn.cursor()
            nombres_finales = {}
            for cat_orig, ent in entradas_cat.items():
                nombre_final = ent.get().strip()
                if nombre_final:
                    try:
                        cur.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre_final,))
                    except: pass
                    nombres_finales[cat_orig] = nombre_final
            conn.commit(); liberar_db(conn)
            v_cat.destroy()
            continuar_fn()

        btn_f = tk.Frame(v_cat, bg=COLORES["fondo"], pady=12)
        btn_f.pack()
        ttk.Button(btn_f, text="✅  Confirmar y Continuar",
                   style="IKA.TButton", command=confirmar).pack(side="left", padx=8)
        ttk.Button(btn_f, text="❌  Cancelar",
                   style="Danger.TButton", command=v_cat.destroy).pack(side="left", padx=8)

    def _procesar_importacion(self, registros_excel, callback_reload):
        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        cur.execute("SELECT cedula FROM miembros")
        cedulas_existentes = set(r[0] for r in cur.fetchall())
        liberar_db(conn)

        nuevos     = [r for r in registros_excel if r["cedula"] not in cedulas_existentes]
        duplicados = [r for r in registros_excel if r["cedula"] in cedulas_existentes]

        if duplicados:
            self._resolver_duplicados(duplicados, nuevos, callback_reload)
        else:
            self._insertar_registros(nuevos, callback_reload)

    def _resolver_duplicados(self, duplicados, nuevos, callback_reload):
        v_dup = hacer_ventana(self.root, "Duplicados Encontrados", 940, 660, modal=True)

        hdr = tk.Frame(v_dup, bg=COLORES["primario"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"⚠️  {len(duplicados)} DUPLICADO(S) ENCONTRADO(S)",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()
        tk.Label(hdr,
                 text="Para cada afiliado elegí cuál versión conservar",
                 font=FUENTES["normal"], fg="#FFCCCC",
                 bg=COLORES["primario"]).pack()

        # Canvas scrollable
        canvas_f = tk.Frame(v_dup, bg=COLORES["fondo"])
        canvas_f.pack(fill="both", expand=True, padx=10, pady=8)
        canvas = tk.Canvas(canvas_f, bg=COLORES["fondo"], highlightthickness=0)
        sc = ttk.Scrollbar(canvas_f, orient="vertical", command=canvas.yview)
        contenedor = tk.Frame(canvas, bg=COLORES["fondo"])
        contenedor.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=contenedor, anchor="nw")
        canvas.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        decisiones = {}  # cedula -> StringVar ("base" o "excel")

        campos_mostrar = ["nombres", "apellidos", "telefono", "correo",
                          "categoria", "ciudad_nacimiento", "genero"]

        for idx, reg_excel in enumerate(duplicados):
            cedula = reg_excel["cedula"]
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                return
            cur = conn.cursor()
            cur.execute("""SELECT nombres, apellidos, telefono, correo, categoria,
                           ciudad_nacimiento, genero FROM miembros WHERE cedula=%s""", (cedula,))
            row_db = cur.fetchone(); liberar_db(conn)

            reg_base = dict(zip(campos_mostrar, row_db)) if row_db else {}

            var = tk.StringVar(value="base")
            decisiones[cedula] = var

            bg_bloque = COLORES["superficie"] if idx % 2 == 0 else COLORES["superficie2"]
            bloque = tk.Frame(contenedor, bg=bg_bloque, padx=10, pady=10,
                              relief="flat", bd=1)
            bloque.pack(fill="x", pady=4, padx=4)

            # Título cédula
            tk.Label(bloque, text=f"Cédula: {cedula}  —  {reg_excel.get('nombres','')} {reg_excel.get('apellidos','')}",
                     font=FUENTES["subtitulo"], fg=COLORES["primario"],
                     bg=bg_bloque).pack(anchor="w", pady=(0, 6))

            # Dos columnas: BASE vs EXCEL
            cols_f = tk.Frame(bloque, bg=bg_bloque)
            cols_f.pack(fill="x")

            # Encabezados
            tk.Label(cols_f, text="", bg=bg_bloque, width=16).grid(row=0, column=0)
            rb_base = tk.Radiobutton(cols_f, text="✅  CONSERVAR BASE DE DATOS",
                                      variable=var, value="base",
                                      font=FUENTES["bold"], fg=COLORES["exito"],
                                      bg=bg_bloque, activebackground=bg_bloque,
                                      selectcolor=bg_bloque)
            rb_base.grid(row=0, column=1, padx=(0, 20), sticky="w")
            rb_excel = tk.Radiobutton(cols_f, text="📥  CONSERVAR EXCEL",
                                       variable=var, value="excel",
                                       font=FUENTES["bold"], fg=COLORES["primario"],
                                       bg=bg_bloque, activebackground=bg_bloque,
                                       selectcolor=bg_bloque)
            rb_excel.grid(row=0, column=2, sticky="w")

            # Filas de campos
            for i, campo in enumerate(campos_mostrar):
                val_base  = str(reg_base.get(campo, "") or "—")
                val_excel = str(reg_excel.get(campo, "") or "—")
                color_dif = COLORES["primario"] if val_base != val_excel else COLORES["texto_suave"]

                tk.Label(cols_f, text=campo.replace("_", " ").title(),
                         font=("Segoe UI", 8, "bold"),
                         fg=COLORES["texto_suave"], bg=bg_bloque,
                         width=16, anchor="w").grid(row=i+1, column=0, sticky="w", pady=1)

                ent_b = tk.Entry(cols_f, font=FUENTES["normal"],
                                  fg=COLORES["texto"], bg=COLORES["blanco"],
                                  relief="flat", bd=1, readonlybackground=COLORES["blanco"],
                                  state="readonly", width=28)
                ent_b.config(state="normal"); ent_b.insert(0, val_base); ent_b.config(state="readonly")
                ent_b.grid(row=i+1, column=1, padx=(0, 20), sticky="ew", pady=1)

                ent_e = tk.Entry(cols_f, font=FUENTES["normal"],
                                  fg=color_dif, bg=COLORES["blanco"],
                                  relief="flat", bd=1, readonlybackground=COLORES["blanco"],
                                  state="readonly", width=28)
                ent_e.config(state="normal"); ent_e.insert(0, val_excel); ent_e.config(state="readonly")
                ent_e.grid(row=i+1, column=2, sticky="ew", pady=1)

            cols_f.columnconfigure(1, weight=1)
            cols_f.columnconfigure(2, weight=1)

        # Botones finales
        def aplicar_decisiones():
            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión", "No hay conexión a PostgreSQL.")
                return
            cur = conn.cursor()
            actualizados = 0
            for cedula, var in decisiones.items():
                if var.get() == "excel":
                    reg = next(r for r in duplicados if r["cedula"] == cedula)
                    cur.execute("""UPDATE miembros SET nombres=%s, apellidos=%s, telefono=%s,
                                   direccion=%s, correo=%s, fecha_ingreso=%s, categoria=%s,
                                   ciudad_nacimiento=%s, fecha_nacimiento=%s, genero=%s
                                   WHERE cedula=%s""",
                                (reg.get("nombres",""), reg.get("apellidos",""),
                                 reg.get("telefono",""), reg.get("direccion",""),
                                 reg.get("correo",""), reg.get("fecha_ingreso",""),
                                 reg.get("categoria",""), reg.get("ciudad_nacimiento",""),
                                 reg.get("fecha_nacimiento",""), reg.get("genero",""), cedula))
                    actualizados += 1
            conn.commit(); liberar_db(conn)
            v_dup.destroy()
            self._insertar_registros(nuevos, callback_reload, actualizados)

        btn_f = tk.Frame(v_dup, bg=COLORES["fondo"], pady=10)
        btn_f.pack()
        ttk.Button(btn_f, text="✅  Aplicar Decisiones e Importar",
                   style="IKA.TButton", command=aplicar_decisiones).pack(side="left", padx=8)
        ttk.Button(btn_f, text="❌  Cancelar Todo",
                   style="Danger.TButton", command=v_dup.destroy).pack(side="left", padx=8)

    def _insertar_registros(self, nuevos, callback_reload, actualizados=0):
        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        insertados = 0
        errores    = 0
        for reg in nuevos:
            try:
                cedula   = reg.get("cedula", "")
                pw_hash  = _hash_cedula(cedula) if cedula else ""
                cur.execute("""INSERT INTO miembros (nombres, apellidos, cedula, telefono,
                               direccion, correo, fecha_ingreso, categoria,
                               ciudad_nacimiento, fecha_nacimiento, genero,
                               password_hash, debe_cambiar_pass)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (reg.get("nombres",""), reg.get("apellidos",""),
                             cedula, reg.get("telefono",""),
                             reg.get("direccion",""), reg.get("correo",""),
                             _parsear_fecha(reg.get("fecha_ingreso","")),
                             reg.get("categoria",""),
                             reg.get("ciudad_nacimiento",""),
                             _parsear_fecha(reg.get("fecha_nacimiento","")),
                             reg.get("genero",""),
                             pw_hash, True))
                insertados += 1
            except:
                errores += 1
        conn.commit(); liberar_db(conn)
        callback_reload()
        resumen = f"Importación completada:\n\n"
        resumen += f"✅  {insertados} afiliado(s) nuevo(s) importado(s)\n"
        if actualizados: resumen += f"🔄  {actualizados} afiliado(s) actualizado(s) desde Excel\n"
        if errores:      resumen += f"⚠️  {errores} registro(s) con error (cédula duplicada u otro)\n"
        messagebox.showinfo("Importación Completa", resumen)


    # ── REGISTRAR ADMIN ─────────────────────────────────────────────────────
    def ventana_registro_admin(self):
        """
        Abre el formulario de Nuevo Afiliado en modo Admin:
        - Categoría fijada automáticamente como 'Administrador N'
        - Al guardar, escribe admin_socio_id en club_config.json
        """
        # Calcular número de admin
        conn = conectar_db()
        if conn is None:
            messagebox.showerror("Sin conexión",
                "No hay conexión a PostgreSQL.\n"
                "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
            return
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM miembros WHERE categoria LIKE 'Administrador%'")
        n_admins = cur.fetchone()[0]
        liberar_db(conn)
        cat_admin = f"Administrador {n_admins + 1}"

        # Asegurar que la categoría exista en la tabla categorias
        conn2 = conectar_db()
        if conn2 is None: return
        cur2 = conn2.cursor()
        try:
            cur2.execute("INSERT INTO categorias (nombre) VALUES (%s)", (cat_admin,))
            conn2.commit()
        except:
            pass  # ya existe
        finally:
            liberar_db(conn2)

        titulo = f"Registrar Administrador ({cat_admin})"
        v_reg = hacer_ventana(self.root, titulo, 540, 820, modal=True)

        hdr = tk.Frame(v_reg, bg=COLORES["primario"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🛡️  {titulo.upper()}",
                 font=FUENTES["titulo"], fg=COLORES["blanco"],
                 bg=COLORES["primario"]).pack()

        canvas = tk.Canvas(v_reg, bg=COLORES["fondo"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(v_reg, orient="vertical", command=canvas.yview)
        form_container = tk.Frame(canvas, bg=COLORES["fondo"])
        form_container.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        form = tk.Frame(form_container, bg=COLORES["fondo"], padx=36)
        form.pack(fill="both", expand=True, pady=16)

        entradas_adm = {}
        campos = [
            ("Nombres",              "nombres"),
            ("Apellidos",            "apellidos"),
            ("Cédula",               "cedula"),
            ("Teléfono",             "telefono"),
            ("Dirección",            "direccion"),
            ("Correo electrónico",   "correo"),
            ("Ciudad de nacimiento", "ciudad_nacimiento"),
        ]

        for label_text, key in campos:
            tk.Label(form, text=label_text.upper(),
                     font=("Segoe UI", 8, "bold"),
                     fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(10, 2))
            ent = ttk.Entry(form)
            ent.pack(fill="x", ipady=4)
            entradas_adm[key] = ent

        # Pre-llenar nombre/apellido desde config si existen
        if _config.get("admin_nombre"):
            entradas_adm["nombres"].insert(0, _config["admin_nombre"])
        if _config.get("admin_apellido"):
            entradas_adm["apellidos"].insert(0, _config["admin_apellido"])

        # Género
        tk.Label(form, text="GÉNERO",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        genero_frame = tk.Frame(form, bg=COLORES["fondo"])
        genero_frame.pack(anchor="w", pady=(0, 4))
        var_genero_adm = tk.StringVar(value="")
        tk.Radiobutton(genero_frame, text="Hombre", variable=var_genero_adm, value="Hombre",
                       bg=COLORES["fondo"], fg=COLORES["texto"], activebackground=COLORES["fondo"],
                       selectcolor=COLORES["superficie2"], font=FUENTES["normal"]).pack(side="left", padx=(0, 16))
        tk.Radiobutton(genero_frame, text="Mujer", variable=var_genero_adm, value="Mujer",
                       bg=COLORES["fondo"], fg=COLORES["texto"], activebackground=COLORES["fondo"],
                       selectcolor=COLORES["superficie2"], font=FUENTES["normal"]).pack(side="left")

        # Fecha nacimiento
        tk.Label(form, text="FECHA DE NACIMIENTO",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        cal_nac_adm = DateEntry(form, width=18,
                                background=COLORES["primario"],
                                foreground=COLORES["blanco"],
                                borderwidth=0, date_pattern="dd/mm/yyyy",
                                font=FUENTES["normal"])
        cal_nac_adm.pack(anchor="w")

        # Categoría — fija, no editable
        tk.Label(form, text="CATEGORÍA / ROL",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        cat_frame = tk.Frame(form, bg=COLORES["superficie2"], pady=6, padx=10)
        cat_frame.pack(fill="x")
        tk.Label(cat_frame, text=cat_admin,
                 font=("Segoe UI", 11, "bold"),
                 fg=COLORES["primario"], bg=COLORES["superficie2"]).pack(side="left")
        tk.Label(cat_frame, text="  (asignado automáticamente)",
                 font=("Segoe UI", 8),
                 fg=COLORES["texto_suave"], bg=COLORES["superficie2"]).pack(side="left")

        # Fecha ingreso
        tk.Label(form, text="FECHA DE INGRESO AL CLUB",
                 font=("Segoe UI", 8, "bold"),
                 fg=COLORES["texto_suave"], bg=COLORES["fondo"]).pack(anchor="w", pady=(14, 2))
        cal_adm = DateEntry(form, width=18,
                            background=COLORES["primario"],
                            foreground=COLORES["blanco"],
                            borderwidth=0, date_pattern="dd/mm/yyyy",
                            font=FUENTES["normal"])
        cal_adm.pack(anchor="w")

        def guardar_admin_registro():
            d = {k: v.get().strip() for k, v in entradas_adm.items()}
            fecha_ing  = cal_adm.get()
            fecha_nac  = cal_nac_adm.get()
            genero_val = var_genero_adm.get()

            if not all(d.values()) or not genero_val:
                messagebox.showwarning("⚠️ Atención",
                    "Todos los campos son obligatorios para registrar el administrador.")
                return

            conn = conectar_db()
            if conn is None:
                messagebox.showerror("Sin conexión",
                    "No hay conexión a PostgreSQL.\n"
                    "Configurá las credenciales en Configuración → 🐘 PostgreSQL.")
                return
            cursor = conn.cursor()
            try:
                pw_hash = _hash_cedula(d["cedula"])
                cursor.execute("""INSERT INTO miembros (nombres, apellidos, cedula, telefono,
                    direccion, correo, fecha_ingreso, categoria,
                    ciudad_nacimiento, fecha_nacimiento, genero, password_hash, debe_cambiar_pass)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (d["nombres"], d["apellidos"], d["cedula"], d["telefono"],
                     d["direccion"], d["correo"],
                     _parsear_fecha(fecha_ing), cat_admin,
                     d["ciudad_nacimiento"], _parsear_fecha(fecha_nac),
                     genero_val, pw_hash, True))
                nuevo_id = cursor.fetchone()[0]
                conn.commit()

                # Guardar socio_id y nombre en config para uso del chat
                _config["admin_nombre"]    = d["nombres"]
                _config["admin_apellido"]  = d["apellidos"]
                _config["admin_socio_id"]  = nuevo_id
                guardar_config(_config)

                messagebox.showinfo(
                    "✅ Admin Registrado",
                    f"{cat_admin} registrado correctamente.\n"
                    f"Nombre: {d['nombres']} {d['apellidos']}\n"
                    f"ID asignado: {nuevo_id}"
                )

                if "master" in self.ventanas and self.ventanas["master"].winfo_exists():
                    self.cargar_datos_tabla()
                v_reg.destroy()
            except Exception as e:
                conn.rollback()
                if "unique" in str(e).lower():
                    messagebox.showerror("Error", "Ya existe un afiliado con esa cédula.")
                else:
                    messagebox.showerror("Error", str(e))
            finally:
                liberar_db(conn)

        btn_frame = tk.Frame(v_reg, bg=COLORES["fondo"], pady=14)
        btn_frame.pack(fill="x", padx=36)
        ttk.Button(btn_frame, text="🛡️  REGISTRAR ADMINISTRADOR",
                   style="IKA.TButton",
                   command=guardar_admin_registro).pack(fill="x", ipady=6)

        return v_reg


if __name__ == "__main__":
    root = tk.Tk()
    aplicar_tema()
    if not PSYCOPG2_OK:
        messagebox.showwarning(
            "Dependencia faltante",
            "psycopg2 no está instalado.\n\n"
            "Ejecutá en tu terminal:\n"
            "  pip install psycopg2-binary\n\n"
            "Luego reiniciá BlackBelt.\n"
            "Podés seguir navegando la interfaz, pero no se guardarán datos."
        )
    app = AplicacionClubPro(root)
    import threading
    threading.Thread(target=_cargar_cache, daemon=True).start()
    root.mainloop()
