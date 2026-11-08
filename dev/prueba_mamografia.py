"""Prueba automática de pacs-rismed (solo mamografía): agenda + PACS.

Requiere corriendo (igual que dev/prueba_agenda.py):
  - dev/mock_orthanc.py                        (PACS simulado en :8042)
  - la app de informes en :8000 con ADMIN_PASSWORD=clave-prueba-123 INTEGRACION_TOKEN=token-prueba (base vacía)
  - la agenda en :3000 con ADMIN_CLAVE=clave-agenda-123 PACS_URL=http://localhost:8000
    INTEGRACION_TOKEN=token-prueba PORTAL_URL=http://localhost:8000/paciente PACS_INTERVALO_SEG=5

    python dev/prueba_mamografia.py
"""
import re
import sys
import time
from datetime import date

import requests

A, P = "http://localhost:3000", "http://localhost:8000"
fallas = 0


def chk(c, m):
    global fallas
    fallas += (not c)
    print(("OK   " if c else "FALLA ") + m)


def esperar(cond, seg=30):
    t = time.time()
    while time.time() - t < seg:
        if cond():
            return True
        time.sleep(0.5)
    return False


hoy = date.today().isoformat()
ag = requests.Session()
chk(ag.post(A + "/api/login", json={"usuario": "admin", "clave": "clave-agenda-123"}).ok, "login agenda")

# --- arancel: solo mamografía, Fonasa MLE 2026 nivel 3
ar = {a["codigo"]: a for a in ag.get(A + "/api/aranceles").json()}
chk(set(ar) == {"0401010", "0401110", "0401130"}, f"arancel solo con las 3 mamografías ({sorted(ar)})")
b = ar.get("0401010", {})
chk(b.get("equipo") == "mx" and b.get("fonasa_total") == 37600 and b.get("fonasa_bonif") == 11750,
    "mamografía bilateral: valor nivel 3 $37.600, bonificación $11.750")

# --- solo se agenda en el mamógrafo
r = ag.post(A + "/api/citas", json={"fecha": hoy, "hora": "09:00", "equipo": "tc", "paciente": "No Va", "prevision": "Particular"})
chk(r.status_code == 400, "no deja agendar en un equipo que no existe (TC)")

cita = ag.post(A + "/api/citas", json={"fecha": hoy, "hora": "10:00", "duracion": 15, "equipo": "mx",
                                       "paciente": "Rosa Elena Pérez Soto", "rut": "11.111.111-1", "fecha_nac": "1970-03-04",
                                       "prevision": "Fonasa", "codigo": "0401010", "examen": "Mamografía bilateral"}).json()
chk(cita.get("valor") == 37600 and cita.get("bonificacion") == 11750 and cita.get("copago") == 25850,
    f"cita Fonasa: valor, bonificación y copago nivel 3 ({cita.get('valor')}, {cita.get('bonificacion')}, {cita.get('copago')})")
acc = cita.get("accesion", "")
chk(bool(re.fullmatch(r"AG\d{8}", acc)), f"número de acceso al agendar ({acc})")

r = ag.post(A + f"/api/citas/{cita['id']}/pago", json={"medio": "Efectivo", "folio_bono": "123456"}).json()
clave = (r.get("portal") or {}).get("clave", "")
chk(len(clave) == 8, "al pagar se crea la clave del portal de pacientes")


def cita_de(id_):
    return next((c for c in ag.get(A + f"/api/citas?fecha={hoy}").json() if c["id"] == id_), {})


# --- llega la mamografía con su número de acceso (modalidad MG)
time.sleep(1.5)
requests.post("http://localhost:8042/dev/llega", json={"AccessionNumber": acc, "PatientID": "11111111-1",
                                                       "PatientName": "PEREZ SOTO^ROSA ELENA", "Modality": "MG",
                                                       "StudyDescription": "MAMOGRAFIA BILATERAL"})
chk(esperar(lambda: cita_de(cita["id"]).get("pacs_estado") == "imagenes"), "la mamografía (MG) se une a su cita")

# --- sin worklist y el lector CR envía modalidad CR: se une por RUT + fecha + equipo
c2 = ag.post(A + "/api/citas", json={"fecha": hoy, "hora": "11:00", "equipo": "mx", "paciente": "Carmen Sin Worklist",
                                     "rut": "15.555.555-5", "prevision": "Fonasa", "codigo": "0401110",
                                     "examen": "Mamografía unilateral"}).json()
chk(c2.get("valor") == 22080 and c2.get("copago") == 15180, "mamografía unilateral nivel 3 ($22.080, copago $15.180)")
ag.post(A + f"/api/citas/{c2['id']}/pago", json={"medio": "Efectivo", "folio_bono": "123457"})
time.sleep(1.5)
requests.post("http://localhost:8042/dev/llega", json={"AccessionNumber": "CRMANUAL1", "PatientID": "15555555-5",
                                                       "PatientName": "SIN WORKLIST^CARMEN", "Modality": "CR",
                                                       "StudyDescription": "MAMOGRAFIA"})
chk(esperar(lambda: cita_de(c2["id"]).get("pacs_estado") == "imagenes"), "sin worklist y con modalidad CR: se une por RUT")

# --- plantillas e informes de mamografía en el PACS
adm = requests.Session()
adm.post(P + "/login", data={"usuario": "admin", "clave": "clave-prueba-123"})
t = adm.get(P + "/admin/plantillas").text
chk("Mamografía bilateral normal" in t and "TC de cerebro" not in t, "plantillas del PACS: solo mamografía")
t = adm.get(P + "/admin/frases").text
chk("BI-RADS 3" in t, "frases rápidas con BI-RADS")

print()
print("TODO OK" if not fallas else f"{fallas} FALLA(S)")
sys.exit(1 if fallas else 0)
