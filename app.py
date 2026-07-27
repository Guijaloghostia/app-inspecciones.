import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Control de Refiscalización", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
        /* Agranda el texto de los elementos de la barra lateral / menú */
        [data-testid="stSidebar"] * {
            font-size: 20px !important;
        }

        /* Agranda los títulos del menú */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            font-size: 24px !important;
        }

        /* Agranda los botones de la barra lateral y de la app */
        .stButton button {
            font-size: 18px !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)



# --- ESTILOS CSS INTERACTIVOS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #d9534f;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .stButton>button {
        width: 100%;
        background-color: #d9534f;
        color: white;
        border-radius: 6px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

DEFAULT_FILE = "1 - BASE PARA REFISCALIZAR 1er Y 2do TRIMESTRE 2025 cruzado al 3-9-25.xlsx"

# --- NAVEGACIÓN PRINCIPAL ---
st.sidebar.title("📌 Menú Principal")
opcion = st.sidebar.radio("Ir a:", [
    "🏠 Dashboard General",
    "🛣️ Análisis por Calle / Cuadra",
    "🔍 Consultar Ficha por Local",
    "🔴 Tablero de Prioridades",
    "🗺️ Mapa de Control",
    "⚙️ Carga y Configuración"
])

# --- FUNCIÓN CARGA DE DATOS ---
@st.cache_data
def cargar_datos(file_path):
    df = pd.read_excel(file_path, sheet_name='TOTAL', engine='openpyxl')
    df.columns = df.columns.str.strip()
    
    for col in ['TREL', 'TNR', 'TRAI', 'Latitud', 'Longitud']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Calle'] = df['Calle'].astype(str).str.strip()
    
    # Extraer la altura numérica para calcular la cuadra (altura al 100)
    if 'Núm.' in df.columns:
        df['Num_Val'] = pd.to_numeric(df['Núm.'], errors='coerce').fillna(0).astype(int)
        df['Cuadra'] = (df['Num_Val'] // 100) * 100
        df['Cuadra_Texto'] = df['Calle'] + " al " + df['Cuadra'].astype(str)
        df['Núm_Clean'] = df['Núm.'].fillna('').astype(str).str.replace('.0', '', regex=False).str.strip()
        df['Direccion_Corta'] = df['Calle'] + " " + df['Núm_Clean']
    else:
        df['Cuadra_Texto'] = df['Calle']
        df['Direccion_Corta'] = df['Calle']

    if 'Fecha' in df.columns:
        df['Fecha_Clean'] = pd.to_datetime(df['Fecha'], errors='coerce')
    else:
        df['Fecha_Clean'] = pd.NaT

    agg_dict = {
        'Calle_Nombre': ('Calle', 'first'),
        'Cuadra_Texto': ('Cuadra_Texto', 'first'),
        'Cant_Inspecciones': ('Calle', 'count'),
        'Total_TREL': ('TREL', 'sum') if 'TREL' in df.columns else ('Calle', 'count'),
        'Total_TNR': ('TNR', 'sum') if 'TNR' in df.columns else ('Calle', 'count'),
        'Ultima_Inspeccion': ('Fecha_Clean', 'max')
    }

    if 'Latitud' in df.columns: agg_dict['Latitud'] = ('Latitud', 'mean')
    if 'Longitud' in df.columns: agg_dict['Longitud'] = ('Longitud', 'mean')

    resumen = df.groupby('Direccion_Corta').agg(**agg_dict).reset_index()
    resumen['% Informalidad'] = ((resumen['Total_TNR'] / resumen['Total_TREL'].replace(0, 1)) * 100).round(1)
    
    # Semáforo de Prioridad
    def asignar_prioridad(row):
        if row['Cant_Inspecciones'] == 1 and row['% Informalidad'] > 50:
            return "🔴 ALTA (1 sola insp. y alta inf.)"
        elif row['Cant_Inspecciones'] <= 2:
            return "🟡 MEDIA (1-2 inspecciones)"
        else:
            return "🟢 BAJA (3+ inspecciones - Evitar)"
            
    resumen['Prioridad'] = resumen.apply(asignar_prioridad, axis=1)
    return df, resumen

df_raw, resumen = None, None

if os.path.exists(DEFAULT_FILE):
    try:
        df_raw, resumen = cargar_datos(DEFAULT_FILE)
    except Exception as e:
        st.error(f"Error cargando base: {e}")

if resumen is not None:

    # --- SECCIÓN 1: DASHBOARD GENERAL ---
    if opcion == "🏠 Dashboard General":
        st.title("📊 Panel de Control e Inspecciones")
        st.caption("Visión sintética de la tasa de informalidad e inspecciones en calle.")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Locales", len(resumen))
        c2.metric("Total Inspecciones", resumen['Cant_Inspecciones'].sum())
        c3.metric("Prom. Informalidad", f"{resumen['% Informalidad'].mean():.1f}%")
        c4.metric("Urgentes Refiscalizar", len(resumen[resumen['Prioridad'].str.contains("ALTA")]))

        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Distribución por Cantidad de Inspecciones")
            st.bar_chart(resumen['Prioridad'].value_counts())
        with col_right:
            st.subheader("Top 10 Zonas con Mayor Informalidad")
            top_inf = resumen.sort_values(by='% Informalidad', ascending=False).head(10)
            st.dataframe(top_inf[['Direccion_Corta', '% Informalidad', 'Cant_Inspecciones']], use_container_width=True)

    # --- SECCIÓN NUEVA: ANÁLISIS POR CALLE / CUADRA ---
    elif opcion == "🛣️ Análisis por Calle / Cuadra":
        st.title("🛣️ Control por Calle y Cuadras")
        st.write("Identificá qué cuadras o calles tienen sobreinspección y cuáles faltan recorrer.")

        lista_calles = sorted([c for c in resumen['Calle_Nombre'].unique() if str(c).strip() != ''])
        calle_sel = st.selectbox("Seleccioná o buscá una Calle:", [""] + lista_calles)

        if calle_sel:
            df_calle = resumen[resumen['Calle_Nombre'].str.upper() == calle_sel.upper()]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Calle", calle_sel)
            m2.metric("Total Locales", len(df_calle))
            m3.metric("Total Inspecciones en la Calle", df_calle['Cant_Inspecciones'].sum())
            m4.metric("Prom. Inspecciones por Local", f"{(df_calle['Cant_Inspecciones'].sum() / len(df_calle)):.1f}")

            st.divider()

            col_cuadra, col_locales = st.columns([1, 1.2])

            with col_cuadra:
                st.subheader("📌 Inspecciones por Cuadra (Altura)")
                resumen_cuadra = df_calle.groupby('Cuadra_Texto').agg(
                    Locales=('Direccion_Corta', 'count'),
                    Inspecciones=('Cant_Inspecciones', 'sum'),
                    Prom_Informalidad=('% Informalidad', 'mean')
                ).reset_index().sort_values(by='Inspecciones', ascending=False)
                
                st.dataframe(resumen_cuadra, use_container_width=True)

            with col_locales:
                st.subheader("🏪 Locales de la Calle (Ordenados por Inspección)")
                filtro_cant = st.radio("Mostrar:", ["Todos", "Solo 1 inspección (Prioridad)", "2 o más inspecciones (Evitar/Analizar)"], horizontal=True)

                df_mostrar = df_calle.copy()
                if filtro_cant == "Solo 1 inspección (Prioridad)":
                    df_mostrar = df_mostrar[df_mostrar['Cant_Inspecciones'] == 1]
                elif filtro_cant == "2 o más inspecciones (Evitar/Analizar)":
                    df_mostrar = df_mostrar[df_mostrar['Cant_Inspecciones'] >= 2]

                st.dataframe(
                    df_mostrar[['Direccion_Corta', 'Cant_Inspecciones', '% Informalidad', 'Prioridad']].sort_values(by='Cant_Inspecciones', ascending=True),
                    use_container_width=True
                )

    # --- SECCIÓN 3: CONSULTAR FICHA POR LOCAL ---
    elif opcion == "🔍 Consultar Ficha por Local":
        st.title("🔍 Buscador Interactivo de Comercio")
        
        busqueda = st.selectbox("Seleccioná o buscá una dirección exacta:", [""] + list(resumen['Direccion_Corta'].unique()))
        
        if busqueda:
            local = resumen[resumen['Direccion_Corta'] == busqueda].iloc[0]
            st.success(f"📍 Ficha de Local: **{local['Direccion_Corta']}**")
            
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Cant. Inspecciones", local['Cant_Inspecciones'])
            f2.metric("Informalidad", f"{local['% Informalidad']}%")
            f3.metric("Última Inspección", str(local['Ultima_Inspeccion'])[:10] if pd.notnull(local['Ultima_Inspeccion']) else "S/D")
            f4.metric("Estado", local['Prioridad'].split(" ")[0])

            st.divider()
            st.subheader("📋 Historial de Inspecciones Registradas")
            historial = df_raw[df_raw['Direccion_Corta'] == busqueda]
            st.dataframe(historial, use_container_width=True)

    # --- SECCIÓN 4: TABLERO DE PRIORIDADES ---
    elif opcion == "🔴 Tablero de Prioridades":
        st.title("🔴 Tablero de Refiscalización Prioritaria")
        
        prio_filtro = st.multiselect(
            "Filtrar por Nivel de Prioridad:",
            options=list(resumen['Prioridad'].unique()),
            default=list(resumen['Prioridad'].unique())
        )
        
        res_filtrado = resumen[resumen['Prioridad'].isin(prio_filtro)]
        st.dataframe(
            res_filtrado.sort_values(by=['Cant_Inspecciones', '% Informalidad'], ascending=[True, False]),
            use_container_width=True
        )

    # --- SECCIÓN 5: MAPA DE CONTROL ---
    elif opcion == "🗺️ Mapa de Control":
        st.title("🗺️ Ubicación de Inspecciones")
        if 'Latitud' in resumen.columns and 'Longitud' in resumen.columns:
            try:
                import folium
                from folium.plugins import HeatMap
                from streamlit_folium import st_folium

                map_data = resumen[(resumen['Latitud'] != 0) & (resumen['Longitud'] != 0)]
                if not map_data.empty:
                    m = folium.Map(location=[map_data['Latitud'].mean(), map_data['Longitud'].mean()], zoom_start=13)
                    heat_data = [[r['Latitud'], r['Longitud'], r['% Informalidad']] for _, r in map_data.iterrows()]
                    HeatMap(heat_data, radius=15).add_to(m)
                    st_folium(m, width=1000, height=500)
                else:
                    st.info("No hay coordenadas para graficar en el mapa.")
            except ImportError:
                st.warning("Instalá folium y streamlit-folium para ver el mapa.")
        else:
            st.info("El archivo actual no posee datos de Latitud y Longitud.")

    # --- SECCIÓN 6: CARGA Y CONFIGURACIÓN ---
    elif opcion == "⚙️ Carga y Configuración":
        st.title("⚙️ Carga y Actualización de Archivos")
        up = st.file_uploader("Subí un nuevo Excel para actualizar el sistema", type=["xlsx", "xls"])
        if up is not None:
            st.success("Archivo subido correctamente. Para reemplazar el predeterminado, guardalo en GitHub.")
else:
    st.warning("Esperando carga de base de datos...")
