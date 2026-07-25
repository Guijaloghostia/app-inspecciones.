import streamlit as st
import pandas as pd

st.set_page_config(page_title="Control de Refiscalización", layout="wide")

st.title("📊 Panel Interactivo de Refiscalización")
st.write("Subí el archivo Excel para activar los tableros de control.")

uploaded_file = st.file_uploader("Cargar archivo Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name='TOTAL', engine='openpyxl')
        df.columns = df.columns.str.strip()

        # Limpieza de columnas numéricas existentes
        for col in ['TREL', 'TNR', 'TRAI', 'Latitud', 'Longitud']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['Calle'] = df['Calle'].astype(str).str.strip()
        df['Núm_Clean'] = df['Núm.'].fillna('').astype(str).str.replace('.0', '', regex=False).str.strip()
        df['Direccion_Corta'] = df['Calle'] + " " + df['Núm_Clean']

        if 'Fecha' in df.columns:
            df['Fecha_Clean'] = pd.to_datetime(df['Fecha'], errors='coerce')
        else:
            df['Fecha_Clean'] = pd.NaT

        # Definir agregaciones seguras según las columnas disponibles
        agg_dict = {
            'Cant_Inspecciones': ('Calle', 'count'),
            'Total_TREL': ('TREL', 'sum') if 'TREL' in df.columns else ('Calle', 'count'),
            'Total_TNR': ('TNR', 'sum') if 'TNR' in df.columns else ('Calle', 'count'),
            'Ultima_Inspeccion': ('Fecha_Clean', 'max')
        }

        if 'Latitud' in df.columns:
            agg_dict['Latitud'] = ('Latitud', 'mean')
        if 'Longitud' in df.columns:
            agg_dict['Longitud'] = ('Longitud', 'mean')

        resumen = df.groupby('Direccion_Corta').agg(**agg_dict).reset_index()

        resumen['% Informalidad'] = ((resumen['Total_TNR'] / resumen['Total_TREL'].replace(0, 1)) * 100).round(1)

        # --- SECCIÓN 1: METRICAS CLAVE ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Locales", len(resumen))
        col2.metric("Total Inspecciones", resumen['Cant_Inspecciones'].sum())
        col3.metric("Prom. Informalidad", f"{resumen['% Informalidad'].mean():.1f}%")
        col4.metric("Locales Críticos (>50% Inf.)", len(resumen[resumen['% Informalidad'] > 50]))

        st.divider()

        # --- SECCIÓN 2: FILTROS INTERACTIVOS ---
        st.sidebar.header("🔍 Filtros de Búsqueda")
        
        filtro_calle = st.sidebar.text_input("Buscar por Calle / Dirección:")
        min_insp, max_insp = st.sidebar.slider(
            "Rango de Inspecciones:",
            int(resumen['Cant_Inspecciones'].min()),
            int(resumen['Cant_Inspecciones'].max()),
            (int(resumen['Cant_Inspecciones'].min()), int(resumen['Cant_Inspecciones'].max()))
        )

        # Aplicar filtros
        df_filtrado = resumen[
            (resumen['Cant_Inspecciones'] >= min_insp) & 
            (resumen['Cant_Inspecciones'] <= max_insp)
        ]
        if filtro_calle:
            df_filtrado = df_filtrado[df_filtrado['Direccion_Corta'].str.contains(filtro_calle, case=False, na=False)]

        # --- SECCIÓN 3: MAPA INTERACTIVO (SOLO SI EXISTEN COORDENADAS) ---
        if 'Latitud' in df_filtrado.columns and 'Longitud' in df_filtrado.columns:
            try:
                import folium
                from folium.plugins import HeatMap
                from streamlit_folium import st_folium

                st.subheader("🗺️ Mapa de Calor de Inspecciones / Informalidad")
                map_data = df_filtrado[(df_filtrado['Latitud'] != 0) & (df_filtrado['Longitud'] != 0)]

                if not map_data.empty:
                    centro_lat = map_data['Latitud'].mean()
                    centro_lon = map_data['Longitud'].mean()
                    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13)
                    heat_data = [[row['Latitud'], row['Longitud'], row['% Informalidad']] for _, row in map_data.iterrows()]
                    HeatMap(heat_data, radius=15).add_to(m)
                    st_folium(m, width=1000, height=450)
                else:
                    st.info("ℹ️ No hay coordenadas válidas para mostrar en el mapa.")
            except ImportError:
                st.info("ℹ️ Para habilitar el mapa, asegurate de tener 'folium' en requirements.txt.")
        else:
            st.info("ℹ️ Para mostrar el mapa de calor, el Excel debe incluir las columnas 'Latitud' y 'Longitud'.")

        st.divider()

        # --- SECCIÓN 4: TABLAS INTERACTIVAS ---
        tab1, tab2 = st.tabs(["🔴 Prioridad de Control (Menos Inspeccionados)", "🟢 Ranking de Inspeccionados"])

        with tab1:
            st.dataframe(
                df_filtrado.sort_values(by=['Cant_Inspecciones', 'Ultima_Inspeccion'], ascending=[True, True]),
                use_container_width=True
            )

        with tab2:
            st.dataframe(
                df_filtrado.sort_values(by='Cant_Inspecciones', ascending=False),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
