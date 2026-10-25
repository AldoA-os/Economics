"""
Módulo de Análisis Estadístico, Auditoría de Calidad de Datos y Visualización Ejecutiva
para Padrones de Personas Políticamente Expuestas (PEPs).
Autor: Aldo Uriel Álvarez Vargas
"""

import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de bitácora de auditoría
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuración estética global para gráficos ejecutivos
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#CCCCCC"
plt.rcParams["axes.linewidth"] = 0.8


def consolidar_archivos_peps(carpeta_resultados: Path) -> pd.DataFrame:
    """
    Lee todos los archivos Excel (.xlsx) generados en la etapa de limpieza
    y reconstruye un DataFrame maestro para el análisis estadístico.
    """
    archivos_excel = list(carpeta_resultados.glob("*.xlsx"))
    if not archivos_excel:
        raise FileNotFoundError(
            f"No se encontraron archivos .xlsx en '{carpeta_resultados}'."
        )

    lista_dfs = []
    for archivo in archivos_excel:
        categoria = archivo.stem  # Nombre del archivo sin extensión
        df_temp = pd.read_excel(archivo)
        df_temp["Categoria_Archivo"] = categoria
        df_temp["Es_Municipio"] = categoria.startswith("Municipio_")
        df_temp["Macro_Sector"] = np.where(
            df_temp["Es_Municipio"],
            "Ayuntamientos (Total Municipal)",
            categoria.replace("_", " ")
        )
        lista_dfs.append(df_temp)

    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    logging.info(
        f"Consolidación exitosa: {len(df_consolidado):,} PEPs integrados "
        f"desde {len(archivos_excel)} archivos."
    )
    return df_consolidado


def calcular_gini(valores: np.ndarray) -> float:
    """
    Calcula el Coeficiente de Gini (0 = equidad perfecta, 1 = concentración total)
    sobre la distribución de PEPs por unidad administrativa.
    """
    arr = np.asarray(valores, dtype=np.float64)
    arr = arr[arr >= 0]
    if arr.size == 0 or np.sum(arr) == 0:
        return 0.0
    arr_sorted = np.sort(arr)
    n = arr_sorted.size
    indices = np.arange(1, n + 1)
    return float((np.sum((2 * indices - n - 1) * arr_sorted)) / (n * np.sum(arr_sorted)))


def calcular_ihh(valores: np.ndarray) -> float:
    """
    Calcula el Índice de Herfindahl-Hirschman (IHH) en escala de 0 a 10,000
    para evaluar el grado de concentración institucional de los PEPs.
    """
    arr = np.asarray(valores, dtype=np.float64)
    total = np.sum(arr)
    if total == 0:
        return 0.0
    participaciones = (arr / total) * 100.0
    return float(np.sum(participaciones ** 2))


