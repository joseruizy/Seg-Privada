#!/usr/bin/env python3
"""
Monitor de Mercado Público — Equipos de Seguridad (Mitosis Seguridad)
Detecta licitaciones nuevas en 3 categorías temáticas:
  1. Guardias y vigilantes
  2. Elementos defensivos y de protección
  3. Chalecos de protección

Corre vía GitHub Actions (lun–vie, 11:00 y 12:00 UTC).
"""

import base64
import json
import os
import re
import smtplib
import time
import unicodedata
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

from config import CATEGORIAS, TIPOS_ACTIVOS

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
API_BASE   = "https://api.mercadopublico.cl/servicios/v1/publico"
SEEN_FILE  = Path(__file__).parent / "seen.json"
LOGO_FILE  = Path(__file__).parent / "mitosis_logo.png"

COLOR_HEADER  = "#853D93"
COLOR_ACCENT  = "#7C408E"
COLOR_LIGHT   = "#F3EBF7"

# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Minúsculas sin tildes."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def keywords_que_matchean(nombre: str, descripcion: str, keywords: list[str]) -> list[str]:
    """Retorna las keywords de la lista que aparecen en nombre o descripción."""
    haystack = normalizar(f"{nombre} {descripcion}")
    encontradas = []
    for kw in keywords:
        kw_norm = normalizar(kw)
        if kw_norm in haystack:
            encontradas.append(kw)
    return encontradas


# ---------------------------------------------------------------------------
# API Mercado Público
# ---------------------------------------------------------------------------

def ticket() -> str:
    t = os.environ.get("MP_TICKET", "")
    if not t:
        raise ValueError("MP_TICKET no está configurado")
    return t


def fecha_str(d: date) -> str:
    return d.strftime("%d%m%Y")


def get_licitaciones_fecha(fecha: date, retries: int = 3) -> list[dict]:
    """Lista licitaciones publicadas en una fecha (paginación completa)."""
    url    = f"{API_BASE}/licitaciones.json"
    params = {
        "ticket": ticket(),
        "fecha":  fecha_str(fecha),
        "estado": 5,
    }
    resultados = []
    for intento in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            items = data.get("Listado", []) or []
            resultados = items
            break
        except Exception as e:
            if intento < retries - 1:
                time.sleep(2 ** intento)
            else:
                print(f"[WARN] Error consultando fecha {fecha}: {e}")
    return resultados


def get_detalle(codigo: str, retries: int = 3) -> dict:
    """Detalle completo de una licitación."""
    url    = f"{API_BASE}/licitaciones.json"
    params = {"ticket": ticket(), "codigo": codigo}
    for intento in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            listado = data.get("Listado", []) or []
            if listado:
                return listado[0]
        except Exception as e:
            if intento < retries - 1:
                time.sleep(2 ** intento)
            else:
                print(f"[WARN] Error obteniendo detalle {codigo}: {e}")
    return {}


# ---------------------------------------------------------------------------
# Deduplicación
# ---------------------------------------------------------------------------

def cargar_seen() -> set[str]:
    if SEEN_FILE.exists():
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def guardar_seen(ids: set[str]):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Matching de categorías
# ---------------------------------------------------------------------------

def categorias_que_matchean(nombre: str, descripcion: str) -> list[dict]:
    """
    Retorna lista de {categoria, keywords_encontradas} para cada categoría
    que tenga al menos una keyword presente.
    """
    resultado = []
    for cat in CATEGORIAS:
        encontradas = keywords_que_matchean(nombre, descripcion, cat["keywords"])
        if encontradas:
            resultado.append({
                "categoria": cat["nombre"],
                "keywords":  encontradas,
            })
    return resultado


# ---------------------------------------------------------------------------
# Construcción del correo HTML
# ---------------------------------------------------------------------------

def logo_base64() -> str:
    if LOGO_FILE.exists():
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def tipo_legible(tipo: str) -> str:
    mapa = {"LS": "LS", "L1": "L1", "LE": "LE", "LP": "LP"}
    return mapa.get(tipo.upper(), tipo)


def formato_monto(valor) -> str:
    if valor is None:
        return "—"
    try:
        v = float(str(valor).replace(".", "").replace(",", "."))
        if v == 0:
            return "—"
        return f"${v:,.0f}".replace(",", ".")
    except Exception:
        return str(valor)


