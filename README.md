# Simulador de Riesgo y EVM — Joyería Kristhal

**Universidad Galileo · IIO**
Postgrado en Investigación de Operaciones · Evaluación y Control de Proyectos
Ing. Gary Avendaño

---

## Descripción

Joyería Kristhal vende actualmente en local físico y redes sociales, sin tienda en línea. Este proyecto modela el lanzamiento de su sitio web con tienda integrada, con el objetivo de planificar, simular y evaluar el esfuerzo mediante:

- Ruta Crítica (CPM/PERT) con diagrama de red interactivo
- Simulación Monte Carlo (mínimo 1,000 simulaciones, 10,000 por defecto)
- Gestión del Valor Ganado (EVM) con curva S
- Dashboard ejecutivo con semáforo de decisión
- Índice de criticidad por actividad *(opcional)*

Aplicación desarrollada en **Python + Streamlit**.

---

## Instalación

### Requisitos
- Python 3.9+

### Pasos

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd kristhal-simulador-evm

# 2. Crear un entorno virtual
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
streamlit run app_kristhal.py
```

La aplicación abrirá automáticamente en `http://localhost:8501`

---

## Despliegue en Streamlit Community Cloud

1. Subir este repositorio a GitHub.
2. Entrar a [share.streamlit.io](https://share.streamlit.io) e iniciar sesión con GitHub.
3. Crear una nueva app seleccionando el repositorio, la rama `main` y el archivo principal `app_kristhal.py`.
4. Streamlit instalará automáticamente las dependencias de `requirements.txt` y publicará la app con una URL pública.

---

## Estructura del repositorio

```
kristhal-simulador-evm/
├── app_kristhal.py            # Aplicación principal (Streamlit)
├── requirements.txt           # Dependencias
├── README.md                  # Este archivo
├── .gitignore
└── data/                      # Datos del caso de ejemplo
    ├── actividades_kristhal.csv   # Actividades, predecesoras y estimaciones PERT
    ├── evm_periodos.csv           # Curvas acumuladas PV/EV/AC por periodo
    └── evm_por_actividad.csv      # BAC/EV/AC y avance por actividad al corte
```

La aplicación carga el caso de estudio desde los archivos en `data/`. Si esa carpeta no está disponible, usa valores de respaldo embebidos en el propio código, por lo que la app siempre puede ejecutarse con el caso de ejemplo tal como lo pide el enunciado.

---

## Caso de Estudio — Joyería Kristhal

| Act. | Actividad | Pred. | Dur. E (días) | Costo E (Q) |
|------|-----------|-------|---------------|-------------|
| A | Marca, identidad y catálogo | — | 10.50 | 15,667 |
| B | Sesión fotográfica y edición | A | 8.33 | 8,333 |
| C | Desarrollo del sitio e-commerce | A | 20.83 | 36,333 |
| D | Integración de pasarela de pagos | C | 6.50 | 6,333 |
| E | Carga de catálogo y contenido | B, C | 7.50 | 5,417 |
| F | Pruebas y seguridad | D, E | 8.50 | 7,500 |
| G | Lanzamiento de la tienda | F | 3.17 | 4,417 |

**Ruta crítica:** A → C → E → F → G = **50.5 días**
**BAC:** Q 84,000
**Corte de análisis:** Período 7 (Día 30)

### Riesgos principales

| # | Riesgo | Actividad | Decisión |
|---|--------|-----------|----------|
| 1 | Retrasos en el desarrollo del sitio por cambios de alcance/diseño | C (crítica) | Sprints cortos con revisión |
| 2 | Demoras en certificar la pasarela de pagos con el banco | D | Iniciar el trámite con mayor anticipación o buscar otra alternativa de banco |
| 3 | Fotografía que no cumple el estándar y obliga a repetir | B - E | Guía de requisitos y test de 3 fotos antes de la sesión |

---

## Flujo de la Aplicación

```
Datos del Proyecto → Ruta Crítica → Monte Carlo → EVM → Dashboard
```

1. **Definición del Proyecto** — Ver/editar actividades y estimaciones PERT
2. **Ruta Crítica** — CPM con tabla de holguras y diagrama de red
3. **Monte Carlo** — Histogramas, percentiles P50/P80 y probabilidades
4. **EVM y Pronósticos** — Indicadores, curva S e interpretación
5. **Dashboard** — Panel ejecutivo con gauges y semáforo de decisión

---

## Resultados al Corte (Período 7)

| Indicador | Valor | Interpretación |
|-----------|-------|----------------|
| PV | Q 58,013 | Valor planificado a la fecha de corte |
| EV | Q 54,513 | Valor ganado (65% de avance físico) |
| AC | Q 62,500 | Costo real incurrido |
| SV | −Q 3,500 | Retraso leve en cronograma |
| CV | −Q 7,987 | Sobrecosto |
| SPI | 0.94 | Avanza al 94% del ritmo planificado |
| CPI | 0.87 | Q 0.87 de valor generado por cada quetzal gastado |
| EAC | Q 96,307 | Costo final proyectado |
| ETC | Q 33,807 | Costo restante estimado |
| VAC | −Q 12,307 | Sobrecosto previsto al cierre |

Los valores fueron verificados contra la plantilla EVM del curso (`EVM_Proyecto.xlsx`) y coinciden con el caso de prueba.

---

## Pruebas realizadas

- Verificación de la duración total y de la ruta crítica (A-C-E-F-G, 50.5 días) contra el cálculo manual del informe.
- Verificación de los indicadores EVM (SV, CV, SPI, CPI, EAC, ETC, VAC) contra la plantilla EVM del curso, con resultados coincidentes.
- Ejecución de la app en modo headless para confirmar que carga sin errores con el caso de ejemplo por defecto.
