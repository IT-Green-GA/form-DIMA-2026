# Apuntes de la sesión — Bitácora de parcela

Fecha: 20/10/2026  
Proyecto: `form-DIMA-2026` (Bitácora de parcela)

---

## 1. Ubicación del proyecto

```
C:\Users\arher\develop\form-DIMA-2026
```

Archivos principales:

| Archivo | Para qué sirve |
|---|---|
| `index.html` | Formulario y lista de registros. |
| `src/main.js` | Conexión con Supabase; guarda y consulta registros. |
| `src/style.css` | Estilos de la aplicación. |
| `server.js` | Servidor para la versión construida (`pnpm start`). |
| `vite.config.js` | Variables de `.env` que sí llegan al navegador. |
| `.env.example` | Plantilla de variables, sin valores. |
| `.env.local` | Variables locales con tus contraseñas reales. |
| `equipos.md` | Lista de equipos del curso. |

---

## 2. Cómo se abrió el formulario

1. Se revisaron los archivos del proyecto y se detectó que era una app de Vite + Supabase.
2. Se instaló `pnpm@11.5.0` (coincide con el declarado en `package.json`).
3. Se ejecutó `pnpm install` para descargar dependencias.
4. Se levantó Vite con:

   ```bash
   pnpm dev --port 5173 --strictPort
   ```

5. Se abrió en el navegador: **http://localhost:5173** (HTTP 200).

---

## 3. Cómo se abrió en VS Code

Se usó el binario local:

```
C:\Users\arher\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd
```

Comando equivalente para futuras sesiones:

```bash
code "C:\Users\arher\develop\form-DIMA-2026"
```

---

## 4. Archivo `.env.local` (credenciales)

Ruta: `C:\Users\arher\develop\form-DIMA-2026\.env.local`

Contenido actual (con campos vacíos para que tú los rellenes):

```env
# URL de tu proyecto en Supabase
# (Project Settings -> API -> Project URL)
SUPABASE_URL=

# Llave publicable (antes "anon key")
# (Project Settings -> API -> Publishable key)
# Debe empezar con sb_publishable_
SUPABASE_PUBLISHABLE_KEY=

# Token opcional de OpenRouter si lo llegas a usar
OPENROUTER_API_KEY=
```

### Cómo obtener los valores

1. Entra a tu proyecto en Supabase.
2. Abre **Project Settings → API**.
3. Copia:
   - **Project URL** → `SUPABASE_URL`
   - **Publishable key** (empieza con `sb_publishable_`) → `SUPABASE_PUBLISHABLE_KEY`
4. Guarda el archivo. Vite recarga solo.

### Reglas importantes

- **Nunca** pegar aquí la llave `service_role`; esa es secreta.
- `.env.local` está en `.gitignore`, no se sube al repo.
- Si cambias `.env.local`, no necesitas reiniciar Vite.

---

## 5. Verificar que el servidor sigue arriba

```bash
curl http://localhost:5173
```

Si está caído, relanzarlo:

```bash
cd "C:\Users\arher\develop\form-DIMA-2026"
pnpm dev --port 5173 --strictPort
```

Para detenerlo: cerrar la ventana del shell donde se ejecutó `pnpm dev`.

---

## 6. Pendientes

- [ ] Rellenar `SUPABASE_URL` en `.env.local`.
- [ ] Rellenar `SUPABASE_PUBLISHABLE_KEY` en `.env.local`.
- [ ] (Opcional) Rellenar `OPENROUTER_API_KEY` en `.env.local`.
- [ ] Verificar que la tabla `registros` exista en Supabase con las columnas del README.
- [ ] Confirmar políticas RLS si están activas.
- [ ] Probar guardar un registro desde http://localhost:5173.

---

## 7. Resumen rápido

- Proyecto: `C:\Users\arher\develop\form-DIMA-2026`
- Servidor local: http://localhost:5173
- Editor: VS Code
- Credenciales: `.env.local` (vacío, listo para llenar)