def fila_licitacion(lic: dict, keywords_encontradas: list[str]) -> str:
    codigo       = lic.get("CodigoExterno", "")
    nombre       = lic.get("Nombre", "")
    organismo    = lic.get("NombreOrganismo", lic.get("Organismo", {}).get("Nombre", ""))
    tipo         = tipo_legible(lic.get("Tipo", ""))
    monto        = formato_monto(lic.get("MontoEstimado"))
    fecha_cierre = (lic.get("FechaCierre") or "")[:10]
    url_lic      = f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?qs=OHaHMCz2Qp2tmkbh/lDvbw=="
    url_lic      = f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?CodigoExterno={codigo}"

    kws_html = " ".join(
        f'<span style="background:{COLOR_LIGHT};color:{COLOR_ACCENT};'
        f'font-weight:700;padding:1px 5px;border-radius:3px;font-size:11px;">{kw}</span>'
        for kw in keywords_encontradas
    )

    return f"""
    <tr style="border-bottom:1px solid #eee;">
      <td style="padding:7px 8px;font-size:12px;">
        <a href="{url_lic}" style="color:{COLOR_ACCENT};font-weight:600;text-decoration:none;">{codigo}</a>
      </td>
      <td style="padding:7px 8px;font-size:12px;">{nombre}</td>
      <td style="padding:7px 8px;font-size:12px;">{organismo}</td>
      <td style="padding:7px 8px;font-size:12px;text-align:center;">{tipo}</td>
      <td style="padding:7px 8px;font-size:12px;text-align:right;">{monto}</td>
      <td style="padding:7px 8px;font-size:12px;text-align:center;">{fecha_cierre}</td>
      <td style="padding:7px 8px;font-size:12px;">{kws_html}</td>
    </tr>"""


def seccion_categoria(nombre_cat: str, filas: list[str], keywords_config: list[str]) -> str:
    kws_display = " · ".join(
        f'<code style="font-size:11px;background:#f0e8f4;padding:1px 4px;border-radius:2px;">{k}</code>'
        for k in keywords_config
    )
    tabla_filas = "\n".join(filas) if filas else (
        '<tr><td colspan="7" style="padding:12px;text-align:center;color:#999;font-size:12px;">'
        'Sin licitaciones nuevas en este período.</td></tr>'
    )
    return f"""
    <div style="margin-bottom:28px;">
      <h2 style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:{COLOR_ACCENT};">{nombre_cat}</h2>
      <p style="margin:0 0 10px 0;font-size:11px;color:#888;">Palabras clave: {kws_display}</p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;font-family:Arial,sans-serif;">
        <thead>
          <tr style="background:{COLOR_LIGHT};">
            <th style="padding:7px 8px;text-align:left;font-size:11px;color:#555;font-weight:700;white-space:nowrap;">Código</th>
            <th style="padding:7px 8px;text-align:left;font-size:11px;color:#555;font-weight:700;">Nombre</th>
            <th style="padding:7px 8px;text-align:left;font-size:11px;color:#555;font-weight:700;">Organismo</th>
            <th style="padding:7px 8px;text-align:center;font-size:11px;color:#555;font-weight:700;">Tipo</th>
            <th style="padding:7px 8px;text-align:right;font-size:11px;color:#555;font-weight:700;">Monto</th>
            <th style="padding:7px 8px;text-align:center;font-size:11px;color:#555;font-weight:700;white-space:nowrap;">Cierre</th>
            <th style="padding:7px 8px;text-align:left;font-size:11px;color:#555;font-weight:700;">Coincidencia</th>
          </tr>
        </thead>
        <tbody>
          {tabla_filas}
        </tbody>
      </table>
    </div>"""


