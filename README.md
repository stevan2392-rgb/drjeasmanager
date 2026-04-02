# Inventario Bicis – Panel Flask + SQLite

Aplicación en Flask para administrar inventarios, compras, clientes, facturas, remisiones y recordatorios de mantenimiento para Ciclo Variedades Sisi.  
El repositorio incluye dos partes:

1. **Backend completo (Flask/SQLite)** – donde se encuentra el panel con todas las funciones.
2. **Landing estática (`docs/`)** – usada por GitHub Pages o Netlify para mostrar información pública mientras el backend corre en otro hosting.

> GitHub Pages/Netlify solo pueden publicar la carpeta `docs/`. Para ver el panel completo necesitas ejecutar el backend (localmente o en un servicio con soporte Python/WSGI).

## Requisitos

- Python 3.11+ (se recomienda 3.12.x)
- Pip y virtualenv

## Instalación local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Variables de entorno

Duplica `.env.example` como `.env` y ajusta tus credenciales:

```powershell
Copy-Item .env.example .env
```

Campos disponibles:

- `SMTP_*` para el envío de correos (facturas/remisiones).
- `TWILIO_*` para WhatsApp opcional.
- `DEFAULT_COUNTRY_CODE` prefijo telefónico (57 por defecto).
- **Opcionales para despliegues remotos**  
  - `DATABASE_PATH=/var/data/inventario.db` → ruta absoluta donde guardar el SQLite.  
  - `DATABASE_URL=sqlite:////var/data/inventario.db` → usa esta opción si prefieres pasar la URL completa a SQLAlchemy.

Si ninguno de esos campos se define, la aplicación crea `inventario.db` junto al archivo `app.py`.

## Ejecución (modo desarrollo)

```powershell
$env:FLASK_APP = 'app.py'
$env:FLASK_ENV = 'development'
python app.py
```

La app se expone en `http://127.0.0.1:5000`.

## Despliegues recomendados

### 1. Landing estática (GitHub Pages / Netlify)

- El contenido público vive en `docs/`.
- GitHub Pages: habilita Pages desde la pestaña *Pages* y selecciona *Branch: main / Folder: /docs*.  
- Netlify: configura el repo con `publish = "docs"` (ya está definido en `netlify.toml`).
- Personaliza el contenido de `docs/index.html` para enlazar al backend ya desplegado.

### 2. Backend completo en Render (recomendado)

Este repo incluye un `render.yaml` listo para usar con **Render Blueprints**:

1. Crea una cuenta en [Render](https://dashboard.render.com/).
2. En la barra superior elige **Blueprints → New Blueprint** y proporciona la URL del repo (`https://github.com/stevan2392-rgb/drjeasmanager`).
3. Render detectará `render.yaml` y creará un servicio tipo **Web (Python)** con:
   - `buildCommand`: `pip install --upgrade pip && pip install -r requirements.txt`
   - `startCommand`: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Un disco persistente montado en `/var/data` (se usa para guardar `inventario.db`).
4. Ajusta las variables de entorno en el panel:
   - `FLASK_ENV=production`
   - `DATABASE_PATH=/var/data/inventario.db`
   - Credenciales SMTP/Twilio necesarias.
5. Pulsa **Deploy**. Render asignará una URL como `https://inventario-bicis.onrender.com`.

> Render usa `runtime.txt` para conocer la versión de Python y respeta `DATABASE_PATH`, por lo que no necesitas tocar el código para cambiar la ubicación de la base de datos.

### 3. Backend completo en Railway

Railway puede desplegar este repo directamente desde GitHub usando el `Procfile`.

1. Entra a [Railway](https://railway.com/) y crea un proyecto nuevo.
2. Elige **Deploy from GitHub repo** y selecciona este repositorio.
3. Railway detectarÃ¡ Python y usarÃ¡ este comando de inicio:  
   `gunicorn app:app --bind 0.0.0.0:${PORT:-8000}`
4. Dentro del servicio crea un **Volume** y mÃ³ntalo, por ejemplo, en `/data`.
5. En variables de entorno define:
   - `DATABASE_PATH=/data/inventario.db`
   - `FLASK_ENV=production`
6. Si vas a usar correo o WhatsApp, agrega tambiÃ©n tus variables `SMTP_*` y `TWILIO_*`.
7. Usa `/health` como healthcheck.

> Railway usa un sistema de archivos efÃ­mero por defecto. Si no montas un Volume o no apuntas `DATABASE_PATH` al volumen, la base SQLite se puede perder al reiniciar o redeployar.

La app tambiÃ©n detecta `RAILWAY_VOLUME_MOUNT_PATH` automÃ¡ticamente si Railway lo expone y no definiste `DATABASE_PATH`.

### 4. Otros proveedores (Fly.io, etc.)

El `Procfile` contiene `web: gunicorn app:app --bind 0.0.0.0:${PORT:-8000}`.  
Para otros hosts repite la configuración:

1. Instala dependencias (`pip install -r requirements.txt`).
2. Define variables de entorno (en especial `DATABASE_PATH` si usas almacenamiento persistente).
3. Ejecuta `gunicorn app:app`.

## Vincular la landing con el backend

1. Despliega el backend (p.ej., en Render).
2. Abre `docs/index.html` y reemplaza los botones/enlaces con la URL pública recién creada.
3. Vuelve a publicar la carpeta `docs/` (GitHub Pages o Netlify) para que tus usuarios lleguen directamente al panel real.

Con esto obtienes:

- **URL pública para el panel real** (Render/Railway/Fly).
- **URL informativa** en GitHub Pages/Netlify que puedes usar como landing o catálogo.

Si necesitas automatizar el deploy o agregar otra plataforma, crea un issue o ajusta el `render.yaml` a tus necesidades.
