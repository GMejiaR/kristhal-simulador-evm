import os
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx

st.set_page_config(page_title="Simulador EVM - Kristhal", layout="wide")

# ---------------------------------------------------------------------------
# Rutas de datos del caso de estudio
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

RUTA_ACTIVIDADES = os.path.join(DATA_DIR, "actividades_kristhal.csv")
RUTA_EVM_PERIODOS = os.path.join(DATA_DIR, "evm_periodos.csv")
RUTA_EVM_ACTIVIDAD = os.path.join(DATA_DIR, "evm_por_actividad.csv")

# Valores de respaldo (se usan solo si los archivos de datos no estan disponibles,
# por ejemplo en un despliegue donde no se incluyo la carpeta data/)
_actividades_respaldo = pd.DataFrame({
    "ID":          ["A","B","C","D","E","F","G"],
    "Actividad":   [
        "Marca, identidad y catalogo",
        "Sesion fotografica y edicion",
        "Desarrollo del sitio e-commerce",
        "Integracion de pasarela de pagos",
        "Carga de catalogo y contenido",
        "Pruebas y seguridad",
        "Lanzamiento de la tienda"
    ],
    "Predecesoras":["","A","A","C","B,C","D,E","F"],
    "d_opt": [7, 5,15, 4, 4, 5,2],
    "d_mp":  [10,8,20, 6, 7, 8,3],
    "d_pes": [16,13,30,11,13,14,5],
    "c_opt": [12000, 6000,28000, 4000,3500, 5000,2500],
    "c_mp":  [15000, 8000,35000, 6000,5000, 7000,4000],
    "c_pes": [22000,12000,50000,10000,9000,12000,8000],
})

_pv_acum_respaldo  = [6395,12789,22136,33899,43062,50538,58013,65348,71896,75636,79418,84000]
_ev_acum_respaldo  = [6395,12789,21539,32214,40290,46679,54513]
_ac_acum_respaldo  = [6939,13878,23253,34621,43495,50747,62500]

_act_evm_respaldo = [
    ("A - Marca y catalogo",       15667, 15667, 17000, 1.00),
    ("B - Fotografia y edicion",    8333,  8333,  8000, 1.00),
    ("C - Sitio e-commerce",       36333, 29067, 33000, 0.80),
    ("D - Pasarela de pagos",       6333,    633,  2500, 0.10),
    ("E - Carga de contenido",      5417,    813,  2000, 0.15),
    ("F - Pruebas y seguridad",     7500,      0,     0, 0.00),
    ("G - Lanzamiento",             4417,      0,     0, 0.00),
]


def cargar_actividades():
    """Carga el caso de estudio desde data/actividades_kristhal.csv.
    Si el archivo no existe, usa los valores de respaldo embebidos."""
    if os.path.exists(RUTA_ACTIVIDADES):
        df = pd.read_csv(RUTA_ACTIVIDADES, dtype={"ID": str, "Predecesoras": str})
        df["Predecesoras"] = df["Predecesoras"].fillna("")
        return df
    return _actividades_respaldo.copy()


def cargar_evm_periodos():
    """Carga las curvas acumuladas PV/EV/AC desde data/evm_periodos.csv."""
    if os.path.exists(RUTA_EVM_PERIODOS):
        df = pd.read_csv(RUTA_EVM_PERIODOS)
        pv = df["PV_acumulado"].dropna().tolist()
        ev = df["EV_acumulado"].dropna().tolist()
        ac = df["AC_acumulado"].dropna().tolist()
        return pv, ev, ac
    return _pv_acum_respaldo, _ev_acum_respaldo, _ac_acum_respaldo


def cargar_evm_por_actividad():
    """Carga el desempeno EVM por actividad desde data/evm_por_actividad.csv."""
    if os.path.exists(RUTA_EVM_ACTIVIDAD):
        df = pd.read_csv(RUTA_EVM_ACTIVIDAD)
        return list(df.itertuples(index=False, name=None))
    return _act_evm_respaldo


actividades_default = cargar_actividades()
pv_acum, ev_acum, ac_acum = cargar_evm_periodos()
act_evm_datos = cargar_evm_por_actividad()

# ---------------------------------------------------------------------------
# Funciones de calculo
# ---------------------------------------------------------------------------

def esperado(a, m, b):
    return (a + 4*m + b) / 6

