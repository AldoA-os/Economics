"""
Módulo de Limpieza Textual, Estandarización y Clasificación Heurística de PEPs
(Personas Políticamente Expuestas) a partir de Directorios de la PNT.
Autor: Aldo Uriel Álvarez Vargas
"""

import re
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# Configuración de bitácora de ejecución
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Diccionario de palabras clave para clasificar Sujetos Obligados por Poder de Estado
PODER_KEYWORDS: Dict[str, List[str]] = {
    "Legislativo": ["congreso", "auditoría superior", "auditoria superior"],
    "Judicial": ["tribunal superior", "judicatura"],
    "Autónomos": [
        "fiscalía", "fiscalia", "derechos humanos", "transparencia",
        "electoral", "tribunal de justicia administrativa", "universidad autónoma"
    ]
}

# Catálogos metodológicos para identificación de Personas Políticamente Expuestas (PEPs)
INCLUSION_ESTRATEGICA: List[str] = [
    "secretario", "secretaria de", "subsecretario", "director general", "directora general",
    "fiscal", "magistrado", "juez", "diputado", "auditor superior", "comisionado", "procurador",
    "alcalde", "presidente municipal", "síndico", "sindico", "regidor", "tesorero", "contralor",
    "titular del organo interno", "titular del órgano interno", "consejero"
]

INCLUSION_FINANCIERA: List[str] = [
    "finanzas", "presupuesto", "adquisiciones", "recursos humanos", "recursos materiales",
    "administración", "administracion", "compras", "licitaciones", "juridico", "jurídico",
    "tesoreria", "patrimonio"
]

EXCLUSION_OPERATIVA: List[str] = [
    "asistente", "enlace", "auxiliar", "soporte", "operativo", "chofer", "recepcionista",
    "intendente", "mensajero", "capturista", "archivista", "instructor", "mecanico", "conductor",
    "policía", "policia", "guardia", "custodio", "paramédico", "bombero", "comandante",
    "monitorista", "jefe de sector", "técnico", "tecnico", "mantenimiento", "inspector",
    "notificador", "actuario", "proyectista", "perito", "psicologo", "psicologa", "terapeuta",
    "trabajadora social", "enfermera", "medico", "médico", "orientador",
    "secretaria mecanografa", "secretaria mecanógrafa", "secretaria b", "secretaria de departamento",
    "secretaria de director", "secretaria ejecutiva", "secretaria tecnica", "secretaria técnica",
    "secretario tecnico", "secretario técnico", "secretario de primera instancia", "secretario de sala",
    "secretario menor", "secretario lider", "secretario líder", "secretario mecanografo",
    "secretario de juzgado", "secretario de ponente", "secretario proyectista", "secretaria de estudio",
    "secretario de estudio", "secretario de tribunal", "secretario auxiliar", "secretario instructor",
    "secretario de la presidencia", "secretario particular", "secretaria particular", "agente del ministerio"
]

# Preposiciones y conectores que deben permanecer en minúscula en formato Título
CONECTORES_MINUSCULAS = {
    "de", "la", "las", "los", "del", "al", "en", "con", "sin", "por", "para",
    "y", "o", "u", "e", "ni", "que", "como", "más", "menos", "ante", "bajo",
    "cabe", "contra", "desde", "durante", "entre", "hacia", "hasta", "mediante",
    "según", "sobre", "tras", "vs", "vía"
}


def formatear_titulo(texto: str) -> str:
    """
    Normaliza nombres y cargos a formato Título gramatical en español,
    preservando siglas institucionales (ej. INE, IMSS), apellidos compuestos
    (ej. McDonald, Macías) y conectores en minúscula.
    """
    if pd.isna(texto) or not str(texto).strip():
        return ""

    palabras = str(texto).strip().split()
    nuevas: List[str] = []

    for i, palabra in enumerate(palabras):
        p_limpia = palabra.strip(".,;:!?()[]{}\"'")
        if not p_limpia:
            nuevas.append(palabra)
            continue

        if i == 0:
            nuevas.append(p_limpia.capitalize())
        elif p_limpia.isupper() and len(p_limpia) >= 2:
            nuevas.append(p_limpia)
        elif re.match(r"^(Mc|Mac)[A-Z]", p_limpia, re.IGNORECASE):
            nuevas.append(p_limpia)
        elif p_limpia.lower() in CONECTORES_MINUSCULAS:
            nuevas.append(p_limpia.lower())
        else:
            nuevas.append(p_limpia.capitalize())

    return " ".join(nuevas)


