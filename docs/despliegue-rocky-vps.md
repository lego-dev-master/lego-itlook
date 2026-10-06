# Derrotero de Despliegue — Lego ITlook en VPS Rocky Linux (Docker)

Guía paso a paso para desplegar la aplicación en un VPS con **Rocky Linux 9**,
usando **Docker + Docker Compose**, con dominio propio (GoDaddy) y **SSL gratuito
con Let's Encrypt (Certbot)**.

Arquitectura final:

```
Internet
   │  (80 / 443)
   ▼
[Nginx (contenedor)]  ──► [Gunicorn + Flask (contenedor web)]  ──► [PostgreSQL (contenedor db)]
   ▲
[Certbot (contenedor)]  (emite y renueva certificados)
```

---

## 0. Requisitos previos

- VPS con **Rocky Linux 9** (mínimo 1 GB RAM, recomendado 2 GB).
- Acceso `root` o un usuario con `sudo`.
- Un **dominio** en GoDaddy (ej: `midominio.co`).
- El código del proyecto subido al VPS (por Git o `scp`).

---

## 1. Preparar el DNS en GoDaddy

Desde la consola de GoDaddy (**Mi cuenta → Dominios → DNS / Administrar zonas**),
crea un **registro A** que apunte el subdominio a la IP pública de tu VPS:

| Tipo | Nombre | Valor            | TTL   |
|------|--------|------------------|-------|
| A    | itlook | `IP_DE_TU_VPS`   | 600   |

> - GoDaddy permite escribir solo `itlook` en el campo **Nombre** y el sistema
>   lo convierte en `itlook.midominio.co`.
> - Si quieres usar la raíz (`midominio.co`), usa `@` como nombre.
> - **NO** necesitas tocar los nameservers para esto; basta con el registro A.

**Verifica la propagación** (puede tardar de minutos a un par de horas):

```bash
# Desde tu PC local
nslookup itlook.midominio.co
# o
dig +short itlook.midominio.co
```

Debe devolver la **IP de tu VPS**. No continúes con el SSL hasta que esto funcione.

---

## 2. Preparar el firewall del VPS (Rocky Linux usa firewalld)

```bash
# Actualizar el sistema
sudo dnf -y update

# Abrir puertos HTTP y HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Verificar
sudo firewall-cmd --list-all
```

> **Nota Rocky Linux (SELinux):** Rocky trae SELinux en modo *enforcing*.
> Docker con los puertos mapeados (80/443) suele funcionar sin desactivar SELinux,
> siempre que Nginx corra **dentro de Docker** y no uses volúmenes con contexto
> incorrecto. Si en el paso 7 ves errores de permisos, revisa la sección
> **Errores comunes**.

---

## 3. Instalar Docker y Docker Compose en Rocky Linux

```bash
# Agregar el repositorio oficial de Docker
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Instalar Docker Engine y el plugin de Compose
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Habilitar e iniciar el servicio
sudo systemctl enable --now docker

# Verificar
docker --version
docker compose version
```

> El comando de Compose moderno es `docker compose` (con espacio), no `docker-compose`.

---

## 4. Subir el proyecto al VPS

Crea la carpeta y clona/subes el proyecto:

```bash
sudo mkdir -p /opt/itlook
sudo chown $USER:$USER /opt/itlook
cd /opt/itlook

# Opción A: desde Git
git clone <URL_DE_TU_REPO> .

# Opción B: desde tu PC local con scp
# scp -r ./lego-itlook/* usuario@IP_VPS:/opt/itlook/
```

Asegúrate de que existan estos archivos (los creamos/ajustamos para este deploy):

- `Dockerfile` (usa Gunicorn)
- `docker-compose.prod.yml`
- `wsgi.py`
- `nginx/conf.d/app.conf.http-only` y `nginx/conf.d/app.conf`
- `.dockerignore`

---

## 5. Crear el archivo `.env` (variables de producción)

En el VPS, dentro de `/opt/itlook`, crea el archivo `.env`:

```bash
nano .env
```

