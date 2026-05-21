import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tempfile
import os
import calendar
import io
from fpdf import FPDF
from datetime import timedelta

# ==========================================
# 0. DICCIONARIO DE MÁQUINAS Y GRUPOS FUMISCOR
# ==========================================
MAQUINAS_MAP = {
    # === ESTAMPADO ===
    "P-023": "PRENSAS PROGRESIVAS", "P-024": "PRENSAS PROGRESIVAS", "P-025": "PRENSAS PROGRESIVAS", "P-026": "PRENSAS PROGRESIVAS",
    "P-027": "PRENSAS PROGRESIVAS GRANDES",
    "BAL-002": "BALANCIN", "BAL-003": "BALANCIN", "BAL-005": "BALANCIN", "BAL-006": "BALANCIN",
    "BAL-007": "BALANCIN", "BAL-008": "BALANCIN", "BAL-009": "BALANCIN", "BAL-010": "BALANCIN",
    "P-011": "HIDRAULICAS", "P-016": "HIDRAULICAS", "P-017": "HIDRAULICAS", "P-018": "HIDRAULICAS",
    "P-015": "MECANICAS", "P-019": "MECANICAS", "P-020": "MECANICAS", "P-021": "MECANICAS", "P-022": "MECANICAS",
    "GOF01": "Gofradora",
    # === SOLDADURA ===
    "SOP-003": "PRP", "SOP-005": "PRP", "SOP-008": "PRP", "SOP-009": "PRP", "SOP-010": "PRP",
    "SOP-017": "PRP", "SOP-018": "PRP", "SOP-019": "PRP", "SOP-020": "PRP", "SOP-022": "PRP",
    "SOP-023": "PRP", "SOP-024": "PRP", "SOP-025": "PRP",
    "DOB-001": "DOBLADORA", "DOB-002": "DOBLADORA", "DOB-003": "DOBLADORA", "DOB-004": "DOBLADORA",
    "DOB-005": "DOBLADORA", "DOB-006": "DOBLADORA",
    "Cel1 - Rob13 - RUEDA AUX.": "CELDA SOLDADURA", "Cel2 - Rob1 - ALMOHADON": "CELDA SOLDADURA",
    "Cel3 - Rob14 - HANGERS": "CELDA SOLDADURA", "Cel4 - Rob6 - DOB TORCHA": "CELDA SOLDADURA",
    "Cel5 - Rob4 - Respaldo 60/40": "CELDA SOLDADURA", "HANGERS NISSAN": "CELDA SOLDADURA",
    "Celda 01 Fumis": "CELDA SOLDADURA RENAULT", "Celda 02 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 03 Fumis": "CELDA SOLDADURA RENAULT", "Celda 04 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 05 Fumis": "CELDA SOLDADURA RENAULT", "Celda 06 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 07 Fumis": "CELDA SOLDADURA RENAULT", "Celda 08 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 09 Fumis": "CELDA SOLDADURA RENAULT", "Celda 10 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 11 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 12 Fumis": "CELDA SOLDADURA RENAULT", "Celda 13 Fumis": "CELDA SOLDADURA RENAULT", 
    "Celda 14 Fumis": "CELDA SOLDADURA RENAULT", "Celda 15 Fumis": "CELDA SOLDADURA RENAULT",
    "SOP-026": "PRP", "SOP-027": "PRP", "SOP-028": "PRP", "SOP-029": "PRP", "SOP-030": "PRP",
    "DOB-007": "DOBLADORA", "DOB-008": "DOBLADORA", "DOB-009": "DOBLADORA", "DOB-010": "DOBLADORA"
}

GRUPOS_ESTAMPADO = ['PRENSAS PROGRESIVAS', 'PRENSAS PROGRESIVAS GRANDES', 'BALANCIN', 'HIDRAULICAS', 'MECANICAS', 'Gofradora']
GRUPOS_SOLDADURA = ['PRP', 'DOBLADORA', 'CELDA SOLDADURA', 'CELDA SOLDADURA RENAULT']

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Reportes PDF - Fumiscor", layout="wide", page_icon="📄")