def detectar_prefijo_estatal(df: pd.DataFrame, columna: str) -> str:
    """Detecta automáticamente prefijos de entidad federativa (ej. 'TLA - ', 'TAM - ')."""
    muestras = df[columna].dropna().astype(str).head(100)
    patron = re.compile(r"^[A-Z]{2,4}\s*-\s*")
    for val in muestras:
        match = patron.match(val)
        if match:
            return match.group(0)
    return ""


def cargar_municipios(ruta_archivo: Path) -> List[str]:
    """Carga el catálogo oficial de municipios desde un archivo CSV."""
    if not ruta_archivo.exists():
        logging.warning(f"Catálogo de municipios no encontrado en '{ruta_archivo}'.")
        return []
    try:
        df_muni = pd.read_csv(ruta_archivo)
        if "Municipio" not in df_muni.columns:
            logging.error("El archivo de municipios debe contener la columna 'Municipio'.")
            return []
        return df_muni["Municipio"].dropna().astype(str).str.strip().unique().tolist()
    except Exception as exc:
        logging.error(f"Error al cargar catálogo de municipios: {exc}")
        return []


def clasificar_municipio(entidad: str, lista_municipios: List[str]) -> Optional[str]:
    """Verifica si una institución corresponde a un gobierno municipal."""
    entidad_limpia = entidad.strip()
    if entidad_limpia in lista_municipios:
        return entidad_limpia

    patrones_municipales = [
        r"^(?:Ayuntamiento|Municipio|H\.?\s*Ayuntamiento)\s+(?:de\s+)?(.+)$",
        r"^(?:Gobierno\s+)?Municipal\s+(?:de\s+)?(.+)$"
    ]
    for pat in patrones_municipales:
        match = re.search(pat, entidad_limpia, re.IGNORECASE)
        if match:
            posible_municipio = match.group(1).strip()
            if posible_municipio in lista_municipios:
                return posible_municipio
    return None


def construir_clasificador_pep():
    """
    Clausura que precompila las expresiones regulares con límites de palabra (\\b)
    y retorna la función evaluadora de cargos PEP de alta velocidad.
    """
    pat_excl = [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in EXCLUSION_OPERATIVA]
    pat_est = [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in INCLUSION_ESTRATEGICA]
    pat_fin = [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in INCLUSION_FINANCIERA]
    pat_jerarquia = re.compile(r"\b(director|directora|subdirector|subdirectora|coordinador|coordinadora|jefe|jefa|titular)\b", re.IGNORECASE)

    def evaluar_cargo(cargo: str) -> bool:
        if not isinstance(cargo, str) or not cargo.strip():
            return False
        c_low = cargo.lower().strip()

        # 1. Filtro de Exclusión Operativa (con excepciones de alta dirección)
        if any(pat.search(c_low) for pat in pat_excl):
            if any(ex in c_low for ex in ("secretario de seguridad", "secretaria de seguridad", "secretaria de administracion")):
                return True
            if "secretario general de acuerdos" in c_low and "juzgado" not in c_low:
                return True
            return False

        # 2. Inclusión Estratégica (Titulares y altos mandos de los tres poderes)
        if any(pat.search(c_low) for pat in pat_est):
            if c_low in ("secretaria", "secretario"):
                return False
            return True

        # 3. Inclusión Financiera / Administrativa (Regla de doble validación: área + nivel jerárquico)
        if any(pat.search(c_low) for pat in pat_fin):
            if pat_jerarquia.search(c_low):
                return True

        return False

    return evaluar_cargo