def orden_topologico(ids, pred):
    visitados, orden = set(), []
    def visitar(n):
        if n in visitados:
            return
        visitados.add(n)
        for p in pred.get(n, []):
            visitar(p)
        orden.append(n)
    for n in ids:
        visitar(n)
    return orden

def calcular_cpm(df):
    ids = df["ID"].tolist()
    pred = {}
    for _, r in df.iterrows():
        txt = r["Predecesoras"].strip()
        pred[r["ID"]] = [x.strip() for x in txt.split(",") if x.strip()] if txt else []

    dur = {r["ID"]: esperado(r["d_opt"], r["d_mp"], r["d_pes"]) for _, r in df.iterrows()}
    orden = orden_topologico(ids, pred)

    # Paso adelante
    IC, TC = {n: 0.0 for n in ids}, {}
    for n in orden:
        if pred[n]:
            IC[n] = max(TC[p] for p in pred[n])
        TC[n] = IC[n] + dur[n]

    duracion = max(TC.values())

    # Paso atras
    TF, IC2 = {n: duracion for n in ids}, {}
    for n in reversed(orden):
        sucesores = [s for s in ids if n in pred.get(s, [])]
        if sucesores:
            TF[n] = min(IC2[s] for s in sucesores)
        IC2[n] = TF[n] - dur[n]

    filas = []
    for n in ids:
        nombre = df.loc[df["ID"]==n, "Actividad"].values[0]
        holgura = round(TF[n] - TC[n], 2)
        filas.append({
            "ID": n,
            "Actividad": nombre,
            "Dur esperada": round(dur[n], 2),
            "IC": round(IC[n], 2),
            "TC": round(TC[n], 2),
            "IL": round(IC2[n], 2),
            "TL": round(TF[n], 2),
            "Holgura": holgura,
            "Critica": abs(holgura) < 0.01,
        })
    return pd.DataFrame(filas), duracion


def simular_mc(df, n_sim):
    ids = df["ID"].tolist()
    pred = {}
    for _, r in df.iterrows():
        txt = r["Predecesoras"].strip()
        pred[r["ID"]] = [x.strip() for x in txt.split(",") if x.strip()] if txt else []

    orden = orden_topologico(ids, pred)

    # generar muestras con distribucion triangular
    muestras_dur  = {r["ID"]: np.random.triangular(r["d_opt"], r["d_mp"], r["d_pes"], n_sim)
                     for _, r in df.iterrows()}
    muestras_cost = {r["ID"]: np.random.triangular(r["c_opt"], r["c_mp"], r["c_pes"], n_sim)
                     for _, r in df.iterrows()}

    duraciones = np.zeros(n_sim)
    costos     = np.zeros(n_sim)
    veces_critica = {n: 0 for n in ids}

    for i in range(n_sim):
        d = {n: muestras_dur[n][i] for n in ids}
        IC, TC = {n: 0.0 for n in ids}, {}
        for n in orden:
            if pred[n]:
                IC[n] = max(TC[p] for p in pred[n])
            TC[n] = IC[n] + d[n]

        dur_total = max(TC.values())
        duraciones[i] = dur_total
        costos[i] = sum(muestras_cost[n][i] for n in ids)

        # identificar ruta critica en esta simulacion
        TF, IC2 = {n: dur_total for n in ids}, {}
        for n in reversed(orden):
            suc = [s for s in ids if n in pred.get(s, [])]
            if suc:
                TF[n] = min(IC2[s] for s in suc)
            IC2[n] = TF[n] - d[n]
        for n in ids:
            if abs(TF[n] - TC[n]) < 0.01:
                veces_critica[n] += 1

    idx_crit = {n: round(veces_critica[n]/n_sim*100, 1) for n in ids}
    return duraciones, costos, idx_crit


def calcular_evm(bac, pv, ev, ac):
    sv  = ev - pv
    cv  = ev - ac
    spi = ev / pv  if pv > 0 else 0
    cpi = ev / ac  if ac > 0 else 0
    eac = bac / cpi if cpi > 0 else bac
    etc = eac - ac
    vac = bac - eac
    return dict(PV=pv, EV=ev, AC=ac, BAC=bac,
                SV=sv, CV=cv, SPI=spi, CPI=cpi,
                EAC=eac, ETC=etc, VAC=vac)