def analizar_distribucion_municipal(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ejecuta pruebas estadísticas descriptivas, paramétricas, no paramétricas
    y detección de valores atípicos (outliers) sobre el padrón municipal.
    """
    df_muni = df[df["Es_Municipio"]].copy()
    if df_muni.empty:
        return pd.DataFrame(), {}

    # Conteo de PEPs por Municipio
    conteo_muni = (
        df_muni.groupby("Categoria_Archivo")
        .size()
        .reset_index(name="Total_PEPs")
    )
    conteo_muni["Municipio"] = (
        conteo_muni["Categoria_Archivo"]
        .str.replace("Municipio_", "", regex=False)
        .str.replace("_", " ", regex=False)
    )
    conteo_muni = conteo_muni.sort_values("Total_PEPs", ascending=False).reset_index(drop=True)

    serie = conteo_muni["Total_PEPs"]
    media = float(serie.mean())
    desv_est = float(serie.std(ddof=1)) if len(serie) > 1 else 0.0
    mediana = float(serie.median())
    q1 = float(serie.quantile(0.25))
    q3 = float(serie.quantile(0.75))
    iqr = q3 - q1

    # Detección estadística de anomalías (Z-Score y Regla de Tukey IQR)
    conteo_muni["Z_Score"] = (serie - media) / desv_est if desv_est > 0 else 0.0
    limite_sup_iqr = q3 + 1.5 * iqr
    limite_inf_iqr = max(0.0, q1 - 1.5 * iqr)

    conteo_muni["Diagnostico_Calidad"] = "Rango Normal"
    conteo_muni.loc[conteo_muni["Total_PEPs"] > limite_sup_iqr, "Diagnostico_Calidad"] = "Alta Concentración (Outlier Superior)"
    conteo_muni.loc[conteo_muni["Total_PEPs"] <= np.percentile(serie, 10), "Diagnostico_Calidad"] = "Alerta Posible Subreporte (Decil Inferior)"

    metricas = {
        "Num_Municipios": len(conteo_muni),
        "Total_PEPs_Municipales": int(serie.sum()),
        "Media_PEPs": round(media, 2),
        "Desviacion_Estandar": round(desv_est, 2),
        "Coeficiente_Variacion_Pct": round((desv_est / media) * 100, 2) if media > 0 else 0.0,
        "Mediana_PEPs": round(mediana, 2),
        "Rango_Intercuartilico_IQR": round(iqr, 2),
        "Asimetria_Skewness": round(float(serie.skew()), 3) if len(serie) > 2 else 0.0,
        "Curtosis": round(float(serie.kurtosis()), 3) if len(serie) > 3 else 0.0,
        "Coeficiente_Gini_Municipal": round(calcular_gini(serie.values), 4),
        "IHH_Municipal": round(calcular_ihh(serie.values), 2),
        "Limite_Superior_IQR": round(limite_sup_iqr, 2),
        "Limite_Inferior_IQR": round(limite_inf_iqr, 2)
    }

    return conteo_muni, metricas


def generar_dashboard_ejecutivo(
    df: pd.DataFrame,
    conteo_muni: pd.DataFrame,
    metricas: Dict[str, Any],
    ruta_imagen: Path
) -> None:
    """
    Construye y exporta un tablero visual de 4 paneles diseñado para presentaciones
    ejecutivas y toma de decisiones.
    """
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.suptitle(
        "Tablero Ejecutivo: Análisis Estadístico y Concentración de PEPs (Datos PNT)",
        fontsize=18, fontweight="bold", y=0.98, color="#1A252C"
    )

    # --- PANEL 1: Distribución por Macro-Sector (Poder de Estado vs. Municipios) ---
    ax1 = axes[0, 0]
    resumen_sector = (
        df["Macro_Sector"]
        .value_counts()
        .reset_index()
    )
    resumen_sector.columns = ["Sector", "Total"]
    resumen_sector["Porcentaje"] = (resumen_sector["Total"] / len(df)) * 100

    sns.barplot(
        data=resumen_sector, x="Total", y="Sector", ax=ax1,
        palette="Blues_r", edgecolor="none"
    )
    ax1.set_title("1. Distribución de PEPs por Poder de Estado y Nivel Municipal", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Número de Servidores Públicos (PEPs)")
    ax1.set_ylabel("")
    for i, row in resumen_sector.iterrows():
        ax1.text(
            row["Total"] + (resumen_sector["Total"].max() * 0.01), i,
            f"{row['Total']:,} ({row['Porcentaje']:.1f}%)",
            va="center", fontsize=10, fontweight="bold", color="#2C3E50"
        )
    ax1.set_xlim(0, resumen_sector["Total"].max() * 1.18)

    # --- PANEL 2: Top 15 Municipios con Mayor Concentración de PEPs ---
    ax2 = axes[0, 1]
    if not conteo_muni.empty:
        top_muni = conteo_muni.head(15)
        sns.barplot(
            data=top_muni, x="Total_PEPs", y="Municipio", ax=ax2,
            palette="viridis", edgecolor="none"
        )
        ax2.axvline(
            metricas["Media_PEPs"], color="#E74C3C", linestyle="--", linewidth=1.8,
            label=f"Media Municipal ({metricas['Media_PEPs']:.1f})"
        )
        ax2.set_title("2. Top 15 Municipios por Volumen de PEPs Identificados", fontsize=13, fontweight="bold")
        ax2.set_xlabel("PEPs Identificados")
        ax2.set_ylabel("")
        ax2.legend(loc="lower right", frameon=True)

    # --- PANEL 3: Distribución Estadística, Densidad Kernel (KDE) y Umbrales ---
    ax3 = axes[1, 0]
    if not conteo_muni.empty:
        sns.histplot(
            conteo_muni["Total_PEPs"], kde=True, ax=ax3,
            color="#2980B9", bins=12, edgecolor="white", alpha=0.6
        )
        ax3.axvline(
            metricas["Media_PEPs"], color="#E74C3C", linestyle="--", linewidth=2,
            label=f"Media: {metricas['Media_PEPs']}"
        )
        ax3.axvline(
            metricas["Mediana_PEPs"], color="#27AE60", linestyle="-", linewidth=2,
            label=f"Mediana: {metricas['Mediana_PEPs']}"
        )
        ax3.axvline(
            metricas["Limite_Superior_IQR"], color="#8E44AD", linestyle=":", linewidth=2,
            label=f"Umbral Outlier IQR: {metricas['Limite_Superior_IQR']}"
        )
        texto_caja = (
            f"Estadísticos Municipales (n={metricas['Num_Municipios']}):\n"
            f"• Desv. Estándar: {metricas['Desviacion_Estandar']}\n"
            f"• Coef. Variación: {metricas['Coeficiente_Variacion_Pct']}%\n"
            f"• Asimetría (Skew): {metricas['Asimetria_Skewness']}\n"
            f"• Coef. Gini: {metricas['Coeficiente_Gini_Municipal']}\n"
            f"• Índice IHH: {metricas['IHH_Municipal']}"
        )
        ax3.text(
            0.97, 0.55, texto_caja, transform=ax3.transAxes, fontsize=9.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F8F9F9", edgecolor="#BDC3C7")
        )
        ax3.set_title("3. Distribución de Frecuencias y Auditoría de Dispersión Municipal", fontsize=13, fontweight="bold")
        ax3.set_xlabel("Número de PEPs por Municipio")
        ax3.set_ylabel("Frecuencia (Número de Municipios)")
        ax3.legend(loc="upper right", frameon=True)

    # --- PANEL 4: Top 10 Denominaciones de Cargos Estratégicos ---
    ax4 = axes[1, 1]
    top_cargos = (
        df["Cargo"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_cargos.columns = ["Cargo", "Frecuencia"]
    sns.barplot(
        data=top_cargos, x="Frecuencia", y="Cargo", ax=ax4,
        palette="magma", edgecolor="none"
    )
    ax4.set_title("4. Top 10 Denominaciones de Cargos PEP más Frecuentes", fontsize=13, fontweight="bold")
    ax4.set_xlabel("Frecuencia Absoluta")
    ax4.set_ylabel("")

    plt.tight_layout(rect=[0, 0.01, 1, 0.95])
    fig.savefig(ruta_imagen, dpi=300)
    plt.close(fig)
    logging.info(f"Tablero visual de alta resolución exportado en: '{ruta_imagen}'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Análisis estadístico y visualización ejecutiva de resultados PEP."
    )
    parser.add_argument(
        "--carpeta", type=str, required=True,
        help="Ruta a la carpeta 'Resultados_PEPs' generada por el módulo 02."
    )
    args = parser.parse_args()

    carpeta_resultados = Path(args.carpeta)
    carpeta_reportes = carpeta_resultados / "Reportes_Estadisticos"
    carpeta_reportes.mkdir(parents=True, exist_ok=True)

    # 1. Consolidar fuentes
    df_maestro = consolidar_archivos_peps(carpeta_resultados)

    # 2. Ejecutar modelo estadístico de concentración y calidad de datos
    df_muni_stats, metricas = analizar_distribucion_municipal(df_maestro)

    if metricas:
        logging.info("=== RESUMEN ESTADÍSTICO MUNICIPAL ===")
        for clave, valor in metricas.items():
            logging.info(f" -> {clave}: {valor}")

        # Exportar diagnósticos municipales y resumen de métricas a CSV
        ruta_diagnostico = carpeta_reportes / "Auditoria_Estadistica_Municipios.csv"
        df_muni_stats.to_csv(ruta_diagnostico, index=False, encoding="utf-8-sig")

        ruta_metricas = carpeta_reportes / "Metricas_Concentracion_Global.csv"
        pd.DataFrame([metricas]).to_csv(ruta_metricas, index=False, encoding="utf-8-sig")
        logging.info(f"Tablas estadísticas guardadas en: '{carpeta_reportes}'")

    # 3. Generar visualización ejecutiva
    ruta_dashboard = carpeta_reportes / "Dashboard_Ejecutivo_PEPs.png"
    generar_dashboard_ejecutivo(df_maestro, df_muni_stats, metricas, ruta_dashboard)


if __name__ == "__main__":
    main()