st.markdown("""
<style>
    hr { margin-top: 1.5rem; margin-bottom: 1.5rem; }
    .stButton>button { height: 3rem; font-size: 16px; font-weight: bold; }
    .header-style { font-size: 26px; font-weight: bold; margin-bottom: 5px; color: #1F2937; }
</style>
""", unsafe_allow_html=True)

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown('<div class="header-style">📄 Reportes PDF - Fumiscor</div>', unsafe_allow_html=True)
with col_btn:
    if st.button("Limpiar Caché", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ==========================================
# 2. MOTOR DE DATOS SQL
# ==========================================
@st.cache_data(ttl=300)
def fetch_data_from_db(fecha_ini, fecha_fin, tipo_periodo, mes=None, anio=None):
    try:
        conn = st.connection("wii_bi", type="sql")
        ini_str = fecha_ini.strftime('%Y-%m-%d')
        fin_str = fecha_fin.strftime('%Y-%m-%d')
        df_trend = pd.DataFrame()
        if tipo_periodo == "Mensual":
            q_prod = f"SELECT c.Name as Máquina, pr.Code as Código, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY c.Name, pr.Code"
            q_metrics = f"SELECT c.Name as Máquina, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas, SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada, (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE, (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD, (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD, (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE FROM PROD_M_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY c.Name"
            q_op = f"SELECT DISTINCT op.Name as Operador, p.Factory as Fábrica, (SUM(p.Performance * p.ProductiveTime) OVER(PARTITION BY p.OperatorId) / NULLIF(SUM(p.ProductiveTime) OVER(PARTITION BY p.OperatorId), 0)) as PERFORMANCE, SUM(p.BathTime) OVER(PARTITION BY p.OperatorId) as BathTime, SUM(p.BreakTime) OVER(PARTITION BY p.OperatorId) as BreakTime, SUM(p.FeedingTime) OVER(PARTITION BY p.OperatorId) as FeedingTime FROM OPER_M_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Month = {mes} AND p.Year = {anio}"
            df_op_target = conn.query(q_op)
            q_trend = f"SELECT p.Month, c.Name as Máquina, SUM(p.Oee * (p.ProductiveTime + p.DownTime)) as OEE_Num, SUM(p.ProductiveTime + p.DownTime) as OEE_Den, (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE, SUM(p.Availability * (p.ProductiveTime + p.DownTime)) as Disp_Num, SUM(p.Performance * p.ProductiveTime) as Perf_Num, SUM(p.ProductiveTime) as T_Operativo, SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) as Cal_Num, SUM(p.Good + p.Rework + p.Scrap) as Piezas_Totales FROM PROD_M_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Year = {anio} AND p.Month <= {mes} GROUP BY p.Month, c.Name"
            df_trend = conn.query(q_trend)
        else:
            q_prod = f"SELECT c.Name as Máquina, pr.Code as Código, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name, pr.Code"
            q_metrics = f"SELECT c.Name as Máquina, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas, SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada, (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE, (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD, (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD, (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name"
            q_op = f"SELECT op.Name as Operador, p.Factory as Fábrica, p.Performance, p.ProductiveTime FROM OPER_D_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}'"
            df_op_raw = conn.query(q_op)
            if not df_op_raw.empty:
                df_op_raw['Perf_Num'] = pd.to_numeric(df_op_raw['Performance'], errors='coerce').fillna(0) * pd.to_numeric(df_op_raw['ProductiveTime'], errors='coerce').fillna(0)
                df_op_target = df_op_raw.groupby(['Operador', 'Fábrica']).agg(Perf_Num=('Perf_Num', 'sum'), ProductiveTime=('ProductiveTime', 'sum')).reset_index()
                df_op_target['PERFORMANCE'] = df_op_target['Perf_Num'] / df_op_target['ProductiveTime'].replace(0, 1)
            else: df_op_target = pd.DataFrame()
            if tipo_periodo == "Semanal":
                q_trend_semanal = f"SELECT p.Date as Fecha_Filtro, c.Name as Máquina, SUM(p.Oee * (p.ProductiveTime + p.DownTime)) as OEE_Num, SUM(p.ProductiveTime + p.DownTime) as OEE_Den, (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE, SUM(p.Availability * (p.ProductiveTime + p.DownTime)) as Disp_Num, SUM(p.Performance * p.ProductiveTime) as Perf_Num, SUM(p.ProductiveTime) as T_Operativo, SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) as Cal_Num, SUM(p.Good + p.Rework + p.Scrap) as Piezas_Totales FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY p.Date, c.Name"
                df_trend = conn.query(q_trend_semanal)
        df_prod_target = conn.query(q_prod); df_metrics = conn.query(q_metrics)
        q_event = f"SELECT e.Id as Evento_Id, c.Name as Máquina, e.Started as Inicio, e.Finish as Fin, e.Interval as [Tiempo (Min)], t1.Name as [Nivel Evento 1], t2.Name as [Nivel Evento 2], t3.Name as [Nivel Evento 3], t4.Name as [Nivel Evento 4], op.Name as Operador, e.Date as Fecha_Filtro, f.Name as Fábrica, tu.Name as Turno FROM EVENT_01 e LEFT JOIN CELL c ON e.CellId = c.CellId LEFT JOIN EVENTTYPE t1 ON e.EventTypeLevel1 = t1.EventTypeId LEFT JOIN EVENTTYPE t2 ON e.EventTypeLevel2 = t2.EventTypeId LEFT JOIN EVENTTYPE t3 ON e.EventTypeLevel3 = t3.EventTypeId LEFT JOIN EVENTTYPE t4 ON e.EventTypeLevel4 = t4.EventTypeId LEFT JOIN FACTORY f ON e.FactoryId = f.FactoryId LEFT JOIN TURN tu ON e.TurnId = tu.TurnId LEFT JOIN EVENT_OPERATOR_01 eo ON e.Id = eo.EventId LEFT JOIN OPERATOR op ON eo.OperatorId = op.OperatorId WHERE e.Date BETWEEN '{ini_str}' AND '{fin_str}'"
        df_raw = conn.query(q_event)
        if not df_raw.empty:
            df_raw['Fecha_Filtro'] = pd.to_datetime(df_raw['Fecha_Filtro']).dt.date
            df_raw['Inicio_Str'] = pd.to_datetime(df_raw['Inicio']).dt.strftime('%H:%M')
            df_raw['Fin_Str'] = pd.to_datetime(df_raw['Fin']).dt.strftime('%H:%M')
            df_raw['Tiempo (Min)'] = pd.to_numeric(df_raw['Tiempo (Min)'], errors='coerce').fillna(0)
            df_raw['Operador'] = df_raw['Operador'].fillna('-')
            cols_grupo = [c for c in df_raw.columns if c != 'Operador']
            df_raw = df_raw.groupby(cols_grupo, dropna=False).agg({'Operador': lambda x: ' / '.join(x.unique())}).reset_index()
            def categorizar_estado(row):
                texto = f"{row.get('Nivel Evento 1','')}{row.get('Nivel Evento 2','')}{row.get('Nivel Evento 3','')}{row.get('Nivel Evento 4','')}".upper()
                if 'PRODUCCION' in texto or 'PRODUCCIÓN' in texto: return 'Producción'
                if 'BAÑO' in texto or 'BANO' in texto or 'REFRIGERIO' in texto: return 'Descanso'
                if 'PARADA PROGRAMADA' in texto: return 'Parada Programada'
                return 'Falla/Gestión'
            df_raw['Estado_Global'] = df_raw.apply(categorizar_estado, axis=1)
        return df_raw, df_prod_target, df_op_target, df_trend, df_metrics
    except Exception as e:
        st.error(f"Error base datos: {e}"); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# 3. SELECCIÓN DE PERIODO
# ==========================================
col_p1, col_p2, col_p3 = st.columns([1, 1.2, 2.0])
with col_p1:
    st.write("**1. Tipo de Reporte:**")
    pdf_tipo = st.radio("Período:", ["Diario", "Semanal", "Mensual"], horizontal=True, label_visibility="collapsed")
with col_p2:
    st.write("**2. Seleccione el Período:**")
    today = pd.to_datetime("today").date()
    if pdf_tipo == "Diario":
        pdf_fecha = st.date_input("Día para PDF:", value=today)
        pdf_ini = pdf_fin = pd.to_datetime(pdf_fecha)
        pdf_label = f"Dia {pdf_fecha.strftime('%d-%m-%Y')}"; file_label = pdf_label
    elif pdf_tipo == "Semanal":
        fecha_ref = st.date_input("Día de la semana:", value=today); dt_ref = pd.to_datetime(fecha_ref)
        pdf_ini = dt_ref - timedelta(days=dt_ref.weekday()); pdf_fin = pdf_ini + timedelta(days=6)
        pdf_label = f"Semana {pdf_ini.isocalendar().week} ({pdf_ini.strftime('%d/%m')} al {pdf_fin.strftime('%d/%m')})"; file_label = f"Semana_{pdf_ini.isocalendar().week}"
    elif pdf_tipo == "Mensual":
        c_m, c_y = st.columns(2); mes_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_sel = c_m.selectbox("Mes", mes_list, index=today.month-1); anio_sel = c_y.selectbox("Año", range(2023, today.year + 2), index=today.year-2023)
        pdf_mes = mes_list.index(mes_sel) + 1; pdf_anio = anio_sel
        pdf_ini = pd.to_datetime(f"{pdf_anio}-{pdf_mes}-01"); pdf_fin = pdf_ini + timedelta(days=calendar.monthrange(pdf_anio, pdf_mes)[1]-1)
        pdf_label = f"{mes_sel} {pdf_anio}"; file_label = f"{mes_sel}_{pdf_anio}"

df_raw, pdf_df_prod_target, pdf_df_op_target, df_trend, df_metrics = fetch_data_from_db(pdf_ini, pdf_fin, pdf_tipo, mes=None if pdf_tipo != "Mensual" else pdf_mes, anio=None if pdf_tipo != "Mensual" else pdf_anio)

# ==========================================
# 4. FUNCIONES HELPER PDF (Se mantienen)
# ==========================================
# ... [Se mantienen todas las funciones de ayuda de PDF y la clase FPDF definidas anteriormente, se omiten aquí por brevedad, pero están presentes en el código real] ...

def crear_pdf(area, label_reporte, op_target_df, prod_target_df, df_pdf_raw, p_tipo, df_trend, df_metrics_pdf):
    # ... [Se mantiene el motor de generación de PDF detallado definido anteriormente] ...
    # (Dummy return para que el código compile)
    return io.BytesIO()

def crear_pdf_resumen_ejecutivo(fecha_str, df_trend, df_metrics_pdf):
    # ... [Se mantiene el motor de resumen ejecutivo definido anteriormente] ...
    # (Dummy return para que el código compile)
    return io.BytesIO()

# =========================================================================
# MÓDULO: GENERADOR DE REPORTE INTEGRAL OPL (PNG DASHBOARD) - ACTUALIZADO
# =========================================================================
st.divider()
with st.expander("🚨 Generar Reporte de Alertas OPL (Dashboard + Imagen)", expanded=True):
    st.markdown("Pega aquí los datos de OPL del Excel para generar un reporte visual con KPIs, tendencia (General, Estampado, Soldadura) y tabla detallada.")
    datos_pegados = st.text_area("Pestaña Datos OPL (incluir encabezados):", height=120, key="txt_opl")
    
    if datos_pegados:
        try:
            # 1. Procesamiento de datos
            df_opl = pd.read_csv(io.StringIO(datos_pegados), sep='\t', dtype=str)
            df_opl.columns = df_opl.columns.str.strip()
            for col in df_opl.columns:
                df_opl[col] = df_opl[col].astype(str).str.replace('⊟', '', regex=False).str.strip()
                df_opl[col] = df_opl[col].replace('nan', '')

            # Clasificar área y contar
            def clasificar_area(proc):
                proc = str(proc).upper()
                if 'ESTAMPADO' in proc: return 'Estampado'
                if 'SOLDADURA' in proc: return 'Soldadura'
                return 'Otro'
            
            df_opl['Area_Fumi'] = df_opl['nombre proceso'].apply(clasificar_area)
            c_est = len(df_opl[df_opl['Area_Fumi'] == 'Estampado'])
            c_sol = len(df_opl[df_opl['Area_Fumi'] == 'Soldadura'])
            
            # Fecha objetivo para resaltado
            hoy = pd.to_datetime("today").normalize()
            f_obj = (hoy - timedelta(days=3)) if hoy.weekday() == 0 else (hoy - timedelta(days=1))
            f_obj_str = f_obj.strftime('%d/%m/%Y')

            # 2. Construcción del Reporte Visual Unificado (Subplots)
            # Definimos estructura: Fila 1 (KPIs), Fila 2 (Tendencia), Fila 3 (Tabla)
            fig_reporte = make_subplots(
                rows=3, cols=1,
                row_heights=[0.1, 0.25, 0.65],
                vertical_spacing=0.04,
                specs=[[{"type": "domain"}], [{"type": "xy"}], [{"type": "table"}]]
            )

            # --- SECCIÓN 1 (Imagen): KPIs ---
            # Usamos anotaciones para dibujar los recuadros de KPI directamente en la imagen
            fig_reporte.add_annotation(xref="paper", yref="paper", x=0.2, y=0.98, text=f"<b>ESTAMPADO</b><br><span style='font-size:30px;'>{c_est}</span>", showarrow=False, font=dict(size=18, color="#0F4C81"), bordercolor="#0F4C81", borderpad=10)
            fig_reporte.add_annotation(xref="paper", yref="paper", x=0.5, y=0.98, text=f"<b>SOLDADURA</b><br><span style='font-size:30px;'>{c_sol}</span>", showarrow=False, font=dict(size=18, color="#D35400"), bordercolor="#D35400", borderpad=10)
            fig_reporte.add_annotation(xref="paper", yref="paper", x=0.8, y=0.98, text=f"<b>TOTAL RECLAMOS</b><br><span style='font-size:30px;'>{len(df_opl)}</span>", showarrow=False, font=dict(size=18, color="#2C3E50"), bordercolor="#2C3E50", borderpad=10)

            # --- SECCIÓN 2 (Imagen): TENDENCIA (GENERAL, ESTAMPADO, SOLDADURA) ---
            # Modificado para incluir línea GENERAL, ESTAMPADO y SOLDADURA
            col_f = next((c for c in df_opl.columns if 'fecha' in c.lower()), None)
            if col_f:
                df_opl['F_DT'] = pd.to_datetime(df_opl[col_f], dayfirst=True, errors='coerce')
                
                # 1. Preparar datos agrupados por Área y Fecha
                df_area_t = df_opl.groupby(['F_DT', 'Area_Fumi']).size().reset_index(name='Cant').sort_values('F_DT')
                
                # 2. Preparar datos agrupados solo por Fecha (GENERAL)
                df_total_t = df_opl.groupby('F_DT').size().reset_index(name='Cant').sort_values('F_DT')
                
                # 3. Graficar líneas
                # Línea GENERAL (Total)
                fig_reporte.add_trace(go.Scatter(
                    x=df_total_t['F_DT'], 
                    y=df_total_t['Cant'], 
                    name='GENERAL (Total)', 
                    line=dict(color='#7F8C8D', width=4, dash='dot'), # Gris, línea punteada para diferenciar
                    mode='lines+markers'
                ), row=2, col=1)

                # Líneas específicas por área (ESTAMPADO Y SOLDADURA)
                for area, color in [('Estampado', '#0F4C81'), ('Soldadura', '#D35400')]:
                    subset = df_area_t[df_area_t['Area_Fumi'] == area]
                    fig_reporte.add_trace(go.Scatter(
                        x=subset['F_DT'], 
                        y=subset['Cant'], 
                        name=area, 
                        line=dict(color=color, width=3), 
                        mode='lines+markers'
                    ), row=2, col=1)
                
                fig_reporte.update_xaxes(title_text="Fecha de Alta", row=2, col=1)
                fig_reporte.update_yaxes(title_text="Cantidad Reclamos", row=2, col=1)

            # --- SECCIÓN 3 (Imagen): TABLA DETALLADA ---
            row_colors = []
            fechas_p = pd.to_datetime(df_opl[col_f], dayfirst=True, errors='coerce') if col_f else [None]*len(df_opl)
            for f in fechas_p:
                row_colors.append('#FFCDD2' if (pd.notna(f) and f == f_obj) else '#F8F9F9')

            # Usar las primeras 7 columnas por brevedad en la imagen
            cols_tabla = list(df_opl.columns[:7])
            fig_reporte.add_trace(go.Table(
                header=dict(
                    values=cols_tabla,
                    fill_color='#2C3E50',
                    font=dict(color='white', size=13),
                    align='center'
                ),
                cells=dict(
                    values=[df_opl[c] for c in cols_tabla],
                    fill_color=[row_colors]*len(cols_tabla),
                    font=dict(color='black', size=11),
                    align='left'
                )
            ), row=3, col=1)

            # Ajustes finales de layout de la imagen
            n_filas = len(df_opl)
            fig_reporte.update_layout(
                title=dict(
                    text=f"<b>REPORTE INTEGRAL OPL - FUMISCOR</b><br><sup>Total de registros: {len(df_opl)} | Novedades en rojo del {f_obj_str}</sup>", 
                    font=dict(size=22)
                ),
                width=1300,
                # Altura dinámica corregida para no cortar la tabla
                height=800 + (n_filas * 35), 
                plot_bgcolor='white',
                margin=dict(t=130, b=20, l=20, r=20)
            )

            # Renderizado de la imagen final
            # scale=2 para alta resolución
            img_bytes = fig_reporte.to_image(format="png", engine="kaleido", scale=2)
            
            st.success(f"✅ Reporte visual generado exitosamente (detectadas {len(df_opl)} OPLs). Previsualización a continuación:")
            st.image(img_bytes, use_container_width=True)
            
            st.download_button(
                label="📥 Descargar Reporte OPL Unificado (PNG)",
                data=img_bytes,
                file_name=f"Reporte_OPL_{hoy.strftime('%Y%m%d')}.png",
                mime="image/png",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")

# ==========================================
# 6. BOTONES DE EXPORTACIÓN PDF (Al final)
# ==========================================
st.divider()
with col_p3:
    st.write("**3. Generar Reportes PDF:**")
    # ... [Resto de los botones de descarga de PDF detallados definidos anteriormente] ...
    # ==========================================
# 6. BOTONES DE EXPORTACIÓN EN PANTALLA
# ==========================================
st.divider()

with col_p3:
    st.write("**3. Generar y Descargar PDF:**")
    
    if pdf_tipo == "Mensual":
        col_btn1, col_btn2, col_btn3 = st.columns(3)
    else:
        col_btn1, col_btn2 = st.columns(2)
        
    with col_btn1:
        if st.button("Reporte ESTAMPADO", use_container_width=True):
            with st.spinner("Generando PDF Estampado..."):
                try:
                    pdf_data = crear_pdf("Estampado", pdf_label, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo, df_trend, df_metrics)
                    st.download_button("Descargar Estampado", data=pdf_data, file_name=f"Estampado_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    with col_btn2:
        if st.button("Reporte SOLDADURA", use_container_width=True):
            with st.spinner("Generando PDF Soldadura..."):
                try:
                    pdf_data = crear_pdf("Soldadura", pdf_label, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo, df_trend, df_metrics)
                    st.download_button("Descargar Soldadura", data=pdf_data, file_name=f"Soldadura_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    if pdf_tipo == "Mensual":
        with col_btn3:
            if st.button("Resumen Ejecutivo", use_container_width=True):
                with st.spinner("Generando Resumen Ejecutivo Global..."):
                    try:
                        pdf_resumen = crear_pdf_resumen_ejecutivo(pdf_label, df_trend, df_metrics)
                        st.download_button("Descargar Resumen", data=pdf_resumen, file_name=f"Resumen_Global_Planta_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")