def qformat(v):
    signo = "-" if v < 0 else ""
    return f"Q{signo}{abs(v):,.0f}"


# ---------------------------------------------------------------------------
# Estado de sesion
# ---------------------------------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = actividades_default.copy()
if "mc_dur" not in st.session_state:
    st.session_state.mc_dur = None
if "mc_cost" not in st.session_state:
    st.session_state.mc_cost = None
if "mc_idx" not in st.session_state:
    st.session_state.mc_idx = None


# ---------------------------------------------------------------------------
# Navegacion
# ---------------------------------------------------------------------------

st.sidebar.title("Kristhal - Simulador EVM")
st.sidebar.markdown("Lanzamiento tienda en linea")
st.sidebar.divider()

seccion = st.sidebar.radio("Modulo", [
    "Inicio",
    "Proyecto",
    "Ruta Critica",
    "Monte Carlo",
    "EVM",
    "Resumen"
])

st.sidebar.divider()
st.sidebar.caption("Universidad Galileo\nEvaluacion y Control de Proyectos")


# ===========================================================================
# INICIO
# ===========================================================================
if seccion == "Inicio":
    st.title("Simulador de Riesgo y EVM")
    st.subheader("Caso: Joyeria Kristhal - Lanzamiento E-Commerce")
    st.markdown("""
    Joyeria Kristhal vende en local fisico y redes sociales. Este proyecto cubre
    el lanzamiento de su tienda en linea, desde la construccion de marca hasta
    el lanzamiento final.

    La aplicacion integra tres herramientas:
    - **Ruta Critica (CPM/PERT):** duraciones esperadas y red del proyecto
    - **Monte Carlo:** cuantificacion del riesgo en duracion y costo
    - **EVM:** seguimiento del desempeno al periodo de corte

    Usa el menu lateral para navegar entre modulos.
    """)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Resumen del caso**")
        st.markdown("""
        - 7 actividades (A - G)
        - Presupuesto base: Q 84,000
        - Duracion esperada: 50.5 dias
        - Ruta critica: A - C - E - F - G
        - Periodo de corte: dia 30 (periodo 7)
        """)

    with col2:
        st.markdown("**Riesgos identificados**")
        riesgos = pd.DataFrame({
            "Riesgo": [
                "Cambios de alcance en sitio web (Act. C)",
                "Retrasos en certificar pasarela bancaria (D)",
                "Fotografias no aptas, requieren repeticion (B/E)",
            ],
            "Impacto": ["Alto","Medio","Medio"],
        })
        st.dataframe(riesgos, hide_index=True, use_container_width=True)


# ===========================================================================
# PROYECTO - editar actividades
# ===========================================================================
elif seccion == "Proyecto":
    st.title("Definicion del Proyecto")
    st.markdown("Actividades, predecesoras y estimaciones de duracion y costo (optimista / mas probable / pesimista).")

    df_edit = st.data_editor(
        st.session_state.df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID":          st.column_config.TextColumn("ID", width="small"),
            "Actividad":   st.column_config.TextColumn("Actividad", width="large"),
            "Predecesoras":st.column_config.TextColumn("Pred.", width="small"),
            "d_opt": st.column_config.NumberColumn("Dur. opt.",  min_value=0),
            "d_mp":  st.column_config.NumberColumn("Dur. mp",    min_value=0),
            "d_pes": st.column_config.NumberColumn("Dur. pes.",  min_value=0),
            "c_opt": st.column_config.NumberColumn("Costo opt.", min_value=0, format="Q %d"),
            "c_mp":  st.column_config.NumberColumn("Costo mp",   min_value=0, format="Q %d"),
            "c_pes": st.column_config.NumberColumn("Costo pes.", min_value=0, format="Q %d"),
        },
    )

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("Guardar", type="primary"):
            st.session_state.df = df_edit.copy()
            st.session_state.mc_dur = None  # reset simulacion al cambiar datos
            st.success("Datos guardados.")
    with col_b:
        if st.button("Restaurar datos originales"):
            st.session_state.df = actividades_default.copy()
            st.session_state.mc_dur = None
            st.rerun()

    st.divider()
    st.markdown("**Duraciones y costos esperados (PERT)**")

    df_actual = st.session_state.df.copy()
    df_actual["Dur esperada"] = df_actual.apply(
        lambda r: round(esperado(r["d_opt"], r["d_mp"], r["d_pes"]), 2), axis=1)
    df_actual["Costo esperado"] = df_actual.apply(
        lambda r: round(esperado(r["c_opt"], r["c_mp"], r["c_pes"]), 0), axis=1)
    df_actual["Desv dur"] = df_actual.apply(
        lambda r: round((r["d_pes"]-r["d_opt"])/6, 2), axis=1)

    st.dataframe(
        df_actual[["ID","Actividad","Predecesoras","Dur esperada","Desv dur","Costo esperado"]],
        use_container_width=True, hide_index=True
    )
    bac_calc = df_actual["Costo esperado"].sum()
    st.metric("BAC total calculado", qformat(bac_calc))