def build_email_html(resultados_por_cat: dict, fechas_consultadas: list[date]) -> str:
    """
    resultados_por_cat: {nombre_cat: [(lic_dict, [keywords_encontradas])]}
    """
    logo_b64  = logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'alt="Mitosis Seguridad" style="height:38px;display:block;">'
        if logo_b64 else
        '<span style="color:#fff;font-size:16px;font-weight:700;">Mitosis Seguridad</span>'
    )

    fechas_str = ", ".join(f.strftime("%d-%m-%Y") for f in fechas_consultadas)
    total = sum(len(v) for v in resultados_por_cat.values())

    secciones_html = []
    for cat in CATEGORIAS:
        nombre_cat = cat["nombre"]
        items      = resultados_por_cat.get(nombre_cat, [])
        filas      = [fila_licitacion(lic, kws) for lic, kws in items]
        secciones_html.append(
            seccion_categoria(nombre_cat, filas, cat["keywords"])
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:6px;overflow:hidden;
                    box-shadow:0 2px 8px rgba(0,0,0,.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:{COLOR_HEADER};padding:16px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>{logo_html}</td>
                <td align="right" style="color:#fff;font-size:12px;line-height:1.5;">
                  <strong>Monitor · Equipos de Seguridad</strong><br>
                  Fechas consultadas: {fechas_str}<br>
                  {total} licitación{'es' if total != 1 else ''} nueva{'s' if total != 1 else ''}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="padding:24px 24px 8px 24px;">
            {''.join(secciones_html)}
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="padding:12px 24px 16px 24px;border-top:1px solid #eee;">
            <p style="margin:0;font-size:10px;color:#aaa;text-align:center;">
              Mitosis Seguridad · Monitor automático Mercado Público ·
              <a href="https://www.mercadopublico.cl" style="color:{COLOR_ACCENT};text-decoration:none;">
                mercadopublico.cl
              </a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Envío de correo
# ---------------------------------------------------------------------------

def send_email(subject: str, html_body: str):
    host     = os.environ["SMTP_HOST"]
    port     = int(os.environ["SMTP_PORT"])
    user     = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    notify   = os.environ["NOTIFY_TO"]

    destinatarios = [d.strip() for d in notify.split(",") if d.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Mitosis Seguridad <{user}>"
    msg["To"]      = ", ".join(destinatarios)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, destinatarios, msg.as_string())

    print(f"[OK] Correo enviado a: {', '.join(destinatarios)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fechas_a_consultar() -> list[date]:
    hoy = date.today()
    fechas = [hoy]
    if hoy.weekday() == 0:          # lunes → agregar viernes y sábado
        fechas += [hoy - timedelta(days=2), hoy - timedelta(days=1)]
    return fechas


def main():
    notify_always = os.environ.get("NOTIFY_ALWAYS", "").lower() in ("1", "true", "yes")

    seen   = cargar_seen()
    nuevos = set()

    fechas = fechas_a_consultar()
    print(f"[INFO] Consultando fechas: {[str(f) for f in fechas]}")

    # Recopilar todas las licitaciones nuevas del período
    licitaciones_raw: list[dict] = []
    for fecha in fechas:
        items = get_licitaciones_fecha(fecha)
        print(f"[INFO] {fecha}: {len(items)} licitaciones en API")
        for item in items:
            codigo = item.get("CodigoExterno", "")
            tipo   = item.get("Tipo", "")
            if not codigo or tipo not in TIPOS_ACTIVOS:
                continue
            if codigo in seen:
                continue
            licitaciones_raw.append(item)
            nuevos.add(codigo)
        time.sleep(0.5)

    print(f"[INFO] Licitaciones nuevas del tipo correcto: {len(licitaciones_raw)}")

    # Bootstrap: primer run guarda IDs y sale sin enviar correo
    if not seen and not notify_always:
        seen.update(nuevos)
        guardar_seen(seen)
        print("[INFO] Bootstrap: seen.json inicializado. No se envía correo.")
        return

    # Obtener detalle de cada licitación nueva y hacer matching
    resultados_por_cat: dict[str, list] = {cat["nombre"]: [] for cat in CATEGORIAS}

    for item in licitaciones_raw:
        codigo = item.get("CodigoExterno", "")
        print(f"[INFO] Detalle: {codigo}")
        detalle = get_detalle(codigo)
        if not detalle:
            detalle = item
        time.sleep(1)

        nombre      = detalle.get("Nombre", item.get("Nombre", ""))
        descripcion = detalle.get("Descripcion", "")

        matches = categorias_que_matchean(nombre, descripcion)
        for m in matches:
            resultados_por_cat[m["categoria"]].append((detalle if detalle else item, m["keywords"]))

    total = sum(len(v) for v in resultados_por_cat.values())
    print(f"[INFO] Total resultados en categorías: {total}")

    # Guardar nuevos IDs independientemente de si hay matches
    seen.update(nuevos)
    guardar_seen(seen)

    # No enviar si no hay nada nuevo (a menos que NOTIFY_ALWAYS)
    if total == 0 and not notify_always:
        print("[INFO] Sin licitaciones nuevas que notificar.")
        return

    # Construir y enviar correo
    fecha_label = fechas[0].strftime("%d-%m-%Y")
    subject     = f"[MP Equipos Seguridad] {total} licitación{'es' if total != 1 else ''} nueva{'s' if total != 1 else ''} — {fecha_label}"
    html        = build_email_html(resultados_por_cat, fechas)
    send_email(subject, html)


if __name__ == "__main__":
    main()
