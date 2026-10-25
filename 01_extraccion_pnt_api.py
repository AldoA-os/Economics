"""
Módulo de Extracción Masiva de Directorios Públicos - Plataforma Nacional de Transparencia (PNT).
Autor: Aldo Uriel Álvarez Vargas
"""

import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
import pandas as pd

# Configuración global de bitácora (logging) con formato de fecha, nivel y mensaje
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constantes de configuración de la API del Buscador Temático de la PNT
API_URL = "https://backbuscadortematico.plataformadetransparencia.org.mx/api/tematico/buscador/consulta"
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
    "Referer": "https://tematicos.plataformadetransparencia.org.mx/"
}


def construir_payload(entidad: str, pagina: int, cantidad: int) -> Dict[str, Any]:
    """Construye el cuerpo JSON (payload) requerido por el endpoint POST de la PNT."""
    return {
        "contenido": entidad,
        "cantidad": cantidad,
        "numeroPagina": pagina,
        "coleccion": "DIRECTORIO",
        "dePaginador": True,
        "idCompartido": "",
        "filtroSeleccionado": "",
        "tipoOrdenamiento": "COINCIDENCIA",
        "sujetosObligados": {"seleccion": [], "descartado": []},
        "organosGarantes": {"seleccion": [], "descartado": []},
        "anioFechaInicio": {"seleccion": [], "descartado": []}
    }


def parsear_registro(reg: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extrae y aplana los campos relevantes de cada documento devuelto por Solr."""
    info = reg.get("informacionPrincipal") or {}
    return {
        "Entidad": reg.get("entidadfederativa"),
        "Sujeto Obligado / Institución": reg.get("sujetoobligado"),
        "Periodo Reportado": reg.get("periodoreporta"),
        "Nombre Completo": reg.get("nombre"),
        "Cargo / Denominación": reg.get("denominacion"),
        "Área de Adscripción": reg.get("areaadscripcion"),
        "Teléfono": info.get("telefono"),
        "Correo Electrónico": info.get("correo"),
        "Dirección": info.get("direccion"),
        "ID Registro": reg.get("id")
    }


def extraer_datos_pnt(
    entidad: str = "Hidalgo",
    cantidad_por_pagina: int = 900,
    max_intentos: int = 5,
    timeout: int = 20,
    pausa_entre_paginas: float = 2.0
) -> List[Dict[str, Optional[str]]]:
    """
    Ejecuta la extracción paginada tolerante a fallos desde la API de la PNT.
    """
    todos_los_datos: List[Dict[str, Optional[str]]] = []
    pagina_actual = 1

    logging.info(f"Iniciando extracción masiva de la PNT para la entidad: {entidad}...")

    # Uso de Session() para reutilizar la conexión TCP (Keep-Alive) y mejorar el rendimiento
    with requests.Session() as session:
        session.headers.update(DEFAULT_HEADERS)

        while True:
            payload = construir_payload(entidad, pagina_actual, cantidad_por_pagina)
            intentos = 0
            exito_pagina = False

            # Bucle de reintentos ante errores HTTP (ej. 520) o cortes de conexión
            while intentos < max_intentos and not exito_pagina:
                try:
                    response = session.post(API_URL, json=payload, timeout=timeout)

                    if response.status_code == 200:
                        datos_json = response.json()
                        payload_respuesta = datos_json.get("paylod") or {}
                        registros = payload_respuesta.get("datosSolr") or []

                        if not registros:
                            logging.info(
                                f"Fin de resultados alcanzado en la página {pagina_actual}."
                            )
                            return todos_los_datos

                        for reg in registros:
                            todos_los_datos.append(parsear_registro(reg))

                        logging.info(
                            f"Página {pagina_actual} procesada con éxito. "
                            f"Total acumulado: {len(todos_los_datos):,} registros."
                        )
                        exito_pagina = True

                    else:
                        intentos += 1
                        logging.warning(
                            f"Respuesta HTTP {response.status_code} en página {pagina_actual}. "
                            f"Reintento {intentos}/{max_intentos} en 3s..."
                        )
                        time.sleep(3)

                except requests.exceptions.RequestException as exc:
                    intentos += 1
                    logging.warning(
                        f"Corte de conexión en página {pagina_actual} ({exc}). "
                        f"Reintento {intentos}/{max_intentos} en 5s..."
                    )
                    time.sleep(5)

            # Salvaguarda: si se agotan los reintentos, conservar lo descargado hasta el momento
            if not exito_pagina:
                logging.error(
                    f"Se agotaron los {max_intentos} reintentos en la página {pagina_actual}. "
                    "Resguardando progreso acumulado para evitar pérdida de datos."
                )
                break

            pagina_actual += 1
            time.sleep(pausa_entre_paginas)

    return todos_los_datos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extractor masivo de directorios de servidores públicos (PNT)."
    )
    parser.add_argument("--entidad", type=str, default="Hidalgo", help="Nombre de la entidad a consultar.")
    parser.add_argument("--salida", type=str, default="data/PNT_Directorio_HGO.csv", help="Ruta del CSV de salida.")
    args = parser.parse_args()

    datos_finales = extraer_datos_pnt(entidad=args.entidad)

    if datos_finales:
        ruta_salida = Path(args.salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(datos_finales)
        df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
        logging.info(f"Proceso finalizado. Archivo '{ruta_salida}' generado con {len(df):,} filas.")
    else:
        logging.warning("No se recolectó información durante la ejecución.")


if __name__ == "__main__":
    main()