# ===========================================================================
# RUTA CRITICA
# ===========================================================================
elif seccion == "Ruta Critica":
    st.title("Ruta Critica - CPM/PERT")

    df = st.session_state.df.copy()
    tabla_cpm, dur_proyecto = calcular_cpm(df)

    criticas = tabla_cpm[tabla_cpm["Critica"]]["ID"].tolist()
    st.success(f"Ruta critica: {' - '.join(criticas)}  |  Duracion: {dur_proyecto:.1f} dias")

    # tabla con holguras
    def resaltar_critica(row):
        if row["Critica"]:
            return ["background-color: #f8d7da"] * len(row)
        return [""] * len(row)

    st.dataframe(
        tabla_cpm.style.apply(resaltar_critica, axis=1),
        use_container_width=True, hide_index=True
    )

    st.divider()
    st.markdown("**Diagrama de red**")

    # construir grafo
    pred_dict = {}
    for _, r in df.iterrows():
        txt = r["Predecesoras"].strip()
        pred_dict[r["ID"]] = [x.strip() for x in txt.split(",") if x.strip()] if txt else []

    G = nx.DiGraph()
    for nid in df["ID"]:
        G.add_node(nid)
    for nid, ps in pred_dict.items():
        for p in ps:
            G.add_edge(p, nid)

    # calcular posiciones por nivel topologico
    niveles = {}
    for n in nx.topological_sort(G):
        preds_n = list(G.predecessors(n))
        niveles[n] = max((niveles[p] for p in preds_n), default=-1) + 1

    conteo_nivel = {}
    for n, lv in sorted(niveles.items(), key=lambda x: x[1]):
        conteo_nivel[lv] = conteo_nivel.get(lv, 0) + 1

    pos = {}
    idx_nivel = {}
    for n, lv in sorted(niveles.items(), key=lambda x: x[1]):
        i = idx_nivel.get(lv, 0)
        total = conteo_nivel[lv]
        pos[n] = (lv * 200, (i - total/2) * 160)
        idx_nivel[lv] = i + 1

    # info para hover
    info_cpm = tabla_cpm.set_index("ID")

    # aristas
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # nodos
    nx_list = list(G.nodes())
    node_x = [pos[n][0] for n in nx_list]
    node_y = [pos[n][1] for n in nx_list]
    colores = ["#c0392b" if info_cpm.loc[n,"Critica"] else "#2E75B6" for n in nx_list]
    labels_hover = []
    for n in nx_list:
        r = info_cpm.loc[n]
        labels_hover.append(
            f"{n}: {r['Actividad']}<br>"
            f"Dur={r['Dur esperada']:.1f} dias<br>"
            f"IC={r['IC']:.0f}  TC={r['TC']:.0f}<br>"
            f"Holgura={r['Holgura']:.1f}"
        )

    fig_red = go.Figure()
    fig_red.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#aaa", width=1.5), hoverinfo="none"
    ))
    fig_red.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=42, color=colores, line=dict(width=2, color="white")),
        text=nx_list,
        textfont=dict(size=14, color="white"),
        textposition="middle center",
        customdata=labels_hover,
        hovertemplate="%{customdata}<extra></extra>",
        showlegend=False,
    ))
    fig_red.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        title="Rojo = actividades en ruta critica",
    )
    st.plotly_chart(fig_red, use_container_width=True)

    # todas las rutas
    st.divider()
    st.markdown("**Comparacion de rutas**")

    raices = [n for n in G.nodes() if G.in_degree(n) == 0]
    hojas  = [n for n in G.nodes() if G.out_degree(n) == 0]
    rutas_encontradas = []
    for r in raices:
        for h in hojas:
            try:
                rutas_encontradas += list(nx.all_simple_paths(G, r, h))
            except Exception:
                pass

    dur_esperada = tabla_cpm.set_index("ID")["Dur esperada"]
    datos_rutas = []
    for ruta in rutas_encontradas:
        d = round(sum(dur_esperada[n] for n in ruta), 2)
        datos_rutas.append({
            "Ruta": " - ".join(ruta),
            "Duracion (dias)": d,
            "Es critica": d == round(dur_proyecto, 2)
        })

    df_rutas = pd.DataFrame(datos_rutas).sort_values("Duracion (dias)", ascending=False)

    def marca_critica(row):
        if row["Es critica"]:
            return ["background-color: #f8d7da"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_rutas.style.apply(marca_critica, axis=1),
        use_container_width=True, hide_index=True
    )


