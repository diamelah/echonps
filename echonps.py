import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import matplotlib.pyplot as plt

# Configuración inicial de la página
st.set_page_config(page_title="Dashboard NPS", layout="wide")
st.title("Análisis Verbatims NPS Relacionamiento")

# Cargar datos desde un archivo CSV
uploaded_file = st.sidebar.file_uploader("Sube tu archivo CSV", type=["csv"])
df = None
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")

# Si no hay datos, mostrar un mensaje y salir
if df is None:
    st.warning("Sube un archivo CSV para visualizar los datos.")
    st.stop()

# --- Filtros de Fecha ---
st.sidebar.header("Filtros")
if "fecha" in df.columns:
    fecha_min = df["fecha"].min().date()
    fecha_max = df["fecha"].max().date()
    fecha_inicio = st.sidebar.date_input("Fecha inicio", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
    fecha_fin = st.sidebar.date_input("Fecha fin", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
    df = df[(df["fecha"].dt.date >= fecha_inicio) & (df["fecha"].dt.date <= fecha_fin)]

# --- Pestañas para diferentes análisis ---
tabs = st.tabs([
    "Tendencias en el Tiempo", "Segmentos y Categorías", "Verbatims", "Clasificación de Dolores", "Canales de Atención",
    "Tabla Completa"
])

# 1. Tendencias en el Tiempo
with tabs[0]:
    st.subheader("Tendencias en el Tiempo")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)
    df_filtered = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)].copy()
    df_filtered["Periodo"] = df_filtered["fecha"].dt.date
    df_filtered = df_filtered.dropna(subset=["Periodo"])

    # ✅ Calcular métricas solo si existen las columnas necesarias
    if "nps" in df_filtered.columns and "score" in df_filtered.columns:
        total_nps = df_filtered["nps"].count()
        score_promedio = df_filtered["score"].mean()
        detractores = df_filtered[df_filtered["nps"] < 7].shape[0]
        porcentaje_detractores = (detractores / total_nps * 100) if total_nps > 0 else 0
    else:
        st.warning("No se encontraron las columnas 'nps' y/o 'score' en el archivo cargado.")
        total_nps = 0
        score_promedio = 0
        porcentaje_detractores = 0

    # 📌 Mostrar métricas clave
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Respuestas NPS", total_nps)
    col2.metric("Score Promedio", f"{score_promedio:.2f}")
    col3.metric("% Detractores", f"{porcentaje_detractores:.2f}%")

    # 📈 Score Promedio por día
    df_grouped = df_filtered.groupby("Periodo").agg({"score": "mean", "fecha": "count"}).rename(
        columns={"score": "Score Promedio", "fecha": "Cantidad Encuestas"}
    )
    fig_line = px.line(df_grouped, x=df_grouped.index, y="Score Promedio", title="Evolución del Score Promedio")
    st.plotly_chart(fig_line, use_container_width=True)

    # 📉 Evolución de Detractores
    df_filtered["detractor"] = df_filtered["nps"] < 7
    df_grouped_det = df_filtered[df_filtered["detractor"]].groupby("Periodo").agg(
        Cantidad_Detractores=("detractor", "sum"),
        Ciclo_Facturacion=("ciclo_fact", "first"),
        Verbatim=("verbatim", "first")
    ).reset_index()

    fig_det = px.line(
        df_grouped_det,
        x="Periodo",
        y="Cantidad_Detractores",
        title="Evolución de Detractores",
        markers=True,
        hover_data={"Ciclo_Facturacion": True, "Verbatim": True}
    )
    fig_det.update_traces(line=dict(color="red"))
    st.plotly_chart(fig_det, use_container_width=True)

    # 📊 Evolución del volumen de respuestas por grupo NPS
    if "grupo_nps" in df_filtered.columns:
        df_volumen = df_filtered.groupby(["Periodo", "grupo_nps"]).size().reset_index(name="Cantidad")
        fig_vol = px.bar(
            df_volumen,
            x="Periodo",
            y="Cantidad",
            color="grupo_nps",
            barmode="stack",
            title="Volumen de respuestas por Grupo NPS en el tiempo",
            color_discrete_map={
                "Detractor": "red",
                "Pasivo": "skyblue",
                "Promotor": "blue"
            }
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # 📋 Evolución de categorías más mencionadas
    if "categoria" in df_filtered.columns:
        df_cat = df_filtered.groupby(["Periodo", "categoria"]).size().reset_index(name="Cantidad")
        top_categorias = df_cat.groupby("categoria")["Cantidad"].sum().nlargest(5).index
        df_cat_top = df_cat[df_cat["categoria"].isin(top_categorias)]
        fig_cat = px.bar(
            df_cat_top,
            x="Periodo",
            y="Cantidad",
            color="categoria",
            barmode="group",
            title="Top 5 Categorías mencionadas por período"
        )
        st.plotly_chart(fig_cat, use_container_width=True)




# 2. Segmentos y Categorías
with tabs[1]:
    st.subheader("Segmentos y Categorías")
    
    # Descripción
    st.markdown("""
    📌 **Descripción:**  
    Aquí se analiza cómo varía el **Score Promedio** según diferentes **segmentos de clientes**, 
    permitiendo identificar qué grupos están más satisfechos o insatisfechos.  

    También se presenta un desglose del **Score Promedio por Categoría**, 
    lo que ayuda a evaluar qué tipo de experiencias afectan más la satisfacción.
    """)
    
    if "segmento" in df.columns and "score" in df.columns:
        colA, colB, colC = st.columns(3)
        grupo_nps_filter = colA.selectbox("Grupo NPS", ["Todos"] + list(df["grupo_nps"].dropna().unique()))
        df_filtered = df.copy()
        if grupo_nps_filter != "Todos":
            df_filtered = df_filtered[df_filtered["grupo_nps"] == grupo_nps_filter]
        df_seg = df_filtered.groupby("segmento")["score"].mean().reset_index()
        fig_barh = px.bar(
            df_seg, x="score", y="segmento", orientation="h", title="Score Promedio por Segmento",
            labels={"score": "Score Promedio", "segmento": "Segmento"}, text_auto=".2f",
            color="segmento", color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig_barh, use_container_width=True)
        mask = (df["segmento"].isna() | (df["segmento"] == "(NULL)") | (df["segmento"].astype(str).str.strip() == ""))
        df_null_seg = df[mask].copy()
        if not df_null_seg.empty:
            st.write("### Registros con Segmento nulo, vacío o '(NULL)'")
            st.dataframe(df_null_seg[["dni", "fecha", "segmento", "grupo_nps", "categoria", "tecnologia"]])
        else:
            st.write("No hay registros con Segmento nulo, vacío o '(NULL)'.")
    if all(col in df.columns for col in ["categoria", "score", "grupo_nps"]):
        colA, colB = st.columns([1, 3])
        with colA:
            grupo_nps_filter = st.selectbox("Grupo NPS", ["Todos"] + list(df["grupo_nps"].dropna().unique()), key="grupo_nps_filter")
        df_filtered = df.copy()
        if grupo_nps_filter != "Todos":
            df_filtered = df_filtered[df_filtered["grupo_nps"] == grupo_nps_filter]
        df_cat = df_filtered.groupby("categoria")["score"].mean().reset_index()
        fig_bar = px.bar(
            df_cat, x="score", y="categoria", orientation="h",
            title=f"Score Promedio por Categoría (Grupo NPS: {grupo_nps_filter})",
            labels={"score": "Score Promedio", "categoria": "Categoría"},
            text_auto=".2f", color="categoria",
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# 3. Distribución de Respuestas NPS
with tabs[2]:
    st.subheader("Distribución de Respuestas NPS")

    # Descripción
    st.markdown("""
    📢 **Descripción:**  
    Esta sección permite filtrar y analizar las respuestas NPS según **Grupo NPS, Categoría y palabras clave en los verbatims**  

    Además, se presenta la **Distribución de Respuestas por Grupo NPS** en formato de tabla y gráfico, 
    facilitando la identificación de tendencias en la satisfacción del cliente.
    """)

    required_cols = ["dni", "fecha", "verbatim", "grupo_nps", "categoria"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.write("⚠️ **Faltan las siguientes columnas necesarias:**", missing_cols)
    else:
        col1, col2 = st.columns(2)
        with col1:
            grupo_nps_filter = st.selectbox("Filtrar por Grupo NPS", ["Todos"] + sorted(df["grupo_nps"].dropna().unique().tolist()), key="grupo_nps_filter_nps")
        with col2:
            categoria_filter = st.selectbox("Filtrar por Categoría", ["Todos"] + sorted(df["categoria"].dropna().unique().tolist()), key="categoria_filter_nps")

        search_word = st.text_input("Buscar palabra en Verbatim (separadas por comas)", key="verbatim_search")

        df_filtered = df.copy()
        if grupo_nps_filter != "Todos":
            df_filtered = df_filtered[df_filtered["grupo_nps"] == grupo_nps_filter]
        if categoria_filter != "Todos":
            df_filtered = df_filtered[df_filtered["categoria"] == categoria_filter]

        df_base = df_filtered.copy()

        if search_word:
            tokens = [token.strip() for token in search_word.split(",") if token.strip()]
            mask = pd.Series(False, index=df_filtered.index)
            for token in tokens:
                mask |= df_filtered["verbatim"].str.contains(token, case=False, na=False)
            df_tokens = df_filtered[mask].copy()

            total_by_group = df_base.groupby("grupo_nps").size()
            tokens_by_group = df_tokens.groupby("grupo_nps").size()
            df_percentage = pd.DataFrame({"Total": total_by_group, "Con Tokens": tokens_by_group})
            df_percentage["Con Tokens"] = df_percentage["Con Tokens"].fillna(0)
            df_percentage["% Verbatim"] = (df_percentage["Con Tokens"] / df_percentage["Total"] * 100).round(1)
            st.write("### Porcentaje de verbatim que contienen los tokens, por Grupo NPS")
            st.dataframe(df_percentage.reset_index())
            df_filtered = df_tokens.copy()

            # --- Gráfico de tendencia en el tiempo ---
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # Tokenización simple
            df_filtered["tokens"] = df_filtered["verbatim"].astype(str).apply(lambda x: x.lower().split())

            tendencia_df = pd.DataFrame()
            token_counts = {}
            for palabra in tokens:
                df_filtered[f"contiene_{palabra}"] = df_filtered["tokens"].apply(lambda t: palabra.lower() in t)
                tendencia = df_filtered.groupby(df_filtered["fecha"].dt.to_period("M"))[f"contiene_{palabra}"].sum()
                tendencia_df[palabra] = tendencia
                token_counts[palabra] = df_filtered[f"contiene_{palabra}"].sum()

            tendencia_df.index = tendencia_df.index.to_timestamp()

            st.subheader("📈 Tendencia de palabras clave en el tiempo")
            fig, ax = plt.subplots(figsize=(10, 5))
            for palabra in tokens:
                ax.plot(tendencia_df.index, tendencia_df[palabra], label=palabra, marker='o')

            ax.set_title("Menciones de palabras clave por mes")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Cantidad de menciones")
            ax.legend()
            ax.grid(True)

            # Formato del eje X solo día y mes
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
            fig.autofmt_xdate()

            st.pyplot(fig)

            # --- Tabla resumen de ocurrencias ---
            st.write("### Cantidad total de menciones por palabra clave en el periodo seleccionado")
            resumen_tokens = pd.DataFrame.from_dict(token_counts, orient="index", columns=["Cantidad de menciones"])
            resumen_tokens.index.name = "Palabra"
            st.dataframe(resumen_tokens.reset_index())

        st.write("### Tabla Completa de Respuestas NPS (filtrada)")
        st.dataframe(df_filtered[required_cols])




        



# 4. Clasificación de Dolores
with tabs[3]:
    st.subheader("Clasificación de Dolores")
    
    # Descripción
    st.markdown("""
    ⚠️ **Descripción:**  
    Aquí se identifican y categorizan los comentarios de los clientes según las palabras clave 
    asociadas a **dolores o problemas frecuentes**.  

    Esto permite comprender los principales motivos de insatisfacción y priorizar acciones de mejora.
    """)
    
    if "verbatim" in df.columns and "grupo_nps" in df.columns:
        dolores = {
            "Precio": ["precio", "caro", "barato", "tarifa"],
            "Política Comercial": ["contrato", "plan", "cambio de plan", "oferta"],
            "Funcionamiento del Servicio": ["corte", "lento", "velocidad", "señal", "problema"],
            "Atención en la Venta": ["vendedor", "compra", "asesoramiento"],
            "Atención al Cliente": ["atención", "asesor", "trato", "mal atendido", "pésimo servicio", "mala atención"],
            "Resolución": ["solución", "resolver", "no resuelven", "demora"],
            "IVR": ["robot", "opciones", "menú", "atendedor automático", "no atienden", "no pude hablar con nadie"],
            "Tiempos de Atención": ["rápido", "lento", "espera", "demora"],
            "Procesos": ["gestión", "documentación", "trámite"],
            "Delivery": ["entrega", "envío", "demora en entrega"],
            "Facturación": ["factura", "cobro", "error en factura"],
            "Pagos": ["pago", "tarjeta", "transferencia", "no puedo pagar"],
            "Atención Técnico": ["técnico", "visita", "reparación", "arreglo"],
            "Cita Técnica": ["turno", "fecha", "visita programada"],
            "Estafa": ["fraude", "robo", "estafado"],
            "Jubilados": ["pensión", "jubilado", "descuento"],
            "Bueno": ["excelente", "satisfecho", "recomiendo", "bueno"],
            "Flow": ["flow", "tv", "canales", "se corta"],
            "App/Web/WhatsApp": ["app", "web", "whatsapp", "online"]
        }
        
        def clasificar_dolor(verbatim):
            if pd.isnull(verbatim):
                return "No identificado"
            text = verbatim.lower()
            coincidencias = [categoria for categoria, palabras in dolores.items() if any(palabra in text for palabra in palabras)]
            return ", ".join(coincidencias) if coincidencias else "No identificado"
        
        df["dolor"] = df["verbatim"].apply(clasificar_dolor)
        
        st.markdown("### Filtros")
        grupo_options = ["Todos"] + sorted(list(df["grupo_nps"].dropna().unique()))
        selected_grupo = st.selectbox("Filtrar por Grupo NPS", grupo_options)
        dolor_options = ["Todos"] + sorted(list(df["dolor"].dropna().unique()))
        selected_dolor = st.selectbox("Filtrar por Dolor", dolor_options)
        if df["fecha"].notnull().any():
            fecha_min = df["fecha"].min().date()
            fecha_max = df["fecha"].max().date()
        else:
            fecha_min = fecha_max = None
        selected_fechas = st.date_input("Filtrar por Fecha (rango)", [fecha_min, fecha_max])
        selected_verbatim = st.text_input("Filtrar por Verbatim (contiene)")
        df_filtered = df.copy()
        if selected_grupo != "Todos":
            df_filtered = df_filtered[df_filtered["grupo_nps"] == selected_grupo]
        if selected_dolor != "Todos":
            df_filtered = df_filtered[df_filtered["dolor"].str.contains(selected_dolor, case=False, na=False)]
        if isinstance(selected_fechas, list) and len(selected_fechas) == 2:
            start_date, end_date = selected_fechas
            df_filtered = df_filtered[(df_filtered["fecha"].dt.date >= start_date) & (df_filtered["fecha"].dt.date <= end_date)]
        if selected_verbatim:
            df_filtered = df_filtered[df_filtered["verbatim"].str.contains(selected_verbatim, case=False, na=False)]
        st.markdown("### Tabla Filtrada")
        st.dataframe(df_filtered[["dni","fecha", "verbatim", "grupo_nps", "dolor"]])
        st.markdown("""
        **Explicación:**
        - **Verbatim:** Comentario del cliente.
        - **Grupo_nps:** Grupo al que pertenece el cliente.
        - **Dolor:** Clasificación basada en la presencia de palabras clave (dolores) en el comentario.
        """)

# 5. Canales de Atención
with tabs[4]:
    st.subheader("Canales de Atención")

    required_cols = [
        "dni", "verbatim", "centro_atencion", "canal_atencion", "resuelto", "no_por_que", "grupo_nps", "categoria"
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.write("⚠️ **Faltan las siguientes columnas necesarias:**", missing_cols)
    else:
        total_registros = len(df)
        registros_centro_atencion = df["centro_atencion"].notna().sum()
        st.write(f"### Total de Registros: {total_registros}")
        st.write(f"### Registros con Centro de Atención: {registros_centro_atencion}")

        st.write("### Filtrar Canales de Atención")
        col1, col2, col3 = st.columns(3)
        col4, col5 = st.columns(2)

        canales_validos = [
            "App Personal Flow",
            "App Personal Flow (Sección Mi WiFI)",
            "Chat por whatsapp",
            "Personalmente",
            "Redes sociales",
            "Telefónico",
            "Web Personal"
        ]

        filters = {}
        filters["centro_atencion"] = col1.selectbox("Centro Atención", ["Todos"] + sorted(df["centro_atencion"].dropna().unique()))
        filters["canal_atencion"] = col2.selectbox("Canal", ["Todos"] + canales_validos)
        filters["resuelto"] = col3.selectbox("Resuelto", ["Todos"] + sorted(df["resuelto"].dropna().astype(str).unique().tolist() + ["None"]))
        filters["grupo_nps"] = col4.selectbox("Grupo NPS", ["Todos"] + sorted(df["grupo_nps"].dropna().unique()))
        filters["categoria"] = col5.selectbox("Categoría", ["Todos"] + sorted(df["categoria"].dropna().unique()))

        df = df[df["canal_atencion"].isin(canales_validos)]
        df_filtered = df.copy()
        for col, value in filters.items():
            if value != "Todos":
                if col == "resuelto" and value == "None":
                    df_filtered = df_filtered[df_filtered[col].isna()]
                else:
                    df_filtered = df_filtered[df_filtered[col] == value]

        st.write("### Tabla de Canales de Atención con Filtros")
        st.dataframe(df_filtered[required_cols], height=500, use_container_width=True)








# 6. Tabla Completa del CSV
with tabs[5]:  # Nueva pestaña en la posición 6
    st.subheader("📋 Tabla Completa del CSV")

    # Descripción
    st.markdown("""
    🔍 **Descripción:**  
    Esta sección permite visualizar la tabla completa del archivo CSV cargado.  
    Puedes buscar un término específico para filtrar los registros y encontrar información rápidamente.
    """)

    # Campo de búsqueda
    search_query = st.text_input("🔎 Buscar en la tabla:", "")

    # Si hay un término de búsqueda, filtrar en todas las columnas
    if search_query:
        df_filtered = df[df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False)).any(axis=1)]
    else:
        df_filtered = df.copy()

    # Mostrar la tabla completa con scroll
    st.write("### 📊 Datos Filtrados")
    st.dataframe(df_filtered, height=500, use_container_width=True)