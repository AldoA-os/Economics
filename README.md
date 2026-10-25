# Pipeline de Extracción Masiva y Clasificación de PEPs (Plataforma Nacional de Transparencia)

Este proyecto implementa un flujo de trabajo de **Ingeniería de Datos y Clasificación Heurística de Texto (RegTech / Prevención de Lavado de Dinero)** diseñado para construir padrones auditables de **Personas Políticamente Expuestas (PEPs)** a nivel estatal y municipal en México utilizando datos abiertos de la **Plataforma Nacional de Transparencia (PNT)**.

## Problema de Negocio y Objetivo
Las instituciones financieras y áreas de cumplimiento normativo (*Compliance* / PLD) requieren identificar con precisión qué servidores públicos ocupan cargos de alta dirección, toma de decisiones o manejo de recursos públicos (PEPs), separándolos del personal puramente operativo o administrativo dentro de padrones gubernamentales que superan los **80,000 a 240,000 registros por entidad federativa**.

Este repositorio resuelve el problema en dos etapas automatizadas:
1. **Ingesta Masiva Tolerante a Fallos (`01_extraccion_pnt_api.py`):** Consumo directo del endpoint REST/Solr del Buscador Temático de la PNT mediante sesiones HTTP persistentes (`requests.Session`), control de *rate-limiting* y reconexión automática ante caídas del servidor (errores HTTP 5xx / cortes de socket), permitiendo extraer cientos de miles de registros estructurados.
2. **Limpieza Gramatical y Motor de Discernimiento PEP (`02_limpieza_clasificacion_peps.py`):** Estandarización de texto, remoción dinámica de prefijos institucionales, clasificación de cargos mediante expresiones regulares precompiladas de alta velocidad y segmentación automatizada en archivos ejecutivos `.xlsx` divididos por **Poder de Estado (Ejecutivo, Legislativo, Judicial, Órganos Autónomos)** y **Ayuntamientos**.
3. **Análisis Estadístico, Auditoría de Calidad y Visualización Ejecutiva (`03_analisis_estadistico_visualizacion.py`):** Consolidación de los padrones clasificados para estimar métricas de dispersión paramétricas y no paramétricas (Media, Mediana, CV, IQR, Asimetría, Curtosis), índices de concentración institucional (**Coeficiente de Gini** e **Índice de Herfindahl-Hirschman - IHH**), detección automatizada de anomalías/subreportes mediante criterio de Tukey ($IQR$) y $Z\text{-Score}$, y generación de un tablero ejecutivo multipanel a 300 DPI (`Dashboard_Ejecutivo_PEPs.png`).
   
## Metodología del Motor de Discernimiento PEP
El clasificador evalúa cada denominación de puesto bajo un árbol de decisión de tres capas con límites de palabra (`\b`):
* **Capa 1 — Exclusión Operativa con Excepciones de Alto Mando:** Filtra puestos operativos, técnicos, médicos, de seguridad básica y secretariado auxiliar/mecanográfico o de juzgado menor, preservando explícitamente titulares estratégicos (ej. *Secretario de Seguridad*, *Secretaria de Administración*, *Secretario General de Acuerdos* de tribunal superior).
* **Capa 2 — Inclusión Estratégica Directa:** Identifica titulares y mandos superiores de los tres poderes y órdenes de gobierno (Secretarios de Estado, Subsecretarios, Directores Generales, Magistrados, Jueces, Diputados, Alcaldes, Síndicos, Regidores, Tesoreros, Contralores y Titulares de OIC).
* **Capa 3 — Inclusión Financiera y Patrimonial (Regla de Doble Validación):** Captura servidores públicos adscritos a áreas críticas (*Finanzas, Presupuesto, Adquisiciones, Licitaciones, Compras, Recursos Humanos/Materiales, Jurídico y Patrimonio*) **únicamente** cuando ostentan un nivel jerárquico de mando (*Director, Subdirector, Coordinador, Jefe o Titular*).


