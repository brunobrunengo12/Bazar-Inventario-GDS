import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "clave_secreta_bazar"  # Necesaria para mostrar mensajes en pantalla

DB_NAME = "bazar.db"

def get_db():
    """Conecta a SQLite y permite acceder a las columnas por nombre."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea las dos tablas del sistema si no existen."""
    with get_db() as conn:
        # Tabla 1: Catálogo de artículos (Sin precios, foco en stock y ubicación)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                categoria TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                stock_actual INTEGER NOT NULL DEFAULT 0,
                stock_minimo INTEGER NOT NULL DEFAULT 5,
                activo INTEGER NOT NULL DEFAULT 1
            )
        """)
        # Tabla 2: Historial de entradas, ventas y bajas por rotura/falla
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,        -- 'INGRESO', 'VENTA', 'BAJA'
                motivo TEXT NOT NULL,      -- 'Re-stock', 'Venta mostrador', 'Rotura en local', 'Falla de fábrica'
                cantidad INTEGER NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos (id)
            )
        """)
        conn.commit()

# F02: Listado general de existencias (MD)
@app.route("/")
def index():
    with get_db() as conn:
        productos = conn.execute(
            "SELECT * FROM productos WHERE activo = 1 ORDER BY nombre"
        ).fetchall()
    return render_template("index.html", productos=productos)

# F01: Alta de artículo en catálogo (BB)
@app.route("/agregar", methods=["POST"])
def agregar_producto():
    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "")
    ubicacion = request.form.get("ubicacion", "")
    stock_actual = int(request.form.get("stock_actual", 0))
    stock_minimo = int(request.form.get("stock_minimo", 0))

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO productos (nombre, categoria, ubicacion, stock_actual, stock_minimo)
               VALUES (?, ?, ?, ?, ?)""",
            (nombre, categoria, ubicacion, stock_actual, stock_minimo)
        )
        producto_id = cursor.lastrowid
        
        # Si ingresa con stock inicial mayor a 0, dejamos asentado el primer movimiento
        if stock_actual > 0:
            conn.execute(
                "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'INGRESO', 'Stock inicial', ?)",
                (producto_id, stock_actual)
            )
        conn.commit()

    return redirect(url_for("index"))

# F03: Registro de ingreso de mercadería / Re-stock (GB)
@app.route("/restock/<int:id>", methods=["POST"])
def re_stock(id):
    cantidad = int(request.form.get("cantidad", 0))
    with get_db() as conn:
        conn.execute(
            "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
            (cantidad, id)
        )
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'INGRESO', 'Re-stock proveedor', ?)",
            (id, cantidad)
        )
        conn.commit()
    return redirect(url_for("index"))

# F04: Registro de salida por venta en mostrador (GB)
@app.route("/venta/<int:id>", methods=["POST"])
def registrar_venta(id):
    cantidad = int(request.form.get("cantidad", 0))
    with get_db() as conn:
        # En Etapa 1 aún no validamos en el backend si el stock queda negativo (F05 pendiente)
        conn.execute(
            "UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?",
            (cantidad, id)
        )
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'VENTA', 'Venta en mostrador', ?)",
            (id, cantidad)
        )
        conn.commit()
    return redirect(url_for("index"))

# F06: Baja de mercadería por rotura o falla de fábrica (IR)
@app.route("/baja/<int:id>", methods=["POST"])
def registrar_baja(id):
    cantidad = int(request.form.get("cantidad", 0))
    motivo = request.form.get("motivo", "Rotura en local") # 'Rotura en local' o 'Falla de fábrica'
    with get_db() as conn:
        conn.execute(
            "UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?",
            (cantidad, id)
        )
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'BAJA', ?, ?)",
            (id, motivo, cantidad)
        )
        conn.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)