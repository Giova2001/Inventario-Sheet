import os, sqlite3, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

BASE=os.path.dirname(os.path.abspath(__file__))
app=Flask(__name__); app.secret_key=os.environ.get('FLASK_SECRET_KEY','local-dev-change-me')
DB=os.path.join(BASE,'inventario.db')
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS categorias(id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE, descripcion TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS productos(id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, categoria_id INTEGER REFERENCES categorias(id), tipo TEXT DEFAULT 'Producto base', precio REAL DEFAULT 0, stock INTEGER DEFAULT 0, activo INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS movimientos(id INTEGER PRIMARY KEY, producto_id INTEGER NOT NULL REFERENCES productos(id), tipo TEXT NOT NULL, cantidad INTEGER NOT NULL, costo REAL DEFAULT 0, referencia TEXT DEFAULT '', observacion TEXT DEFAULT '', fecha TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS configuracion(clave TEXT PRIMARY KEY, valor TEXT DEFAULT '');''')
  if not c.execute('SELECT 1 FROM categorias LIMIT 1').fetchone():
   c.executemany('INSERT INTO categorias(nombre,descripcion) VALUES (?,?)',[('Textiles','Prendas y telas para personalización'),('Sublimación','Artículos sublimables'),('Publicidad','Banners y material promocional'),('Insumos','Materiales de producción')])
  if not c.execute('SELECT 1 FROM productos LIMIT 1').fetchone():
   c.executemany('INSERT INTO productos(codigo,nombre,categoria_id,tipo,precio,stock) VALUES (?,?,?,?,?,?)',[('PROD-001','Camiseta Blanca S',1,'Producto base',45,25),('PROD-002','Camiseta Blanca M',1,'Producto base',45,25),('PROD-003','Taza Blanca 11 oz',2,'Producto base',18.5,30),('PROD-004','Banner 120x200 cm',3,'Producto base',350,8),('PROD-005','Vinil textil blanco',4,'Consumible',35,25)])
@app.context_processor
def globals_(): return {'now':datetime.now()}
@app.route('/')
def index():
 q=request.args.get('q','');cat=request.args.get('categoria','')
 with conn() as c:
  sql='SELECT p.*,c.nombre categoria FROM productos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE (p.nombre LIKE ? OR p.codigo LIKE ?)';params=['%'+q+'%']*2
  if cat.isdigit():sql+=' AND p.categoria_id=?';params.append(int(cat))
  sql+=' ORDER BY p.id DESC'
  return render_template('index.html',page='productos',productos=c.execute(sql,params).fetchall(),categorias=c.execute('SELECT * FROM categorias ORDER BY nombre').fetchall(),q=q,cat=cat)
@app.route('/producto/guardar',methods=['POST'])
def guardar_producto():
 f=request.form;pid=f.get('id');codigo=f['codigo'].strip();nombre=f['nombre'].strip()
 if not codigo or not nombre:flash('Código y nombre obligatorios','error');return redirect(url_for('index'))
 try:
  with conn() as c:
   values=(codigo,nombre,int(f['categoria_id']) if f.get('categoria_id') else None,f.get('tipo','Producto base'),float(f.get('precio') or 0),int(f.get('stock') or 0))
   if pid:c.execute('UPDATE productos SET codigo=?,nombre=?,categoria_id=?,tipo=?,precio=?,stock=? WHERE id=?',values+(int(pid),))
   else:c.execute('INSERT INTO productos(codigo,nombre,categoria_id,tipo,precio,stock) VALUES (?,?,?,?,?,?)',values)
  flash('Producto guardado correctamente','ok')
 except (sqlite3.IntegrityError,ValueError) as e:flash('No se pudo guardar: '+str(e),'error')
 return redirect(url_for('index'))
@app.route('/producto/<int:pid>/borrar',methods=['POST'])
def borrar_producto(pid):
 try:
  with conn() as c:c.execute('DELETE FROM productos WHERE id=?',(pid,))
  flash('Producto eliminado','ok')
 except sqlite3.IntegrityError:flash('Este producto tiene movimientos y no puede eliminarse','error')
 return redirect(url_for('index'))
@app.route('/categorias')
def categorias():
 with conn() as c:return render_template('categorias.html',page='categorias',categorias=c.execute('SELECT c.*, (SELECT COUNT(*) FROM productos p WHERE p.categoria_id=c.id) total FROM categorias c ORDER BY c.id DESC').fetchall())
@app.route('/categoria/guardar',methods=['POST'])
def guardar_categoria():
 f=request.form
 try:
  with conn() as c:
   if f.get('id'):c.execute('UPDATE categorias SET nombre=?,descripcion=? WHERE id=?',(f['nombre'].strip(),f.get('descripcion',''),int(f['id'])))
   else:c.execute('INSERT INTO categorias(nombre,descripcion) VALUES (?,?)',(f['nombre'].strip(),f.get('descripcion','')))
  flash('Categoría guardada','ok')
 except sqlite3.IntegrityError:flash('El nombre ya existe','error')
 return redirect(url_for('categorias'))
@app.route('/categoria/<int:cid>/borrar',methods=['POST'])
def borrar_categoria(cid):
 with conn() as c:
  if c.execute('SELECT 1 FROM productos WHERE categoria_id=?',(cid,)).fetchone():flash('No se puede borrar una categoría con productos','error')
  else:c.execute('DELETE FROM categorias WHERE id=?',(cid,));flash('Categoría eliminada','ok')
 return redirect(url_for('categorias'))
@app.route('/movimientos/<tipo>')
def movimientos(tipo):
 if tipo not in ('entrada','salida'):return redirect(url_for('index'))
 with conn() as c:return render_template('movimientos.html',page=tipo,tipo=tipo,productos=c.execute('SELECT * FROM productos ORDER BY nombre').fetchall(),movimientos=c.execute('SELECT m.*,p.nombre producto FROM movimientos m JOIN productos p ON p.id=m.producto_id WHERE m.tipo=? ORDER BY m.id DESC',(tipo,)).fetchall())
@app.route('/movimiento/guardar',methods=['POST'])
def guardar_movimiento():
 f=request.form;tipo=f.get('tipo');cantidad=int(f.get('cantidad') or 0);pid=int(f['producto_id'])
 if tipo not in ('entrada','salida') or cantidad<=0:flash('Movimiento inválido','error');return redirect(url_for('index'))
 with conn() as c:
  producto=c.execute('SELECT stock FROM productos WHERE id=?',(pid,)).fetchone()
  if not producto or (tipo=='salida' and producto['stock']<cantidad):flash('Stock insuficiente o producto inexistente','error');return redirect(url_for('movimientos',tipo=tipo))
  c.execute('UPDATE productos SET stock=stock+? WHERE id=?',((cantidad if tipo=='entrada' else -cantidad),pid))
  c.execute('INSERT INTO movimientos(producto_id,tipo,cantidad,costo,referencia,observacion,fecha) VALUES (?,?,?,?,?,?,?)',(pid,tipo,cantidad,float(f.get('costo') or 0),f.get('referencia',''),f.get('observacion',''),datetime.now().strftime('%Y-%m-%d %H:%M')))
 flash('Movimiento registrado','ok');return redirect(url_for('movimientos',tipo=tipo))
@app.route('/ajustes',methods=['GET','POST'])
def ajustes():
 if request.method=='POST':
  with conn() as c:
   for k in ('spreadsheet_id','sheet_productos','sheet_categorias','sheet_movimientos'):
    c.execute('INSERT INTO configuracion(clave,valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor',(k,request.form.get(k,'').strip()))
  flash('Configuración guardada localmente. La sincronización todavía no está activada.','ok');return redirect(url_for('ajustes'))
 with conn() as c:config={r['clave']:r['valor'] for r in c.execute('SELECT * FROM configuracion')}
 return render_template('ajustes.html',page='ajustes',config=config)
if __name__=='__main__':init();app.run(debug=True,host='127.0.0.1',port=5001)