def procesar_peps(ruta_csv: Path, ruta_municipios: Path, carpeta_salida: Optional[Path] = None) -> None:
    """Ejecuta el flujo completo de limpieza, discernimiento PEP y particionamiento en Excel."""
    logging.info("=== INICIO DEL PIPELINE DE CLASIFICACIÓN PEP ===")

    if not ruta_csv.exists():
        logging.error(f"Archivo de entrada no encontrado: {ruta_csv}")
        return

    lista_municipios = cargar_municipios(ruta_municipios)
    logging.info(f"Municipios de referencia cargados: {len(lista_municipios)}")

    # Lectura con fallback automático de codificación (UTF-8 -> Latin-1)
    try:
        df = pd.read_csv(ruta_csv, encoding="utf-8")
    except UnicodeDecodeError:
        logging.info("Codificación UTF-8 no compatible; aplicando fallback a latin1...")
        df = pd.read_csv(ruta_csv, encoding="latin1")

    logging.info(f"Total de registros brutos cargados: {len(df):,}")

    # Validación de esquema de datos de entrada
    columnas_requeridas = ["Sujeto Obligado / Institución", "Cargo / Denominación", "Nombre Completo"]
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        logging.error(f"Faltan columnas requeridas en el CSV: {faltantes}")
        return

    # Limpieza y homologación de columnas
    if "Entidad" in df.columns:
        df = df.drop(columns=["Entidad"])

    df.rename(columns={
        "Sujeto Obligado / Institución": "Entidad",
        "Cargo / Denominación": "Cargo",
        "Nombre Completo": "Nombre de la Persona"
    }, inplace=True)

    # Eliminación dinámica de prefijo estatal
    prefijo = detectar_prefijo_estatal(df, "Entidad")
    if prefijo:
        df["Entidad"] = df["Entidad"].astype(str).str.replace(prefijo, "", regex=False).str.strip()
        logging.info(f"Prefijo institucional eliminado: '{prefijo}'")

    # Normalización gramatical de nombres y cargos
    logging.info("Normalizando nombres propios y denominaciones de cargos...")
    df["Nombre de la Persona"] = df["Nombre de la Persona"].astype(str).apply(formatear_titulo)
    df["Cargo"] = df["Cargo"].astype(str).apply(formatear_titulo)
    df["Cargo_lower"] = df["Cargo"].str.lower().str.strip()

    # Ejecución del motor de discernimiento PEP
    logging.info("Ejecutando motor heurístico de discernimiento PEP...")
    evaluar_pep = construir_clasificador_pep()
    df["Es_PEP"] = df["Cargo_lower"].apply(evaluar_pep)
    pep_df = df[df["Es_PEP"]].copy()
    logging.info(f"Total de PEPs identificados: {len(pep_df):,} ({len(pep_df)/len(df)*100:.2f}% del padrón)")

    # Clasificación por Poder del Estado y Ayuntamiento
    def clasificar_ente(row: pd.Series) -> str:
        entidad = str(row["Entidad"])
        entidad_lower = entidad.lower()

        if lista_municipios:
            mun = clasificar_municipio(entidad, lista_municipios)
            if mun:
                return f"Municipio_{mun}"

        for poder, keywords in PODER_KEYWORDS.items():
            if any(kw in entidad_lower for kw in keywords):
                return poder

        return "Ejecutivo"

    logging.info("Segmentando registros por Poder de Estado y Municipio...")
    pep_df["Categoria"] = pep_df.apply(clasificar_ente, axis=1)

    # Exportación particionada a archivos Excel (.xlsx)
    directorio_destino = carpeta_salida or (ruta_csv.parent / "Resultados_PEPs")
    directorio_destino.mkdir(parents=True, exist_ok=True)
    columnas_finales = ["Entidad", "Cargo", "Nombre de la Persona"]

    for categoria, grupo_df in pep_df.groupby("Categoria"):
        df_exportar = grupo_df[columnas_finales]
        if not df_exportar.empty:
            nombre_seguro = f"{categoria}.xlsx".replace(" ", "_").replace("/", "-")
            ruta_excel = directorio_destino / nombre_seguro
            df_exportar.to_excel(ruta_excel, index=False)
            logging.info(f" -> Guardado: {nombre_seguro} ({len(df_exportar):,} PEPs)")

    logging.info(f"=== PROCESO FINALIZADO. Archivos exportados en: '{directorio_destino}' ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpieza y clasificación de PEPs desde directorios PNT.")
    parser.add_argument("--csv", type=str, required=True, help="Ruta al archivo CSV descargado de la PNT.")
    parser.add_argument("--municipios", type=str, required=True, help="Ruta al catálogo CSV/TXT de municipios.")
    parser.add_argument("--salida", type=str, default=None, help="Carpeta de salida para los archivos Excel.")
    args = parser.parse_args()

    procesar_peps(
        ruta_csv=Path(args.csv),
        ruta_municipios=Path(args.municipios),
        carpeta_salida=Path(args.salida) if args.salida else None
    )


if __name__ == "__main__":
    main()