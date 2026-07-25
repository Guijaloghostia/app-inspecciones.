import streamlit as st
import pandas as pd

st.set_page_config(page_title="Refiscalización", layout="wide")

st.title("📋 Control de Inspecciones")
st.write("Subí el archivo Excel para ver los rankings actualizados.")

uploaded_file = st.file_uploader("Cargar archivo Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name='TOTAL', engine='openpyxl')
        df.columns = df.columns.str.strip()

        for col in ['TREL', 'TNR', 'TRAI']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['Calle'] = df['Calle'].astype(str).str.strip()
        df['Núm_Clean'] = df['Núm.'].fillna('').astype(str).str.replace('.0', '', regex=False).str.strip()
        df['Direccion_Corta'] = df['Calle'] + " " + df['Núm_Clean']

        if 'Fecha' in df.columns:
            df['Fecha_Clean'] = pd.to_datetime(df['Fecha'], errors='coerce')
        else:
            df['Fecha_Clean'] = pd.NaT

        resumen = df.groupby('Direccion_Corta').agg(
            Cant_Inspecciones=('Calle', 'count'),
            Total_TREL=('TREL', 'sum'),
            Total_TNR=('TNR', 'sum'),
            Ultima_Inspeccion=('Fecha_Clean', 'max')
        ).reset_index()

        resumen['% Informalidad'] = ((resumen['Total_TNR'] / resumen['Total_TREL'].replace(0, 1)) * 100).round(1)

        st.subheader("🔴 Prioridad: Menos Inspeccionados / Antiguos")
        menos_insp = resumen.sort_values(by=['Cant_Inspecciones', 'Ultima_Inspeccion'], ascending=[True, True])
        st.dataframe(menos_insp, use_container_width=True)

        st.subheader("🟢 Locales Más Inspeccionados")
        mas_insp = resumen.sort_values(by='Cant_Inspecciones', ascending=False)
        st.dataframe(mas_insp, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