# ===========================================================================
# MONTE CARLO
# ===========================================================================
elif seccion == "Monte Carlo":
    st.title("Simulacion Monte Carlo")
    st.markdown("Distribucion triangular sobre estimaciones optimista / mas probable / pesimista.")

    col1, col2, col3 = st.columns(3)
    with col1:
        n_sim = st.number_input("Numero de simulaciones", 1000, 50000, 10000, 1000)
    with col2:
        fecha_obj = st.number_input("Fecha objetivo (dias)", 30, 200, 55)
    with col3:
        ppto_obj = st.number_input("Presupuesto objetivo (Q)", 50000, 200000, 90000, 5000)

    np.random.seed(42)

    if st.button("Ejecutar simulacion", type="primary"):
        with st.spinner("Corriendo simulaciones..."):
            dur_mc, cost_mc, idx_crit = simular_mc(st.session_state.df, n_sim)
        st.session_state.mc_dur  = dur_mc
        st.session_state.mc_cost = cost_mc
        st.session_state.mc_idx  = idx_crit
        st.success(f"Listo: {n_sim:,} simulaciones.")

    if st.session_state.mc_dur is None:
        st.info("Presiona 'Ejecutar simulacion' para ver resultados.")
        st.stop()

    dur_mc  = st.session_state.mc_dur
    cost_mc = st.session_state.mc_cost
    idx_crit= st.session_state.mc_idx

    p50_d = np.percentile(dur_mc, 50)
    p80_d = np.percentile(dur_mc, 80)
    p50_c = np.percentile(cost_mc, 50)
    p80_c = np.percentile(cost_mc, 80)
    prob_d = np.mean(dur_mc  <= fecha_obj) * 100
    prob_c = np.mean(cost_mc <= ppto_obj)  * 100

    st.divider()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Media duracion",  f"{dur_mc.mean():.1f} d")
    c2.metric("P50 duracion",    f"{p50_d:.1f} d")
    c3.metric("P80 duracion",    f"{p80_d:.1f} d")
    c4.metric("Media costo",     qformat(cost_mc.mean()))
    c5.metric("P50 costo",       qformat(p50_c))
    c6.metric("P80 costo",       qformat(p80_c))

    c7, c8 = st.columns(2)
    c7.metric(f"Prob. terminar en <= {fecha_obj} dias", f"{prob_d:.1f}%")
    c8.metric(f"Prob. costo <= {qformat(ppto_obj)}",    f"{prob_c:.1f}%")

    st.divider()

    # histogramas
    fig_h = make_subplots(rows=1, cols=2,
        subplot_titles=("Distribucion de duracion", "Distribucion de costo total"))

    fig_h.add_trace(go.Histogram(x=dur_mc, nbinsx=50,
        marker_color="rgba(46,117,182,0.75)", showlegend=False), row=1, col=1)
    fig_h.add_vline(x=p50_d, line_color="green", line_dash="dash",
        annotation_text=f"P50={p50_d:.0f}d", row=1, col=1)
    fig_h.add_vline(x=p80_d, line_color="orange", line_dash="dash",
        annotation_text=f"P80={p80_d:.0f}d", row=1, col=1)
    fig_h.add_vline(x=fecha_obj, line_color="red", line_dash="dot",
        annotation_text=f"Obj={fecha_obj}d", row=1, col=1)

    fig_h.add_trace(go.Histogram(x=cost_mc, nbinsx=50,
        marker_color="rgba(192,57,43,0.75)", showlegend=False), row=1, col=2)
    fig_h.add_vline(x=p50_c, line_color="green",  line_dash="dash",
        annotation_text="P50", row=1, col=2)
    fig_h.add_vline(x=p80_c, line_color="orange", line_dash="dash",
        annotation_text="P80", row=1, col=2)
    fig_h.add_vline(x=ppto_obj, line_color="red", line_dash="dot",
        annotation_text="Obj", row=1, col=2)

    fig_h.update_xaxes(title_text="Dias",       row=1, col=1)
    fig_h.update_xaxes(title_text="Quetzales",  row=1, col=2)
    fig_h.update_yaxes(title_text="Frecuencia", row=1, col=1)
    fig_h.update_layout(height=380, margin=dict(t=50, b=30))
    st.plotly_chart(fig_h, use_container_width=True)

    # tabla de percentiles
    st.markdown("**Tabla de percentiles**")
    pcts = [10, 25, 50, 75, 80, 90, 95]
    st.dataframe(pd.DataFrame({
        "Percentil":       [f"P{p}" for p in pcts],
        "Duracion (dias)": [round(np.percentile(dur_mc,  p), 1) for p in pcts],
        "Costo (Q)":       [round(np.percentile(cost_mc, p), 0) for p in pcts],
    }), hide_index=True, use_container_width=True)

    # indice de criticidad
    st.divider()
    st.markdown("**Indice de criticidad** — frecuencia en ruta critica por simulacion")

    df_ic = pd.DataFrame({
        "Actividad":       list(idx_crit.keys()),
        "% critica":       list(idx_crit.values()),
    }).sort_values("% critica", ascending=True)

    fig_ic = go.Figure(go.Bar(
        x=df_ic["% critica"], y=df_ic["Actividad"],
        orientation="h",
        marker_color=["#c0392b" if v >= 50 else "#2E75B6" for v in df_ic["% critica"]],
        text=[f"{v:.1f}%" for v in df_ic["% critica"]],
        textposition="outside",
    ))
    fig_ic.add_vline(x=50, line_dash="dash", line_color="gray",
                     annotation_text="50%")
    fig_ic.update_layout(height=320, margin=dict(l=10, r=60, t=20, b=30),
                         xaxis_title="% de simulaciones en ruta critica")
    st.plotly_chart(fig_ic, use_container_width=True)


