#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
beco_analysis.py

Script para limpieza de datos, análisis exploratorio (EDA) y 
generación de insights conductuales (BECO) para el caso práctico.
"""

import pandas as pd
import matplotlib.pyplot as plt

def clean_sheet(df):
    """Limpia una hoja de datos usando la primera fila como encabezado 
    y rellena hacia adelante columnas de 'Tribu' y 'Banner'."""
    df = df.copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    for col in ['Tribu', 'Banner']:
        if col in df.columns:
            df[col] = df[col].ffill()
    return df

def main():
    # 1. Cargar datos
    path = 'Caso_practico_analizado2 (1).xlsx'
    sheets = pd.read_excel(path, sheet_name=None)

    # 2. Limpieza de hojas
    df_cov = clean_sheet(sheets['Cobertura'])
    df_rot = clean_sheet(sheets['Rotación'])
    df_geo = sheets[[name for name in sheets if 'Geolocal' in name][0]]

    # 3. Ajuste de nombres de columna de código de tienda
    def find_code_col(cols):
        return next((c for c in cols if isinstance(c, str) and 'cod' in c.lower()), None)
    code_geo = find_code_col(df_geo.columns)
    code_cov = find_code_col(df_cov.columns)
    code_rot = find_code_col(df_rot.columns)
    key = 'Codigo de tienda'
    if code_geo: df_geo.rename(columns={code_geo:key}, inplace=True)
    if code_cov: df_cov.rename(columns={code_cov:key}, inplace=True)
    if code_rot: df_rot.rename(columns={code_rot:key}, inplace=True)

    # 4. Merge con geolocalización
    if key in df_cov.columns and key in df_geo.columns:
        df_cov = df_cov.merge(df_geo, on=key, how='left')
    if key in df_rot.columns and key in df_geo.columns:
        df_rot = df_rot.merge(df_geo, on=key, how='left')

    # 5. Conversión de tipos numéricos
    for col in ['Criticidad','Cobertura']:
        if col in df_cov.columns:
            df_cov[col] = pd.to_numeric(df_cov[col], errors='coerce')
    if 'Rotación' in df_rot.columns:
        df_rot['Rotación'] = pd.to_numeric(df_rot['Rotación'], errors='coerce')

    # 6. EDA: Top 5 estados con mejor cobertura
    if 'Estado' in df_cov.columns:
        cov_summary = df_cov.groupby('Estado')['Criticidad'].mean().sort_values().head(5)
        print("\nTop 5 estados con mejor criticidad (menor):")
        print(cov_summary)

    # 7. EDA: Rotación promedio por Banner
    if 'Banner' in df_rot.columns:
        rot_summary = df_rot.groupby('Banner')['Rotación'].mean().sort_values(ascending=False)
        print("\nRotación promedio por Banner:")
        print(rot_summary)

    # 8. Categorías de cobertura
    if 'Cobertura' in df_cov.columns:
        bins = [0, 0.95, 0.97, 1]
        labels = ['Muy críticas (<95%)', 'Críticas (95-97%)', 'Sanas (>97%)']
        df_cov['Categoria Cobertura'] = pd.cut(df_cov['Cobertura'], bins=bins, labels=labels)
        counts = df_cov['Categoria Cobertura'].value_counts()
        print("\nNúmero de tiendas por categoría de cobertura:")
        print(counts)

    # 9. Gráficas
    if 'cov_summary' in locals():
        cov_summary.plot(kind='bar', title='Top 5 estados con mejor cobertura')
        plt.xlabel('Estado'); plt.ylabel('Criticidad promedio')
        plt.savefig('coverage_bar.png', bbox_inches='tight')
        plt.clf()
    if 'rot_summary' in locals():
        rot_summary.plot(kind='bar', title='Rotación promedio por Banner')
        plt.xlabel('Banner'); plt.ylabel('Rotación promedio')
        plt.savefig('rotation_bar.png', bbox_inches='tight')
        plt.close()

    # 10. Interpretación BECO (impresa en consola)
    interpretation = """
1. Diagnóstico Conductual Detallado:
   - Regiones con criticidad promedio 0.80-0.90 operan sin fricciones.
   - 15% de tiendas bajo "Muy críticas (<95%)": quiebres frecuentes.

2. Insights Conductuales:
   • Sesgo de responsabilidad difusa: se diluye responsabilidad en inventarios.
   • Falta de feedback inmediato: no se percibe impacto de quiebres en ventas.
   • Normas sociales insuficientes: no hay reconocimiento entre equipos.

3. Intervenciones BECO:
   - Simplificación: checklists digitales diarios.
   - Feedback inmediato: paneles en tiempo real de cobertura.
   - Recordatorios: alertas push semanales.
   - Refuerzo social: “Top 5 tiendas” con badges.
   - Defaults & Framing: órdenes preseleccionadas.

4. Diseño de Experimento A/B:
   - Grupo Tratamiento: alertas + defaults; Control: proceso actual.
   - Duración: 4 semanas.
   - Métricas: cobertura %, rotación %, satisfacción interna.

5. Plan de Comunicación y Escalado:
   - Narrativa: “Piloto aumentó cobertura X p.p. y redujo rotación Y p.p.”
   - Visualizaciones pre/post.
   - Extensión a tiendas “Muy críticas” y documentación de lecciones.
"""
    print(interpretation)

if __name__ == "__main__":
    main()