Contenido (ajusta los valores):

```dotenv
FLASK_ENV=prod

# Genera la SECRET_KEY con:  openssl rand -hex 32
SECRET_KEY=cambia_esto_por_una_clave_larga_y_aleatoria

POSTGRES_USER=itlook_user
POSTGRES_PASSWORD=UnaContrasenaFuerte2026!
POSTGRES_DB=itlook_db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_app_password_de_gmail
```

Genera la SECRET_KEY así:

```bash
openssl rand -hex 32
```

> El archivo `.dockerignore` ya excluye `.env`, así que **no** se copiará a la imagen.

---

## 6. Primer arranque (fase HTTP, SIN SSL todavía)

Para que Certbot pueda validar el dominio, primero levantamos Nginx por HTTP.

```bash
cd /opt/itlook

# (a) Empezar con la config SOLO HTTP
cp nginx/conf.d/app.conf.http-only nginx/conf.d/app.conf

# (b) Levantar los servicios
docker compose -f docker-compose.prod.yml up -d --build

# (c) Ver logs / estado
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
```

Verifica en el navegador (o con curl) que responda **por HTTP**:

```bash
curl -I http://itlook.midominio.co
```

Debe devolver `HTTP/1.1 200 OK` o un redirect al login. Si funciona, el DNS y
el proxy están correctos y ya podemos pedir el certificado.

> La app crea las tablas automáticamente al iniciar (`db.create_all()` en `wsgi.py`).
> La primera vez la base estará vacía; deberás crear tu usuario administrador
> (ver **Paso 9**).

---

## 7. Emitir el certificado SSL con Certbot

Ejecuta Certbot en modo **webroot** (publica el challenge en `/var/www/certbot`):

```bash
cd /opt/itlook

docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d itlook.midominio.co \
  --email tu_correo@gmail.com \
  --agree-tos --no-eff-email
```

Si todo va bien verás: `Congratulations! Your certificate...`.
El certificado queda en el volumen `certbot_conf` → `/etc/letsencrypt/live/itlook.midominio.co/`.

---

## 8. Activar HTTPS

Cambia la config de Nginx a la versión con SSL y reinicia Nginx:

```bash
cd /opt/itlook

# Usar la config con SSL (esta ya asume el dominio)
# Edita app.conf y reemplaza itlook.midominio.co por tu dominio real:
nano nginx/conf.d/app.conf

# Copia la versión completa (con bloques 80 y 443) que dejamos en el repo:
cp nginx/conf.d/app.conf app.conf.tmp && mv app.conf.tmp nginx/conf.d/app.conf
# (si ya editaste app.conf con tu dominio, omite esta línea y salta al reload)

# Recargar Nginx para tomar los cambios
docker compose -f docker-compose.prod.yml restart nginx
```

Prueba:

```bash
curl -I https://itlook.midominio.co
```

Debe responder `HTTP/2 200` y el navegador mostrar el candado.

> **Importante:** para que este paso funcione, el archivo `nginx/conf.d/app.conf`
> debe contener tu dominio real (no `itlook.midominio.co` de ejemplo) en:
> - `server_name`
> - `ssl_certificate` y `ssl_certificate_key`

---

## 9. Crear el usuario administrador

Con la base de datos vacía necesitas crear el primer admin. Opciones:

**Opción A — vía script (recomendado):** usa el seed existente adaptado o ejecuta
un shell dentro del contenedor:

```bash
docker compose -f docker-compose.prod.yml exec web python -c "
from app import create_app, db
from app.models.user import User
app = create_app('prod')
with app.app_context():
    if not User.query.filter_by(email='admin@midominio.co').first():
        u = User(name='Administrador', email='admin@midominio.co', role='admin')
        u.set_password('CambiaEstaClave123!')
        db.session.add(u); db.session.commit()
        print('Admin creado')
    else:
        print('El admin ya existe')
"
```

**Opción B — datos de demo:** ejecuta el script de seed si quieres datos de ejemplo:

```bash
docker compose -f docker-compose.prod.yml exec web python scripts/seed_db.py
```

Luego entra a `https://itlook.midominio.co` y haz login.

---

## 10. Renovación automática del certificado

Let's Encrypt emite certificados válidos por **90 días**. El contenedor `certbot`
queda en reposo y hay que lanzar la renovación periódicamente.

**Renovación manual (prueba):**

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew --dry-run
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml restart nginx
```

**Renovación automática con cron (recomendado):** añade una tarea al usuario:

```bash
crontab -e
```

Y agrega (ejecuta cada 12 h a las 3am y 3pm y recarga nginx):

```cron
0 3,15 * * * cd /opt/itlook && docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
```

---

## 11. Operación diaria (comandos útiles)

```bash
cd /opt/itlook
COMPOSE="docker compose -f docker-compose.prod.yml"

# Estado de los contenedores
$COMPOSE ps

# Ver logs en vivo
$COMPOSE logs -f web
$COMPOSE logs -f nginx

# Reiniciar la app tras cambios de código
git pull
$COMPOSE up -d --build web

# Apagar todo
$COMPOSE down

# Apagar y borrar volúmenes (¡CUIDADO: borra la BD!)
$COMPOSE down -v

# Backup de la base de datos
$COMPOSE exec db pg_dump -U itlook_user itlook_db > backup_$(date +%F).sql

# Restaurar backup
cat backup_2026-01-01.sql | $COMPOSE exec -T db psql -U itlook_user itlook_db
```

---

## 12. Checklist final

- [ ] Registro A en GoDaddy apunta a la IP del VPS (`dig +short itlook.midominio.co`).
- [ ] Firewalld permite 80 y 443.
- [ ] Docker y Docker Compose instalados.
- [ ] `.env` creado con SECRET_KEY y contraseñas fuertes.
- [ ] `docker compose up -d --build` levanta `db`, `web`, `nginx` (y `certbot`).
- [ ] HTTP responde antes de pedir el certificado.
- [ ] Certificado emitido con Certbot (`/etc/letsencrypt/live/<dominio>/`).
- [ ] `app.conf` apunta al dominio real en `server_name`, `ssl_certificate` y `ssl_certificate_key`.
- [ ] HTTPS responde con candado.
- [ ] Usuario administrador creado y login funcionando.
- [ ] Cron de renovación configurado.

---

## Errores comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `502 Bad Gateway` | El contenedor `web` aún no arrancó o crasheó | `docker compose logs web`; revisar `DATABASE_URL` |
| `404` en el challenge de Certbot | DNS no apunta al VPS o Nginx no sirve `/var/www/certbot` | Verifica `dig`, revisa el `location /.well-known/acme-challenge/` |
| Certbot: `Timeout during connect` | Puerto 80 cerrado | `firewall-cmd --add-service=http --permanent && --reload` |
| Nginx: `cannot load certificate` | Bloque 443 activo sin certificado | Usa primero `app.conf.http-only`, luego cambia a `app.conf` |
| `Connection refused` en app | Variables de entorno mal formadas en `.env` | Revisa `docker compose config` |
| Permisos en uploads | Volumen `uploads_data` con dueño incorrecto | `docker compose exec web chown -R root:root /app/app/static/uploads` |
| SECRET_KEY expuesta | No se cambió el default | Regenerar con `openssl rand -hex 32` y reiniciar |

---

## Notas de seguridad recomendadas

1. **Nunca expongas PostgreSQL al host** (en `docker-compose.prod.yml` el `db` no
   publica puertos; así está bien).
2. Cambia la `SECRET_KEY` y la contraseña de PostgreSQL por valores fuertes.
3. Considera **fail2ban** y **actualizaciones automáticas** (`dnf-automatic`).
4. Haz **backups periódicos** de la base (`pg_dump`) y de `uploads_data`.
5. El `cmd` del `Dockerfile` con `debug=True` de `run.py` **no** se usa en prod;
   en producción se usa `wsgi.py` + Gunicorn (ya configurado).