# ===========================================================================
# EVM
# ===========================================================================
elif seccion == "EVM":
    st.title("EVM - Gestion del Valor Ganado")
    st.markdown("Datos al corte del periodo 7 (dia 30).")

    col1, col2, col3, col4 = st.columns(4)
    with col1: bac = st.number_input("BAC", value=84000, step=500)
    with col2: pv  = st.number_input("PV",  value=58013, step=100)
    with col3: ev  = st.number_input("EV",  value=54513, step=100)
    with col4: ac  = st.number_input("AC",  value=62500, step=100)

    evm = calcular_evm(bac, pv, ev, ac)

    st.divider()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("SV (variacion cronograma)", qformat(evm["SV"]),
                  delta="Retraso" if evm["SV"] < 0 else "Adelantado")
        st.metric("SPI", f"{evm['SPI']:.3f}",
                  delta="Desfavorable" if evm["SPI"] < 1 else "Favorable")
    with col_b:
        st.metric("CV (variacion costo)", qformat(evm["CV"]),
                  delta="Sobrecosto" if evm["CV"] < 0 else "Bajo presupuesto")
        st.metric("CPI", f"{evm['CPI']:.3f}",
                  delta="Desfavorable" if evm["CPI"] < 1 else "Favorable")
    with col_c:
        st.metric("EAC (costo final estimado)", qformat(evm["EAC"]))
        st.metric("ETC (costo restante)",       qformat(evm["ETC"]))
        st.metric("VAC",                        qformat(evm["VAC"]),
                  delta="Sobrecosto previsto" if evm["VAC"] < 0 else "Ahorro previsto")

    st.divider()

    # desempeno por actividad
    st.markdown("**Desempeno por actividad al corte**")

    filas_act = []
    for nombre, bac_a, ev_a, ac_a, pct in act_evm_datos:
        cv_a  = ev_a - ac_a
        cpi_a = round(ev_a / ac_a, 3) if ac_a > 0 else None
        filas_act.append({
            "Actividad": nombre,
            "BAC": bac_a,
            "EV":  ev_a,
            "AC":  ac_a,
            "Avance": f"{pct:.0%}",
            "CV": cv_a,
            "CPI": cpi_a if cpi_a else "-",
        })

    df_act = pd.DataFrame(filas_act)

    def color_cv(val):
        if isinstance(val, (int, float)):
            return "color: red" if val < 0 else "color: green"
        return ""

    st.dataframe(
        df_act.style.map(color_cv, subset=["CV"]),
        use_container_width=True, hide_index=True
    )

    st.divider()

    # curva S
    st.markdown("**Curva S - PV, EV y AC acumulados**")

    periodos   = list(range(1, len(pv_acum)+1))
    periodos_ev = list(range(1, len(ev_acum)+1))
    periodos_ac = list(range(1, len(ac_acum)+1))

    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(x=periodos, y=pv_acum, name="PV",
        mode="lines+markers", line=dict(color="#2E75B6", dash="dash", width=2)))
    fig_s.add_trace(go.Scatter(x=periodos_ev, y=ev_acum, name="EV",
        mode="lines+markers", line=dict(color="#28a745", width=2)))
    fig_s.add_trace(go.Scatter(x=periodos_ac, y=ac_acum, name="AC",
        mode="lines+markers", line=dict(color="#c0392b", width=2)))
    fig_s.add_vline(x=7, line_dash="dot", line_color="gray",
                    annotation_text="Corte P7")
    fig_s.add_hline(y=bac, line_dash="dot", line_color="#888",
                    annotation_text=f"BAC = {qformat(bac)}", annotation_position="right")
    fig_s.update_layout(
        height=420,
        xaxis_title="Periodo",
        yaxis_title="Q acumulado",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig_s, use_container_width=True)

    st.markdown(f"""
    **Interpretacion al periodo 7:**
    El proyecto va retrasado: el SPI de {evm['SPI']:.2f} indica que avanza al {evm['SPI']*100:.0f}%
    del ritmo planificado. Tambien presenta sobrecosto: por cada quetzal gastado se generan
    Q{evm['CPI']:.2f} de valor (CPI={evm['CPI']:.2f}). Si se mantiene esta eficiencia, el proyecto
    cerraria en {qformat(evm['EAC'])}, unos {qformat(abs(evm['VAC']))} por encima del BAC.
    El mayor problema esta en la actividad C (80% completada con sobrecosto) y D/E que recien empiezan.
    """)


