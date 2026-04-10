import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import os
import calendar
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
    # --- PREVISIÓN FUTURAS ESTAMPADO ---
    "P-028": "PRENSAS PROGRESIVAS GRANDES", "P-029": "PRENSAS PROGRESIVAS GRANDES", "P-030": "PRENSAS PROGRESIVAS GRANDES",
    "BAL-011": "BALANCIN", "BAL-012": "BALANCIN", "BAL-013": "BALANCIN", "BAL-014": "BALANCIN", "BAL-015": "BALANCIN",
    "P-012": "HIDRAULICAS", "P-013": "HIDRAULICAS", "P-014": "HIDRAULICAS",

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
st.set_page_config(page_title="Generador de Reportes PDF - Fumiscor", layout="wide", page_icon="📄")

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
    st.write("Seleccione los parámetros para generar y descargar los reportes consolidados directamente de la base de datos.")
with col_btn:
    if st.button("Limpiar Caché", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ==========================================
# 2. CARGA Y LIMPIEZA DE DATOS DESDE SQL SERVER
# ==========================================
@st.cache_data(ttl=300)
def fetch_data_from_db(fecha_ini, fecha_fin, tipo_periodo, mes=None, anio=None):
    try:
        conn = st.connection("wii_bi", type="sql")
        ini_str = fecha_ini.strftime('%Y-%m-%d')
        fin_str = fecha_fin.strftime('%Y-%m-%d')

        df_trend = pd.DataFrame()

        if tipo_periodo == "Mensual":
            q_prod = f"""
                SELECT c.Name as Máquina, pr.Code as Código, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas
                FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY c.Name, pr.Code
            """
            
            q_metrics = f"""
                SELECT c.Name as Máquina, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas,
                       SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada,
                       (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE,
                       (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD,
                       (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD,
                       (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE
                FROM PROD_M_03 p JOIN CELL c ON p.CellId = c.CellId
                WHERE p.Month = {mes} AND p.Year = {anio}
                GROUP BY c.Name
            """

            q_op = f"""
                SELECT DISTINCT op.Name as Operador, p.Factory as Fábrica, 
                       (SUM(p.Performance * p.ProductiveTime) OVER(PARTITION BY p.OperatorId) / NULLIF(SUM(p.ProductiveTime) OVER(PARTITION BY p.OperatorId), 0)) as PERFORMANCE, 
                       SUM(p.BathTime) OVER(PARTITION BY p.OperatorId) as BathTime, 
                       SUM(p.BreakTime) OVER(PARTITION BY p.OperatorId) as BreakTime, 
                       SUM(p.FeedingTime) OVER(PARTITION BY p.OperatorId) as FeedingTime 
                FROM OPER_M_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId 
                WHERE p.Month = {mes} AND p.Year = {anio}
            """
            
            # Se agregan los numeradores y denominadores de los 4 indicadores para poder combinarlos por planta
            q_trend = f"""
                SELECT p.Month, c.Name as Máquina,
                       SUM(p.Oee * (p.ProductiveTime + p.DownTime)) as OEE_Num,
                       SUM(p.ProductiveTime + p.DownTime) as OEE_Den,
                       (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE,
                       SUM(p.Availability * (p.ProductiveTime + p.DownTime)) as Disp_Num,
                       SUM(p.Performance * p.ProductiveTime) as Perf_Num,
                       SUM(p.ProductiveTime) as T_Operativo,
                       SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) as Cal_Num,
                       SUM(p.Good + p.Rework + p.Scrap) as Piezas_Totales
                FROM PROD_M_03 p JOIN CELL c ON p.CellId = c.CellId
                WHERE p.Year = {anio} AND p.Month <= {mes}
                GROUP BY p.Month, c.Name
            """
            df_trend = conn.query(q_trend)
            
        else:
            q_prod = f"""
                SELECT c.Name as Máquina, pr.Code as Código, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas
                FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name, pr.Code
            """
            
            q_metrics = f"""
                SELECT c.Name as Máquina, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas,
                       SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada,
                       (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE,
                       (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD,
                       (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD,
                       (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE
                FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId
                WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}'
                GROUP BY c.Name
            """
            
            q_op = f"""
                SELECT DISTINCT op.Name as Operador, p.Factory as Fábrica, 
                       (SUM(p.Performance * p.ProductiveTime) OVER(PARTITION BY p.OperatorId) / NULLIF(SUM(p.ProductiveTime) OVER(PARTITION BY p.OperatorId), 0)) as PERFORMANCE, 
                       SUM(p.BathTime) OVER(PARTITION BY p.OperatorId) as BathTime, 
                       SUM(p.BreakTime) OVER(PARTITION BY p.OperatorId) as BreakTime, 
                       SUM(p.FeedingTime) OVER(PARTITION BY p.OperatorId) as FeedingTime 
                FROM OPER_D_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId 
                WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' 
            """

        df_prod_target = conn.query(q_prod)
        df_metrics = conn.query(q_metrics)
        df_op_target = conn.query(q_op)

        q_event = f"""
            SELECT e.Id as Evento_Id, c.Name as Máquina, e.Started as Inicio, e.Finish as Fin, 
                   e.Interval as [Tiempo (Min)], t1.Name as [Nivel Evento 1], t2.Name as [Nivel Evento 2], 
                   t3.Name as [Nivel Evento 3], t4.Name as [Nivel Evento 4], op.Name as Operador, 
                   e.Date as Fecha_Filtro, f.Name as Fábrica, tu.Name as Turno
            FROM EVENT_01 e
            LEFT JOIN CELL c ON e.CellId = c.CellId
            LEFT JOIN EVENTTYPE t1 ON e.EventTypeLevel1 = t1.EventTypeId
            LEFT JOIN EVENTTYPE t2 ON e.EventTypeLevel2 = t2.EventTypeId
            LEFT JOIN EVENTTYPE t3 ON e.EventTypeLevel3 = t3.EventTypeId
            LEFT JOIN EVENTTYPE t4 ON e.EventTypeLevel4 = t4.EventTypeId
            LEFT JOIN FACTORY f ON e.FactoryId = f.FactoryId
            LEFT JOIN TURN tu ON e.TurnId = tu.TurnId
            LEFT JOIN EVENT_OPERATOR_01 eo ON e.Id = eo.EventId
            LEFT JOIN OPERATOR op ON eo.OperatorId = op.OperatorId
            WHERE e.Date BETWEEN '{ini_str}' AND '{fin_str}'
        """
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
                texto_completo = f"{row.get('Nivel Evento 1','')} {row.get('Nivel Evento 2','')} {row.get('Nivel Evento 3','')} {row.get('Nivel Evento 4','')} ".upper()
                if 'PRODUCCION' in texto_completo or 'PRODUCCIÓN' in texto_completo: return 'Producción'
                if 'PROYECTO' in texto_completo: return 'Proyecto'
                if 'BAÑO' in texto_completo or 'BANO' in texto_completo or 'REFRIGERIO' in texto_completo: return 'Descanso'
                if 'PARADA PROGRAMADA' in texto_completo: return 'Parada Programada'
                return 'Falla/Gestión'

            def clasificar_macro(row):
                n1 = str(row.get('Nivel Evento 1', '')).strip().upper()
                n2 = str(row.get('Nivel Evento 2', '')).strip().upper()
                if 'GESTION' in n1 or 'GESTIÓN' in n1: return 'Gestión'
                if 'FALLA' in n1: return n2.title() if n2 not in ['NAN', 'NONE', ''] else 'Falla (Sin área)'
                return n1.title() if n1 not in ['NAN', 'NONE', ''] else 'Sin Clasificar'

            df_raw['Estado_Global'] = df_raw.apply(categorizar_estado, axis=1)
            df_raw['Categoria_Macro'] = df_raw.apply(clasificar_macro, axis=1)

            def obtener_ultimo_nivel(row):
                niveles = [str(row.get(col, '')).strip() for col in ['Nivel Evento 1', 'Nivel Evento 2', 'Nivel Evento 3', 'Nivel Evento 4']]
                validos = [n for n in niveles if n.lower() not in ['none', 'nan', '', 'null']]
                if not validos: return "Sin detalle en sistema"
                ultimo = validos[-1]; macro = row['Categoria_Macro']
                if row['Estado_Global'] == 'Falla/Gestión':
                    if macro.upper() not in ultimo.upper(): return f"[{macro}] {ultimo}"
                return ultimo

            df_raw['Detalle_Final'] = df_raw.apply(obtener_ultimo_nivel, axis=1)

        return df_raw, df_prod_target, df_op_target, df_trend, df_metrics

    except Exception as e:
        st.error(f"Error ejecutando consulta a base de datos wii_bi: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# 3. INTERFAZ: CONFIGURACIÓN PERIODO
# ==========================================
col_p1, col_p2, col_p3 = st.columns([1, 1.2, 1.5])

with col_p1:
    st.write("**1. Tipo de Reporte:**")
    pdf_tipo = st.radio("Período:", ["Diario", "Semanal", "Mensual"], horizontal=True, label_visibility="collapsed")

with col_p2:
    st.write("**2. Seleccione el Período:**")
    today = pd.to_datetime("today").date()
    pdf_ini, pdf_fin, pdf_mes, pdf_anio = None, None, None, None
    pdf_label, file_label = "", ""

    if pdf_tipo == "Diario":
        pdf_fecha = st.date_input("Día para PDF:", value=today)
        pdf_ini = pdf_fin = pd.to_datetime(pdf_fecha)
        pdf_label = f"Dia {pdf_fecha.strftime('%d-%m-%Y')}"
        file_label = pdf_label
        
    elif pdf_tipo == "Semanal":
        fecha_ref = st.date_input("Seleccione un día de la semana deseada:", value=today)
        dt_ref = pd.to_datetime(fecha_ref)
        pdf_ini = dt_ref - timedelta(days=dt_ref.weekday()); pdf_fin = pdf_ini + timedelta(days=6) 
        semana_num = pdf_ini.isocalendar().week
        pdf_label = f"Semana {semana_num} ({pdf_ini.strftime('%d/%m/%Y')} al {pdf_fin.strftime('%d/%m/%Y')})"
        file_label = f"Semana_{semana_num}_{pdf_ini.strftime('%d-%m-%Y')}_al_{pdf_fin.strftime('%d-%m-%Y')}"
        
    elif pdf_tipo == "Mensual":
        c_m, c_y = st.columns(2)
        mes_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        with c_m: mes_sel = st.selectbox("Mes", mes_list, index=today.month-1)
        with c_y: anio_sel = st.selectbox("Año", range(2023, today.year + 2), index=today.year-2023)
        pdf_mes = mes_list.index(mes_sel) + 1; pdf_anio = anio_sel
        pdf_ini = pd.to_datetime(f"{pdf_anio}-{pdf_mes}-01")
        last_day = calendar.monthrange(pdf_anio, pdf_mes)[1]
        pdf_fin = pd.to_datetime(f"{pdf_anio}-{pdf_mes}-{last_day}")
        pdf_label = f"{mes_sel} {pdf_anio}"; file_label = f"{mes_sel}_{pdf_anio}"

df_raw, pdf_df_prod_target, pdf_df_op_target, df_trend, df_metrics = fetch_data_from_db(pdf_ini, pdf_fin, pdf_tipo, mes=pdf_mes, anio=pdf_anio)

# ==========================================
# 4. FUNCIONES HELPER PDF
# ==========================================
def parse_time_to_mins(t_str):
    try:
        if pd.isna(t_str) or t_str in ['nan', 'None', '', '-']: return None
        parts = str(t_str).split(':'); return int(parts[0]) * 60 + int(parts[1])
    except: return None

def mins_to_time_str(m):
    if pd.isna(m) or m is None: return "-"
    m = int(m) % 1440; return f"{m//60:02d}:{m%60:02d}"

def mins_to_duration_str(m):
    if pd.isna(m) or m is None: return "00:00 hs"
    m = int(m); return f"{m//60:02d}:{m%60:02d} hs"

class ReportePDF(FPDF):
    def __init__(self, area, fecha_str, theme_color):
        super().__init__()
        self.area = area; self.fecha_str = fecha_str; self.theme_color = theme_color

    def header(self):
        if os.path.exists("logo.jpg"): self.image("logo.jpg", 10, 8, 30)
        self.set_font("Times", 'B', 16); self.set_text_color(*self.theme_color)
        self.cell(0, 10, clean_text(f"REPORTE GERENCIAL - {self.area.upper()}"), ln=True, align='R')
        self.set_font("Arial", 'B', 10); self.set_text_color(100, 100, 100)
        self.cell(0, 6, clean_text(f"Periodo: {self.fecha_str}"), ln=True, align='R'); self.ln(5)

    def footer(self):
        self.set_y(-15); self.set_font("Arial", "I", 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

def clean_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '-').replace('➤', '>').encode('latin-1', 'replace').decode('latin-1')

def check_space(pdf, required_height):
    if pdf.get_y() + required_height > 275 and pdf.get_y() > 40:
        pdf.add_page(); return True
    return False

def print_section_title(pdf, title, theme_color):
    pdf.ln(3); pdf.set_font("Times", 'B', 14); pdf.set_text_color(*theme_color)
    pdf.cell(0, 6, clean_text(title), ln=True)
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*theme_color); pdf.set_line_width(0.5); pdf.line(x, y, x + 190, y)
    pdf.set_draw_color(0, 0, 0); pdf.set_line_width(0.2); pdf.set_text_color(0, 0, 0); pdf.ln(3)

def setup_table_header(pdf, theme_color):
    pdf.set_fill_color(*theme_color); pdf.set_text_color(255, 255, 255); pdf.set_draw_color(*theme_color)

def setup_table_row(pdf):
    pdf.set_fill_color(255, 255, 255); pdf.set_text_color(50, 50, 50); pdf.set_draw_color(200, 200, 200)

def set_pdf_color(pdf, val):
    if val < 0.85: pdf.set_text_color(220, 20, 20)
    elif val <= 0.95: pdf.set_text_color(200, 150, 0)
    else: pdf.set_text_color(33, 195, 84)

def print_pdf_metric_row(pdf, prefix, m):
    pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text(f"{prefix} | OEE: "))
    set_pdf_color(pdf, m.get('OEE', 0)); pdf.write(7, f"{m.get('OEE', 0):.1%}")
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Disp: "))
    set_pdf_color(pdf, m.get('DISPONIBILIDAD', 0)); pdf.write(7, f"{m.get('DISPONIBILIDAD', 0):.1%}")
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Perf: "))
    set_pdf_color(pdf, m.get('PERFORMANCE', 0)); pdf.write(7, f"{m.get('PERFORMANCE', 0):.1%}")
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Cal: "))
    set_pdf_color(pdf, m.get('CALIDAD', 0)); pdf.write(7, f"{m.get('CALIDAD', 0):.1%}")
    pdf.set_text_color(0, 0, 0); pdf.ln(7)

