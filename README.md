# mp-equipos-seguridad

Monitor automático de licitaciones de Mercado Público para **Mitosis Seguridad**,
enfocado en equipos y personal de seguridad privada.

Corre lunes a viernes a las 11:00 y 12:00 UTC vía GitHub Actions.

## Categorías monitoreadas

| # | Categoría | Keywords (OR) |
|---|---|---|
| 1 | Guardias y vigilantes | `guardias`, `vigilantes` |
| 2 | Elementos defensivos y de protección | `elementos defensivos`, `elementos de protección` |
| 3 | Chalecos de protección | `chalecos anticortes`, `chalecos antibalas` |

Las keywords de múltiples palabras se buscan como **frase exacta**.
Una licitación puede aparecer en más de una sección si matchea keywords de distintas categorías.

## Estructura

```
mp-equipos-seguridad/
├── monitor_equipos.py          ← script principal
├── config.py                   ← categorías y keywords (editar acá)
├── mitosis_logo.png            ← logo embebido en el correo
├── requirements.txt
├── seen.json                   ← deduplicación (no editar manualmente)
├── README.md
└── .github/
    └── workflows/
        └── monitor_equipos.yml
```

## Setup

### 1. Crear repo en GitHub

Repo privado con nombre `mp-equipos-seguridad`. Subir todos los archivos
respetando la estructura, incluido `mitosis_logo.png` en la raíz.

### 2. Habilitar permisos de escritura

**Settings → Actions → General → Workflow permissions** →
seleccionar **Read and write permissions**.

### 3. Configurar secrets

**Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|--------|-------|
| `MP_TICKET` | Ticket de la API de Mercado Público |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | Correo remitente |
| `SMTP_PASSWORD` | Contraseña de aplicación Gmail |
| `NOTIFY_TO` | Correo(s) destinatarios separados por coma |

> Los secrets son **por repo** — hay que crearlos aunque ya estén en otros monitores.

### 4. Primer run (bootstrap)

**Actions → Monitor MP - Equipos de Seguridad → Run workflow**

La primera ejecución guarda todos los IDs actuales en `seen.json` sin enviar correo.
Desde la segunda ejecución notifica solo licitaciones nuevas.

### Test forzado

Agregar secret `NOTIFY_ALWAYS` = `true` y correr el workflow manualmente.
Envía correo aunque no haya licitaciones nuevas.

## Personalización

Para agregar o quitar keywords, editar `config.py`:

```python
{
    "nombre": "1. Guardias y vigilantes",
    "keywords": ["guardias", "vigilantes", "guardia de seguridad"],
}
```

Las frases exactas (con espacio) requieren que ambas palabras aparezcan
en ese orden en el nombre o descripción de la licitación.
