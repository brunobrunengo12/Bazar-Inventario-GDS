import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "clave_secreta_bazar"

DB_NAME = "bazar.db"

def get_db():
    """CONECTA A SQLITE"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """CREA LAS DOS TABLAS SI NO EXISTEN"""
    with get_db() as conn:
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                motivo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos (id)
            )
        """)
        conn.commit()

# FUNCIONALIDADES F02, F07 Y F10 (MAURO Y GONZALO)
@app.route("/")
def index():
    busqueda = request.args.get("q", "").strip()
    categoria_filtro = request.args.get("categoria", "").strip()

    query = "SELECT * FROM productos WHERE activo = 1"
    params = []

    if busqueda:
        query += " AND nombre LIKE ?"
        params.append(f"%{busqueda}%")
    
    if categoria_filtro:
        query += " AND categoria = ?"
        params.append(categoria_filtro)

    query += " ORDER BY nombre"

    with get_db() as conn:
        productos = conn.execute(query, params).fetchall()

    return render_template(
        "index.html",
        productos=productos,
        busqueda=busqueda,
        categoria_filtro=categoria_filtro
    )

# FUNCIONALIDADES F01 Y F05 (BRUNO)
@app.route("/agregar", methods=["POST"])
def agregar_producto():
    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "").strip()
    ubicacion = request.form.get("ubicacion", "").strip()
    
    try:
        stock_actual = int(request.form.get("stock_actual", 0))
        stock_minimo = int(request.form.get("stock_minimo", 0))
    except ValueError:
        flash("Error: Las cantidades de stock deben ser números enteros válidos.", "danger")
        return redirect(url_for("index"))

    if not nombre or stock_actual < 0 or stock_minimo < 0:
        flash("Error: El nombre es obligatorio y no se permite ingresar stock inicial ni mínimo negativo.", "danger")
        return redirect(url_for("index"))

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO productos (nombre, categoria, ubicacion, stock_actual, stock_minimo)
               VALUES (?, ?, ?, ?, ?)""",
            (nombre, categoria, ubicacion, stock_actual, stock_minimo)
        )
        producto_id = cursor.lastrowid
        
        if stock_actual > 0:
            conn.execute(
                "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'INGRESO', 'Stock inicial', ?)",
                (producto_id, stock_actual)
            )
        conn.commit()

    flash(f"Artículo '{nombre}' registrado correctamente.", "success")
    return redirect(url_for("index"))

# FUNCIONALIDADES F03 Y F05 (GONZALO Y BRUNO)
@app.route("/restock/<int:id>", methods=["POST"])
def re_stock(id):
    try:
        cantidad = int(request.form.get("cantidad", 0))
    except ValueError:
        cantidad = 0

    if cantidad <= 0:
        flash("Error: La cantidad a ingresar por re-stock debe ser mayor a cero.", "danger")
        return redirect(url_for("index"))

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

    flash("Ingreso de mercadería registrado correctamente.", "success")
    return redirect(url_for("index"))

# FUNCIONALIDADES F04 Y F05 (GONZALO Y BRUNO)
@app.route("/venta/<int:id>", methods=["POST"])
def registrar_venta(id):
    try:
        cantidad = int(request.form.get("cantidad", 0))
    except ValueError:
        cantidad = 0

    if cantidad <= 0:
        flash("Error: La cantidad de salida por venta debe ser mayor a cero.", "danger")
        return redirect(url_for("index"))

    with get_db() as conn:
        producto = conn.execute("SELECT nombre, stock_actual FROM productos WHERE id = ?", (id,)).fetchone()
        if not producto or producto["stock_actual"] < cantidad:
            flash(f"Error: Stock insuficiente para '{producto['nombre']}'. Disponible: {producto['stock_actual']} u.", "danger")
            return redirect(url_for("index"))

        conn.execute(
            "UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?",
            (cantidad, id)
        )
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'VENTA', 'Venta en mostrador', ?)",
            (id, cantidad)
        )
        conn.commit()

    flash("Salida por venta registrada.", "success")
    return redirect(url_for("index"))

# FUNCIONALIDADES F06 Y F06 (IGNACIO Y BRUNO)
@app.route("/baja/<int:id>", methods=["POST"])
def registrar_baja(id):
    try:
        cantidad = int(request.form.get("cantidad", 0))
    except ValueError:
        cantidad = 0

    motivo = request.form.get("motivo", "Rotura en local")

    if cantidad <= 0:
        flash("Error: La cantidad a dar de baja debe ser mayor a cero.", "danger")
        return redirect(url_for("index"))

    with get_db() as conn:
        producto = conn.execute("SELECT nombre, stock_actual FROM productos WHERE id = ?", (id,)).fetchone()
        if not producto or producto["stock_actual"] < cantidad:
            flash(f"Error: No se puede dar de baja más unidades de las existentes ({producto['stock_actual']} u.).", "danger")
            return redirect(url_for("index"))

        conn.execute(
            "UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?",
            (cantidad, id)
        )
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, motivo, cantidad) VALUES (?, 'BAJA', ?, ?)",
            (id, motivo, cantidad)
        )
        conn.commit()

    flash(f"Baja registrada ({motivo}).", "warning")
    return redirect(url_for("index"))

# FUNCIONALIDAD F08 (MAURO)
@app.route("/editar/<int:id>", methods=["POST"])
def editar_producto(id):
    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "").strip()
    ubicacion = request.form.get("ubicacion", "").strip()

    try:
        stock_minimo = int(request.form.get("stock_minimo", 0))
    except ValueError:
        stock_minimo = -1

    if not nombre or stock_minimo < 0:
        flash("Error: Datos de edición inválidos o stock mínimo negativo.", "danger")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            """UPDATE productos 
               SET nombre = ?, categoria = ?, ubicacion = ?, stock_minimo = ?
               WHERE id = ?""",
            (nombre, categoria, ubicacion, stock_minimo, id)
        )
        conn.commit()

    flash(f"Datos del artículo '{nombre}' actualizados sin alterar sus existencias.", "info")
    return redirect(url_for("index"))

# FUNCIONALIDAD F12 (BRUNO)
@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_producto(id):
    with get_db() as conn:
        conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (id,))
        conn.commit()
    flash("Artículo discontinuado eliminado del catálogo activo.", "secondary")
    return redirect(url_for("index"))

# FUNCIONALIDAD F11 (IGNACIO)
@app.route("/historial")
def historial():
    with get_db() as conn:
        movimientos = conn.execute("""
            SELECT m.id, p.nombre AS producto_nombre, p.categoria, m.tipo, m.motivo, m.cantidad, m.fecha
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            ORDER BY m.fecha DESC, m.id DESC
        """).fetchall()
    return render_template("historial.html", movimientos=movimientos)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)