# ===========================================================================
# RESUMEN / DASHBOARD
# ===========================================================================
elif seccion == "Resumen":
    st.title("Resumen Ejecutivo")

    df = st.session_state.df.copy()
    _, dur_proyecto = calcular_cpm(df)
    evm = calcular_evm(84000, 58013, 54513, 62500)

    # metricas principales
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("BAC",           qformat(84000))
    col2.metric("Duracion CPM",  f"{dur_proyecto:.1f} dias")
    col3.metric("SPI al corte",  f"{evm['SPI']:.3f}")
    col4.metric("CPI al corte",  f"{evm['CPI']:.3f}")
    col5.metric("EAC estimado",  qformat(evm["EAC"]))

    st.divider()

    cola, colb = st.columns(2)

    with cola:
        # gauge CPI
        fig_cpi = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=round(evm["CPI"], 3),
            title={"text": "CPI"},
            delta={"reference": 1.0},
            gauge={
                "axis": {"range": [0, 1.5]},
                "bar":  {"color": "#c0392b" if evm["CPI"] < 1 else "#28a745"},
                "steps": [
                    {"range": [0.0, 0.8], "color": "#f8d7da"},
                    {"range": [0.8, 1.0], "color": "#fff3cd"},
                    {"range": [1.0, 1.5], "color": "#d4edda"},
                ],
                "threshold": {"line": {"color": "black", "width": 3}, "value": 1.0},
            }
        ))
        fig_cpi.update_layout(height=260, margin=dict(t=50, b=10, l=20, r=20))
        st.plotly_chart(fig_cpi, use_container_width=True)

        # gauge SPI
        fig_spi = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=round(evm["SPI"], 3),
            title={"text": "SPI"},
            delta={"reference": 1.0},
            gauge={
                "axis": {"range": [0, 1.5]},
                "bar":  {"color": "#f39c12" if evm["SPI"] < 1 else "#28a745"},
                "steps": [
                    {"range": [0.0, 0.8], "color": "#f8d7da"},
                    {"range": [0.8, 1.0], "color": "#fff3cd"},
                    {"range": [1.0, 1.5], "color": "#d4edda"},
                ],
                "threshold": {"line": {"color": "black", "width": 3}, "value": 1.0},
            }
        ))
        fig_spi.update_layout(height=260, margin=dict(t=50, b=10, l=20, r=20))
        st.plotly_chart(fig_spi, use_container_width=True)

    with colb:
        # comparacion BAC vs EAC vs MC
        etiquetas = ["BAC", "EAC (CPI)"]
        valores   = [84000, evm["EAC"]]
        colores_b = ["#2E75B6", "#c0392b"]

        if st.session_state.mc_cost is not None:
            mc_c = st.session_state.mc_cost
            etiquetas += ["P50 MC", "P80 MC"]
            valores   += [np.percentile(mc_c, 50), np.percentile(mc_c, 80)]
            colores_b += ["#28a745", "#f39c12"]

        fig_bar = go.Figure(go.Bar(
            x=etiquetas, y=valores, marker_color=colores_b,
            text=[qformat(v) for v in valores], textposition="outside",
        ))
        fig_bar.update_layout(
            title="Comparacion de costo: BAC vs pronosticos",
            height=420,
            yaxis_title="Quetzales",
            showlegend=False,
        )
        if st.session_state.mc_cost is None:
            fig_bar.add_annotation(
                text="Ejecuta Monte Carlo para ver P50/P80",
                xref="paper", yref="paper", x=0.7, y=0.5,
                showarrow=False, font=dict(color="gray")
            )
        st.plotly_chart(fig_bar, use_container_width=True)

    # curva S resumida
    st.divider()
    periodos_all = list(range(1, len(pv_acum)+1))
    fig_s2 = go.Figure()
    fig_s2.add_trace(go.Scatter(x=periodos_all, y=pv_acum, name="PV",
        line=dict(color="#2E75B6", dash="dash", width=2), mode="lines+markers"))
    fig_s2.add_trace(go.Scatter(x=list(range(1, len(ev_acum)+1)), y=ev_acum, name="EV",
        line=dict(color="#28a745", width=2), mode="lines+markers"))
    fig_s2.add_trace(go.Scatter(x=list(range(1, len(ac_acum)+1)), y=ac_acum, name="AC",
        line=dict(color="#c0392b", width=2), mode="lines+markers"))
    fig_s2.add_vline(x=7, line_dash="dot", line_color="gray")
    fig_s2.update_layout(height=300, xaxis_title="Periodo",
        yaxis_title="Q acumulado", hovermode="x unified",
        legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_s2, use_container_width=True)

    # estado del proyecto en texto
    st.divider()
    st.markdown("**Estado del proyecto al periodo de corte**")

    estado = [
        ("Cronograma", evm["SPI"] >= 0.95,
         f"SPI = {evm['SPI']:.2f} — va al {evm['SPI']*100:.0f}% del ritmo. Retraso principal en actividad C."),
        ("Costo", evm["CPI"] >= 0.95,
         f"CPI = {evm['CPI']:.2f} — sobrecosto acumulado de {qformat(abs(evm['CV']))}. Act. A y C superaron presupuesto."),
        ("Ruta critica", True,
         "Actividades A-C-E-F-G son criticas. B y D tienen holgura disponible."),
        ("Pronostico cierre", evm["EAC"] <= 90000,
         f"EAC = {qformat(evm['EAC'])} — se proyecta un sobrecosto de {qformat(abs(evm['VAC']))} al cierre."),
    ]

    for nombre, ok, detalle in estado:
        color = "#d4edda" if ok else "#f8d7da"
        indicador = "OK" if ok else "Alerta"
        st.markdown(
            f'<div style="background:{color};border-radius:5px;padding:9px 14px;margin:5px 0;">'
            f'<b>{nombre} [{indicador}]:</b> {detalle}</div>',
            unsafe_allow_html=True
        )

    st.markdown("""
    **Conclusion:** El proyecto muestra presion en costo y cronograma al periodo 7.
    La actividad C es el punto critico, con 80% de avance y sobrecosto. Para las semanas restantes
    se recomienda reforzar el equipo de desarrollo y revisar el alcance para no ampliar el presupuesto.
    """)