def add_image_safe(pdf, img_path, w_mm, h_mm, center=True):
    if pdf.get_y() + h_mm > 275:
        pdf.add_page()
    x = (210 - w_mm) / 2 if center else pdf.get_x()
    y = pdf.get_y()
    pdf.image(img_path, x=x, y=y, w=w_mm)
    pdf.set_y(y + h_mm + 5)


# ==========================================
# 5. MOTOR GENERADOR DEL PDF
# ==========================================
def crear_pdf(area, label_reporte, op_target_df, prod_target_df, df_pdf_raw, p_tipo, df_trend, df_metrics_pdf):
    if area.upper() == "ESTAMPADO":
        theme_color = (15, 76, 129); comp_color = (52, 152, 219)  
        chart_bars = ['#003366', '#3498DB', '#AED6F1']; pie_colors = px.colors.sequential.Blues_r
        grupos_area = GRUPOS_ESTAMPADO
    else:
        theme_color = (211, 84, 0); comp_color = (230, 126, 34) 
        chart_bars = ['#993300', '#E67E22', '#FAD7A1']; pie_colors = px.colors.sequential.Oranges_r
        grupos_area = GRUPOS_SOLDADURA
        
    hex_theme = '#%02x%02x%02x' % theme_color; hex_comp = '#%02x%02x%02x' % comp_color  
    mapa_limpio = {str(k).strip().upper(): v for k, v in MAQUINAS_MAP.items()}

    if not df_metrics_pdf.empty and df_metrics_pdf['OEE'].max() > 1.5:
        df_metrics_pdf['OEE'] = df_metrics_pdf['OEE'] / 100.0
        df_metrics_pdf['DISPONIBILIDAD'] = df_metrics_pdf['DISPONIBILIDAD'] / 100.0
        df_metrics_pdf['PERFORMANCE'] = df_metrics_pdf['PERFORMANCE'] / 100.0
        df_metrics_pdf['CALIDAD'] = df_metrics_pdf['CALIDAD'] / 100.0

    df_pdf = pd.DataFrame(columns=['Máquina', 'Fábrica', 'Estado_Global', 'Tiempo (Min)'])
    if not df_pdf_raw.empty:
        df_pdf = df_pdf_raw[df_pdf_raw['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
    df_pdf['Grupo_Máquina'] = df_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    df_prod_pdf = pd.DataFrame(columns=['Máquina', 'Buenas', 'Retrabajo', 'Observadas'])
    if not prod_target_df.empty:
        df_prod_pdf = prod_target_df.copy()
    df_prod_pdf['Grupo_Máquina'] = df_prod_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    pdf = ReportePDF(area, label_reporte, theme_color)
    pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    
    links_grupos = {g: pdf.add_link() for g in grupos_area}
    link_perfo = pdf.add_link(); link_tiempos = pdf.add_link()

    # --- ÍNDICE DEL REPORTE ---
    pdf.ln(10); pdf.set_font("Times", 'B', 18); pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text("ÍNDICE DEL REPORTE"), ln=True, align='C')
    
    pdf.ln(10); pdf.set_font("Arial", 'U', 12); pdf.set_text_color(*comp_color)
    
    if p_tipo == "Mensual":
        pdf.cell(0, 8, clean_text("> Resumen Ejecutivo Mensual: KPI de Planta (Estampado y Soldadura)"), ln=True)
        
    for g in grupos_area:
        pdf.cell(0, 8, clean_text(f"> Reporte detallado de Grupo: {g}"), ln=True, link=links_grupos[g])
    pdf.ln(5)
    pdf.cell(0, 8, clean_text("> Performance General de Operarios"), ln=True, link=link_perfo)
    pdf.cell(0, 8, clean_text("> Tablas de Tiempos Acumulados de Baño y Refrigerio"), ln=True, link=link_tiempos)

    if df_pdf.empty and p_tipo != "Mensual":
        pdf.add_page(); pdf.set_font("Arial", 'I', 12); pdf.set_text_color(100)
        pdf.cell(0, 10, f"No hay datos registrados para la fabrica {area} en este periodo.", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    # =========================================================================
    # NUEVA PÁGINA: RESUMEN EJECUTIVO (SÓLO PARA REPORTE MENSUAL)
    # =========================================================================
    if p_tipo == "Mensual":
        pdf.add_page()
        print_section_title(pdf, "RESUMEN EJECUTIVO: KPI POR PLANTA", theme_color)

        def get_planta(maq_name):
            maq_upper = str(maq_name).strip().upper()
            grupo = mapa_limpio.get(maq_upper, 'OTRO')
            if grupo in GRUPOS_ESTAMPADO: return 'ESTAMPADO'
            if grupo in GRUPOS_SOLDADURA: return 'SOLDADURA'
            return 'OTRO'

        df_met_all = df_metrics_pdf.copy()
        df_met_all['Planta'] = df_met_all['Máquina'].apply(get_planta)
        
        # Ponderaciones Matemáticas por Máquina para calcular el Real Global
        df_met_all['T_Planificado'] = df_met_all['T_Operativo'].fillna(0) + df_met_all['T_Parada'].fillna(0)
        df_met_all['Piezas_Totales'] = df_met_all['Buenas'].fillna(0) + df_met_all['Retrabajo'].fillna(0) + df_met_all['Observadas'].fillna(0)

        df_met_all['OEE_Num'] = df_met_all['OEE'].fillna(0) * df_met_all['T_Planificado']
        df_met_all['Disp_Num'] = df_met_all['DISPONIBILIDAD'].fillna(0) * df_met_all['T_Planificado']
        df_met_all['Perf_Num'] = df_met_all['PERFORMANCE'].fillna(0) * df_met_all['T_Operativo']
        df_met_all['Cal_Num'] = df_met_all['CALIDAD'].fillna(0) * df_met_all['Piezas_Totales']

        met_planta = df_met_all.groupby('Planta')[['OEE_Num', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Planificado', 'T_Operativo', 'Piezas_Totales']].sum()

        def calc_metrics(p_name):
            if p_name in met_planta.index:
                row = met_planta.loc[p_name]
                oee = row['OEE_Num'] / row['T_Planificado'] if row['T_Planificado'] > 0 else 0
                disp = row['Disp_Num'] / row['T_Planificado'] if row['T_Planificado'] > 0 else 0
                perf = row['Perf_Num'] / row['T_Operativo'] if row['T_Operativo'] > 0 else 0
                cal = row['Cal_Num'] / row['Piezas_Totales'] if row['Piezas_Totales'] > 0 else 0
                return oee, disp, perf, cal
            return 0, 0, 0, 0

        oee_est, disp_est, perf_est, cal_est = calc_metrics('ESTAMPADO')
        oee_sol, disp_sol, perf_sol, cal_sol = calc_metrics('SOLDADURA')

        def draw_kpi_row(y, title, oee, disp, perf, cal):
            pdf.set_xy(10, y)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(*theme_color)
            pdf.cell(0, 6, clean_text(title), ln=1)
            y_boxes = pdf.get_y() + 2
            
            w = 42; spacing = 5; x_start = 13.5
            
            def draw_box(x, title_box, val):
                pdf.set_xy(x, y_boxes)
                pdf.set_font("Arial", 'B', 9)
                pdf.set_fill_color(*theme_color)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(w, 8, clean_text(title_box), border=1, align='C', fill=True, ln=2)
                
                pdf.set_fill_color(245, 245, 245)
                set_pdf_color(pdf, val)
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(w, 12, f"{val*100:.1f}%", border=1, align='C', fill=True)
            
            draw_box(x_start, "OEE", oee)
            draw_box(x_start + w + spacing, "DISPONIBILIDAD", disp)
            draw_box(x_start + 2*(w + spacing), "PERFORMANCE", perf)
            draw_box(x_start + 3*(w + spacing), "CALIDAD", cal)
            
            return y_boxes + 25

        y_curr = pdf.get_y() + 5
        y_curr = draw_kpi_row(y_curr, "INDICADORES: ESTAMPADO", oee_est, disp_est, perf_est, cal_est)
        y_curr += 8
        y_curr = draw_kpi_row(y_curr, "INDICADORES: SOLDADURA", oee_sol, disp_sol, perf_sol, cal_sol)

        if not df_trend.empty:
            pdf.set_y(y_curr + 10)
            pdf.set_font("Arial", 'B', 12); pdf.set_text_color(*theme_color)
            pdf.cell(0, 6, clean_text("Evolución Mensual Histórica (4 Indicadores por Planta)"), ln=True)

            df_trend_all = df_trend.copy()
            df_trend_all['Planta'] = df_trend_all['Máquina'].apply(get_planta)

            trend_planta = df_trend_all[df_trend_all['Planta'] != 'OTRO'].groupby(['Month', 'Planta'])[['OEE_Num', 'OEE_Den', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Operativo', 'Piezas_Totales']].sum().reset_index()
            
            trend_planta['OEE'] = (trend_planta['OEE_Num'] / trend_planta['OEE_Den']).fillna(0)
            trend_planta['DISP'] = (trend_planta['Disp_Num'] / trend_planta['OEE_Den']).fillna(0)
            trend_planta['PERF'] = (trend_planta['Perf_Num'] / trend_planta['T_Operativo']).fillna(0)
            trend_planta['CAL'] = (trend_planta['Cal_Num'] / trend_planta['Piezas_Totales']).fillna(0)

            trend_melt = trend_planta.melt(id_vars=['Month', 'Planta'], value_vars=['OEE', 'DISP', 'PERF', 'CAL'], var_name='Indicador', value_name='Valor')
            
            if trend_melt['Valor'].max() <= 1.5 and trend_melt['Valor'].max() > 0:
                trend_melt['Valor'] = trend_melt['Valor'] * 100

            meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
            trend_melt['Mes_Nombre'] = trend_melt['Month'].map(meses_map)

            fig_glob = px.bar(
                trend_melt, x='Mes_Nombre', y='Valor', color='Indicador', facet_row='Planta',
                barmode='group', text_auto='.0f',
                color_discrete_map={'OEE': '#2C3E50', 'DISP': '#2980B9', 'PERF': '#F39C12', 'CAL': '#27AE60'}
            )
            fig_glob.update_layout(
                height=450, width=800, margin=dict(t=30, b=20, l=20, r=20),
                yaxis_title='Porcentaje (%)', xaxis_title='',
                plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_glob.update_yaxes(range=[0, 110])

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_glob:
                fig_glob.write_image(tmp_glob.name, engine="kaleido")
                add_image_safe(pdf, tmp_glob.name, w_mm=190, h_mm=115, center=True)
                os.remove(tmp_glob.name)
    # =========================================================================

    def dibujar_tabla_eventos_detallada(df_subset, col_detalle, titulo, color_t):
        if not df_subset.empty:
            check_space(pdf, 25); pdf.set_font("Arial", 'B', 9); pdf.set_text_color(*color_t)
            pdf.cell(0, 6, clean_text(f">> {titulo}:"), ln=True); pdf.ln(1)
            def dibujar_cabeceras():
                setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                pdf.cell(15, 6, "Fecha", 1, 0, 'C', True)
                pdf.cell(12, 6, "Ini.", 1, 0, 'C', True)
                pdf.cell(12, 6, "Fin", 1, 0, 'C', True)
                pdf.cell(106, 6, "Detalle Registrado en Sistema", 1, 0, 'L', True)
                pdf.cell(12, 6, "Min", 1, 0, 'C', True)
                pdf.cell(33, 6, "Operador", 1, 1, 'L', True)
            
            dibujar_cabeceras(); setup_table_row(pdf); pdf.set_font("Arial", '', 8)
            df_subset['_sort_time'] = df_subset['Inicio_Str'].apply(lambda x: parse_time_to_mins(x) if pd.notna(x) else 9999)
            df_subset = df_subset.sort_values(['Fecha_Filtro', '_sort_time'], ascending=[True, True])
            for _, row in df_subset.iterrows():
                if pdf.get_y() > 265:
                    pdf.add_page(); dibujar_cabeceras(); setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                val_fecha = pd.to_datetime(row['Fecha_Filtro']).strftime('%d/%m') if pd.notna(row['Fecha_Filtro']) else "-"
                val_inicio = str(row['Inicio_Str'])[:5] if pd.notna(row['Inicio_Str']) else "-"
                val_fin = str(row['Fin_Str'])[:5] if pd.notna(row['Fin_Str']) else "-"
                minutos = f"{row['Tiempo (Min)']:.0f}"
                operador = " " + str(row['Operador'])[:15]
                detalle_str = " " + str(row[col_detalle]) if col_detalle in row and pd.notna(row[col_detalle]) else " Sin detalle"
                
                pdf.cell(15, 5, val_fecha, 'B', 0, 'C')
                pdf.cell(12, 5, val_inicio, 'B', 0, 'C')
                pdf.cell(12, 5, val_fin, 'B', 0, 'C')
                pdf.cell(106, 5, clean_text(detalle_str[:70]), 'B', 0, 'L')
                pdf.cell(12, 5, minutos, 'B', 0, 'C')
                pdf.cell(33, 5, clean_text(operador), 'B', 1, 'L')
            pdf.ln(4)

    def obtener_metricas_maquina(maq_name):
        maq_row = df_metrics_pdf[df_metrics_pdf['Máquina'] == maq_name]
        if maq_row.empty: return None
        r = maq_row.iloc[0]
        return {
            'OEE': r['OEE'], 'DISPONIBILIDAD': r['DISPONIBILIDAD'], 
            'PERFORMANCE': r['PERFORMANCE'], 'CALIDAD': r['CALIDAD'], 
            'T_Planificado': (r['T_Operativo'] + r['T_Parada']) if pd.notna(r['T_Operativo']) else 0,
            'T_Operativo': r['T_Operativo'] if pd.notna(r['T_Operativo']) else 0, 
            'Buenas': r['Buenas'] if pd.notna(r['Buenas']) else 0, 
            'Totales': (r['Buenas'] + r['Retrabajo'] + r['Observadas']) if pd.notna(r['Buenas']) else 0
        }

    # RECORRIDO POR CADA GRUPO 
    for g in grupos_area:
        maq_del_grupo = [m for m, grp in MAQUINAS_MAP.items() if grp == g]
        df_pdf_g = df_pdf[df_pdf['Máquina'].isin(maq_del_grupo)]
        if df_pdf_g.empty: continue
            
        pdf.add_page(); pdf.set_link(links_grupos[g]) 
        pdf.set_font("Times", 'B', 16); pdf.set_text_color(*theme_color)
        pdf.cell(0, 10, clean_text(f"SECCIÓN GRUPO: {g}"), ln=True, align='L', border='B'); pdf.ln(5)

        # 1. RESUMEN OEE
        check_space(pdf, 30); print_section_title(pdf, "1. Resumen OEE del Grupo", theme_color)
        g_plan = 0; g_op = 0; g_buenas = 0; g_totales = 0
        g_disp_w = 0; g_perf_w = 0; g_oee_w = 0
        maquinas_metricas = {}
        
        for maq in maq_del_grupo:
            metrics = obtener_metricas_maquina(maq)
            if metrics:
                maquinas_metricas[maq] = metrics
                t_p = metrics['T_Planificado']; t_o = metrics['T_Operativo']
                g_plan += t_p; g_op += t_o
                g_buenas += metrics['Buenas']; g_totales += metrics['Totales']
                
                g_disp_w += metrics['DISPONIBILIDAD'] * t_p
                g_perf_w += metrics['PERFORMANCE'] * t_o
                g_oee_w += metrics['OEE'] * t_p
                
        g_disp = g_disp_w / g_plan if g_plan > 0 else 0
        g_perf = g_perf_w / g_op if g_op > 0 else 0
        g_cal = g_buenas / g_totales if g_totales > 0 else 0
        g_oee = g_disp * g_perf * g_cal
        
        m_g = {'OEE': g_oee, 'DISPONIBILIDAD': g_disp, 'PERFORMANCE': g_perf, 'CALIDAD': g_cal}
        print_pdf_metric_row(pdf, f"Total {g}", m_g)
        
        for maq, metrics in maquinas_metricas.items():
            print_pdf_metric_row(pdf, f"    > {maq}", metrics)
        pdf.ln(3)

        # 2. GRÁFICO OEE MENSUAL AGRUPADO O HORARIOS
        if p_tipo == "Mensual":
            check_space(pdf, 80)
            print_section_title(pdf, "2. Evolución Mensual OEE por Máquina", theme_color)
            
            if not df_trend.empty:
                df_trend_g = df_trend[df_trend['Máquina'].isin(maq_del_grupo)].copy()
                if not df_trend_g.empty:
                    if df_trend_g['OEE'].max() <= 1.5:
                        df_trend_g['OEE'] = df_trend_g['OEE'] * 100
                    
                    meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                    df_trend_g['Mes_Nombre'] = df_trend_g['Month'].map(meses_map)
                    
                    fig_trend_oee = px.bar(
                        df_trend_g, x='Mes_Nombre', y='OEE', color='Máquina', 
                        barmode='group', text_auto='.1f', color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    
                    fig_trend_oee.update_layout(
                        height=350, width=800, margin=dict(t=20, b=20, l=20, r=20),
                        yaxis_title='OEE (%)', xaxis_title='', legend_title='Máquinas', 
                        plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(range=[0, 110])
                    )
                    
                    y_base = pdf.get_y()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_oee:
                        fig_trend_oee.write_image(tmp_oee.name, engine="kaleido")
                        pdf.image(tmp_oee.name, x=10, y=y_base, w=190)
                        os.remove(tmp_oee.name)
                        
                    pdf.set_y(y_base + 90); pdf.ln(2)
                else:
                    pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay datos históricos para graficar en este grupo."), ln=True)
            else:
                pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay datos históricos para graficar."), ln=True)
        else:
            check_space(pdf, 25); print_section_title(pdf, "2. Horarios y Tiempo de Apertura", theme_color)
            df_pdf_g_horarios = df_pdf_g.copy()
            if not df_pdf_g_horarios.empty and 'Inicio_Str' in df_pdf_g_horarios.columns:
                if p_tipo == "Diario":
                    tiempos_list = []
                    for (maq, turno), grp in df_pdf_g_horarios.groupby(['Máquina', 'Turno']):
                        intervals = []
                        for _, r in grp.iterrows():
                            ini = parse_time_to_mins(r['Inicio_Str']); fin = parse_time_to_mins(r['Fin_Str'])
                            if ini is not None and fin is not None:
                                if fin < ini and (ini - fin) > 720: fin += 1440
                                intervals.append([ini, fin])
                        if not intervals: continue
                        intervals.sort(key=lambda x: x[0]); merged = [intervals[0]]
                        for current in intervals[1:]:
                            last = merged[-1]
                            if current[0] <= last[1]: last[1] = max(last[1], current[1])
                            else: merged.append(current)
                        total_active = sum(iv[1] - iv[0] for iv in merged)
                        min_i, max_f = merged[0][0], merged[-1][1]; tiempo_bruto = max_f - min_i
                        unregistered_time = max(0, tiempo_bruto - total_active)
                        tiempos_list.append({'Máquina': maq, 'Turno': turno, 'Inicio': min_i, 'Fin': max_f, 'Total': total_active, 'NoReg': unregistered_time})
                    
                    df_horarios = pd.DataFrame(tiempos_list)
                    if not df_horarios.empty:
                        df_horarios = df_horarios.sort_values(['Máquina', 'Turno'])
                        def dibujar_cabeza_hora():
                            setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                            pdf.cell(35, 6, "Maquina", 1, 0, 'C', True); pdf.cell(15, 6, "Turno", 1, 0, 'C', True)
                            pdf.cell(25, 6, "Hora Inicio", 1, 0, 'C', True); pdf.cell(25, 6, "Hora Cierre", 1, 0, 'C', True)
                            pdf.cell(45, 6, "Apertura Neta", 1, 0, 'C', True); pdf.cell(45, 6, "No Registrado", 1, 1, 'C', True); pdf.ln()
                        
                        dibujar_cabeza_hora()
                        setup_table_row(pdf); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
                        for _, r in df_horarios.iterrows():
                            if pdf.get_y() > 265: 
                                pdf.add_page(); dibujar_cabeza_hora(); setup_table_row(pdf); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
                            pdf.cell(35, 5, " " + clean_text(str(r['Máquina'])[:15]), 1, 0, 'L'); pdf.cell(15, 5, clean_text(str(r['Turno'])), 1, 0, 'C')
                            pdf.cell(25, 5, clean_text(mins_to_time_str(r['Inicio'])), 1, 0, 'C'); pdf.cell(25, 5, clean_text(mins_to_time_str(r['Fin'])), 1, 0, 'C')
                            pdf.cell(45, 5, clean_text(mins_to_duration_str(r['Total'])), 1, 0, 'C'); pdf.cell(45, 5, clean_text(mins_to_duration_str(r['NoReg'])), 1, 1, 'C')
                        pdf.ln(5)
                else:
                    df_pdf_g_horarios['Fecha_DT'] = pd.to_datetime(df_pdf_g_horarios['Fecha_Filtro'])
                    df_pdf_g_horarios['Dia_Semana'] = df_pdf_g_horarios['Fecha_DT'].dt.dayofweek
                    horarios_list = []
                    for (maq, turno, dia), grp in df_pdf_g_horarios.groupby(['Máquina', 'Turno', 'Dia_Semana']):
                        if dia > 4: continue 
                        ini = grp['Inicio_Str'].apply(parse_time_to_mins).min(); fin = grp['Fin_Str'].apply(parse_time_to_mins).max()
                        if pd.notna(ini) and pd.notna(fin):
                            horarios_list.append({'Máquina': maq, 'Turno': turno, 'Dia': dia, 'Rango': f"{mins_to_time_str(ini)} - {mins_to_time_str(fin)}"})
                    if horarios_list:
                        df_h = pd.DataFrame(horarios_list).pivot_table(index=['Máquina', 'Turno'], columns='Dia', values='Rango', aggfunc='first').reset_index()
                        for i in range(5):
                            if i not in df_h.columns: df_h[i] = "-"
                        df_h = df_h.fillna("-").sort_values(['Máquina', 'Turno'])
                        def dibujar_cabeza_semana():
                            setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                            pdf.cell(25, 6, "Maquina", 1, 0, 'C', True); pdf.cell(12, 6, "Turno", 1, 0, 'C', True)
                            for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]: pdf.cell(30, 6, d, 1, 0, 'C', True)
                            pdf.ln()

                        dibujar_cabeza_semana()
                        setup_table_row(pdf); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                        for _, row in df_h.iterrows():
                            if pdf.get_y() > 265: 
                                pdf.add_page(); dibujar_cabeza_semana(); setup_table_row(pdf); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                            pdf.cell(25, 5, clean_text(row['Máquina']), 1); pdf.cell(12, 5, clean_text(str(row.get('Turno', '-'))), 1, 0, 'C')
                            for i in range(5): pdf.cell(30, 5, str(row.get(i, "-")), 1, 0, 'C')
                            pdf.ln()
                        pdf.ln(5)
            else:
                pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay horarios registrados para generar las estadísticas."), ln=True)

        # 3. DESGLOSE POR MÁQUINA (Espacio optimizado)
        maquinas_con_tiempo = []
        if not df_pdf_g.empty:
            for maq in sorted(df_pdf_g['Máquina'].unique()):
                df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
                t_total = df_maq[df_maq['Estado_Global'].isin(['Producción', 'Falla/Gestión', 'Parada Programada', 'Proyecto', 'Descanso'])]['Tiempo (Min)'].sum()
                if t_total > 0: maquinas_con_tiempo.append(maq)
        
        if maquinas_con_tiempo:
            pdf.ln(5) # Añadimos un pequeño margen antes de empezar a listar las máquinas
            for maq in maquinas_con_tiempo:
                check_space(pdf, 50) # <-- VERIFICA ESPACIO EN VEZ DE SALTO ESTRICTO
                
                df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
                t_prod = df_maq[df_maq['Estado_Global'] == 'Producción']['Tiempo (Min)'].sum()
                t_falla = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']['Tiempo (Min)'].sum()
                t_parada = df_maq[df_maq
