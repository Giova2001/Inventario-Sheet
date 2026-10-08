# Inventario Creativa Studios — Flask

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abrir http://127.0.0.1:5000

El archivo `inventario.db` se crea automáticamente con datos de ejemplo.

## Funcionalidad
- Productos: crear, buscar, editar, eliminar (si no tienen movimientos).
- Categorías: crear, editar y eliminar (si están vacías).
- Entradas y salidas: registro con actualización de stock e historial.
- Ajustes: almacenamiento local del ID y nombres de hojas de Google Sheets.

## Google Sheets
**Todavía no hay conexión activa a Google Sheets.** La pantalla Ajustes únicamente guarda la configuración para implementar la integración después. Las credenciales de cuenta de servicio deben mantenerse en el servidor, fuera del repositorio y nunca exponerse en HTML.

## Importante
Proyecto inicial para desarrollo local, no listo para exposición pública: antes de producción, desactivar debug, definir FLASK_SECRET_KEY seguro, agregar autenticación, protección CSRF y controles de acceso.
