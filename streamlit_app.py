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
    "P-023": "PRENSAS PROGRESIVAS", "P-024": "PRENSAS PROGRESIVAS", "P-025": "PRENSAS PROGRESIVAS",
    "P-026": "PRENSAS PROGRESIVAS GRANDES", "P-027": "PRENSAS PROGRESIVAS GRANDES",
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
    # --- PREVISIÓN FUTURAS SOLDADURA ---
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

        if tipo_periodo == "Mensual":
            q_oee = f"SELECT c.Name as Máquina, p.Oee as OEE, p.Availability as DISPONIBILIDAD, p.Performance as PERFORMANCE, p.Quality as CALIDAD FROM PROD_M_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Month = {mes} AND p.Year = {anio}"
            q_prod = f"SELECT c.Name as Máquina, pr.Code as Código, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY c.Name, pr.Code"
            q_op = f"SELECT op.Name as Operador, p.Factory as Fábrica, AVG(p.Performance) as PERFORMANCE, SUM(p.BathTime) as BathTime, SUM(p.BreakTime) as BreakTime, SUM(p.FeedingTime) as FeedingTime FROM OPER_M_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY op.Name, p.Factory"
        else:
            q_oee = f"SELECT c.Name as Máquina, AVG(p.Oee) as OEE, AVG(p.Availability) as DISPONIBILIDAD, AVG(p.Performance) as PERFORMANCE, AVG(p.Quality) as CALIDAD FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name"
            q_prod = f"SELECT c.Name as Máquina, pr.Code as Código, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name, pr.Code"
            q_op = f"SELECT op.Name as Operador, p.Factory as Fábrica, AVG(p.Performance) as PERFORMANCE, SUM(p.BathTime) as BathTime, SUM(p.BreakTime) as BreakTime, SUM(p.FeedingTime) as FeedingTime FROM OPER_D_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY op.Name, p.Factory"

        df_oee_target = conn.query(q_oee)
        df_prod_target = conn.query(q_prod)
        df_op_target = conn.query(q_op)

        # AHORA INCLUIMOS HASTA EL NIVEL 4 PARA QUE NO SE PIERDA NADA
        q_event = f"""
            SELECT c.Name as Máquina, e.Started as Inicio, e.Finish as Fin, 
                   e.Interval as [Tiempo (Min)], 
                   t1.Name as [Nivel Evento 1], 
                   t2.Name as [Nivel Evento 2], 
                   t3.Name as [Nivel Evento 3], 
                   t4.Name as [Nivel Evento 4],
                   op.Name as Operador, e.Date as Fecha_Filtro, f.Name as Fábrica,
                   tu.Name as Turno
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

            # --- FUNCIONES DE CLASIFICACIÓN INTELIGENTE ---
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
                
                ultimo = validos[-1]
                macro = row['Categoria_Macro']
                
                # Si es Falla/Gestión, agregamos el tag del área visible para dar contexto
                if row['Estado_Global'] == 'Falla/Gestión':
                    if macro.upper() not in ultimo.upper():
                        return f"[{macro}] {ultimo}"
                return ultimo

            df_raw['Detalle_Final'] = df_raw.apply(obtener_ultimo_nivel, axis=1)

        return df_raw, df_oee_target, df_prod_target, df_op_target

    except Exception as e:
        st.error(f"Error ejecutando consulta a base de datos wii_bi: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
        pdf_ini = dt_ref - timedelta(days=dt_ref.weekday()) 
        pdf_fin = pdf_ini + timedelta(days=6) 
        
        semana_num = pdf_ini.isocalendar().week
        pdf_label = f"Semana {semana_num} ({pdf_ini.strftime('%d/%m/%Y')} al {pdf_fin.strftime('%d/%m/%Y')})"
        file_label = f"Semana_{semana_num}_{pdf_ini.strftime('%d-%m-%Y')}_al_{pdf_fin.strftime('%d-%m-%Y')}"
        
    elif pdf_tipo == "Mensual":
        c_m, c_y = st.columns(2)
        mes_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        with c_m: mes_sel = st.selectbox("Mes", mes_list, index=today.month-1)
        with c_y: anio_sel = st.selectbox("Año", range(2023, today.year + 2), index=today.year-2023)
        
        pdf_mes = mes_list.index(mes_sel) + 1
        pdf_anio = anio_sel
        pdf_ini = pd.to_datetime(f"{pdf_anio}-{pdf_mes}-01")
        last_day = calendar.monthrange(pdf_anio, pdf_mes)[1]
        pdf_fin = pd.to_datetime(f"{pdf_anio}-{pdf_mes}-{last_day}")
        
        pdf_label = f"{mes_sel} {pdf_anio}"
        file_label = f"{mes_sel}_{pdf_anio}"

df_raw, pdf_df_oee_target, pdf_df_prod_target, pdf_df_op_target = fetch_data_from_db(
    pdf_ini, pdf_fin, pdf_tipo, mes=pdf_mes, anio=pdf_anio
)

# ==========================================
# 4. FUNCIONES HELPER PDF
# ==========================================
def parse_time_to_mins(t_str):
    try:
        if pd.isna(t_str) or t_str in ['nan', 'None', '', '-']: return None
        parts = str(t_str).split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

def mins_to_time_str(m):
    if pd.isna(m) or m is None: return "-"
    m = int(m) % 1440
    return f"{m//60:02d}:{m%60:02d}"

def mins_to_duration_str(m):
    if pd.isna(m) or m is None: return "00:00 hs"
    m = int(m)
    return f"{m//60:02d}:{m%60:02d} hs"

class ReportePDF(FPDF):
    def __init__(self, area, fecha_str, theme_color):
        super().__init__()
        self.area = area
        self.fecha_str = fecha_str
        self.theme_color = theme_color

    def header(self):
        if os.path.exists("logo.jpg"): self.image("logo.jpg", 10, 8, 30)
        self.set_font("Times", 'B', 16)
        self.set_text_color(*self.theme_color)
        self.cell(0, 10, clean_text(f"REPORTE GERENCIAL - {self.area.upper()}"), ln=True, align='R')
        self.set_font("Arial", 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, clean_text(f"Periodo: {self.fecha_str}"), ln=True, align='R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

def clean_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '-').replace('➤', '>').encode('latin-1', 'replace').decode('latin-1')

def check_space(pdf, required_height):
    if pdf.get_y() + required_height > (pdf.h - 15): pdf.add_page()

def print_section_title(pdf, title, theme_color):
    pdf.ln(3)
    pdf.set_font("Times", 'B', 14)
    pdf.set_text_color(*theme_color)
    pdf.cell(0, 6, clean_text(title), ln=True)
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*theme_color)
    pdf.set_line_width(0.5)
    pdf.line(x, y, x + 190, y)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.2)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

def setup_table_header(pdf, theme_color):
    pdf.set_fill_color(*theme_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(*theme_color)

def setup_table_row(pdf):
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(50, 50, 50)
    pdf.set_draw_color(200, 200, 200)

def set_pdf_color(pdf, val):
    if val < 0.85: pdf.set_text_color(220, 20, 20)
    elif val <= 0.95: pdf.set_text_color(200, 150, 0)
    else: pdf.set_text_color(33, 195, 84)

def print_pdf_metric_row(pdf, prefix, m):
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text(f"{prefix} | OEE: "))
    set_pdf_color(pdf, m.get('OEE', 0))
    pdf.write(7, f"{m.get('OEE', 0):.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Disp: "))
    set_pdf_color(pdf, m.get('DISPONIBILIDAD', 0))
    pdf.write(7, f"{m.get('DISPONIBILIDAD', 0):.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Perf: "))
    set_pdf_color(pdf, m.get('PERFORMANCE', 0))
    pdf.write(7, f"{m.get('PERFORMANCE', 0):.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Cal: "))
    set_pdf_color(pdf, m.get('CALIDAD', 0))
    pdf.write(7, f"{m.get('CALIDAD', 0):.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)

# ==========================================
# 5. MOTOR GENERADOR DEL PDF
# ==========================================
def crear_pdf(area, label_reporte, oee_target_df, op_target_df, prod_target_df, df_pdf_raw, p_tipo):
    if area.upper() == "ESTAMPADO":
        theme_color = (0, 128, 128) 
        comp_color = (210, 105, 30) 
        chart_bars = ['#008080', '#66B2B2', '#B2D8D8']
        grupos_area = GRUPOS_ESTAMPADO
    else:
        theme_color = (178, 34, 34) 
        comp_color = (40, 100, 150) 
        chart_bars = ['#B22222', '#D98880', '#F2D7D5']
        grupos_area = GRUPOS_SOLDADURA
        
    hex_theme = '#%02x%02x%02x' % theme_color
    hex_comp = '#%02x%02x%02x' % comp_color  

    mapa_limpio = {str(k).strip().upper(): v for k, v in MAQUINAS_MAP.items()}

    df_pdf = pd.DataFrame()
    if not df_pdf_raw.empty:
        df_pdf = df_pdf_raw[df_pdf_raw['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
        df_pdf['Grupo_Máquina'] = df_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    df_prod_pdf = pd.DataFrame()
    if not prod_target_df.empty:
        df_prod_pdf = prod_target_df.copy()
        df_prod_pdf['Grupo_Máquina'] = df_prod_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    if not oee_target_df.empty:
        for c in ['OEE', 'DISPONIBILIDAD', 'PERFORMANCE', 'CALIDAD']:
            if c in oee_target_df.columns:
                oee_target_df[c] = pd.to_numeric(oee_target_df[c], errors='coerce').fillna(0) / 100.0

    pdf = ReportePDF(area, label_reporte, theme_color)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    links_grupos = {g: pdf.add_link() for g in grupos_area}
    link_perfo = pdf.add_link()
    link_tiempos = pdf.add_link()

    pdf.ln(10)
    pdf.set_font("Times", 'B', 18)
    pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text("ÍNDICE DEL REPORTE"), ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'U', 12)
    pdf.set_text_color(0, 102, 204)
    for g in grupos_area:
        pdf.cell(0, 8, clean_text(f"> Reporte detallado de Grupo: {g}"), ln=True, link=links_grupos[g])
    pdf.ln(5)
    pdf.cell(0, 8, clean_text("> Performance General de Operarios"), ln=True, link=link_perfo)
    pdf.cell(0, 8, clean_text("> Tiempos de Baño y Refrigerio (General)"), ln=True, link=link_tiempos)

    def dibujar_tabla_eventos_detallada(df_subset, col_detalle):
        setup_table_header(pdf, theme_color)
        pdf.set_font("Arial", 'B', 8)
        
        w_f, w_i, w_f2, w_d, w_m, w_o = 18, 14, 14, 86, 13, 45
        headers = ["Fecha", "Ini.", "Fin", "Detalle Registrado en Sistema", "Min", "Operador"]
        aligns = ['C', 'C', 'C', 'L', 'C', 'L']
        
        for col, w, al in zip(headers, [w_f, w_i, w_f2, w_d, w_m, w_o], aligns):
            ln = True if col == "Operador" else False
            pdf.cell(w, 7, col, border=1, align=al, fill=True, ln=ln)
        
        setup_table_row(pdf)
        pdf.set_font("Arial", '', 8)
        
        df_subset['_sort_time'] = df_subset['Inicio_Str'].apply(lambda x: parse_time_to_mins(x) if pd.notna(x) else 9999)
        df_subset = df_subset.sort_values(['Fecha_Filtro', '_sort_time'], ascending=[True, True])
        
        for _, row in df_subset.iterrows():
            val_fecha = pd.to_datetime(row['Fecha_Filtro']).strftime('%d/%m') if pd.notna(row['Fecha_Filtro']) else "-"
            val_inicio = str(row['Inicio_Str'])[:5] if pd.notna(row['Inicio_Str']) else "-"
            val_fin = str(row['Fin_Str'])[:5] if pd.notna(row['Fin_Str']) else "-"
            minutos = f"{row['Tiempo (Min)']:.0f}"
            
            operador = " " + str(row['Operador'])[:22]
            detalle_str = " " + str(row[col_detalle]) if col_detalle in row and pd.notna(row[col_detalle]) else " Sin detalle"

            pdf.cell(w_f, 6, val_fecha, border='B', align='C')
            pdf.cell(w_i, 6, val_inicio, border='B', align='C')
            pdf.cell(w_f2, 6, val_fin, border='B', align='C')
            pdf.cell(w_d, 6, clean_text(detalle_str[:60]), border='B', align='L')
            pdf.cell(w_m, 6, minutos, border='B', align='C')
            pdf.cell(w_o, 6, clean_text(operador), border='B', align='L', ln=True)

    # ==================================
    # RECORRIDO POR CADA GRUPO 
    # ==================================
    for g in grupos_area:
        pdf.add_page()
        pdf.set_link(links_grupos[g]) 
        
        pdf.set_font("Times", 'B', 16)
        pdf.set_text_color(*theme_color)
        pdf.cell(0, 10, clean_text(f"SECCIÓN GRUPO: {g}"), ln=True, align='L', border='B')
        pdf.ln(5)

        df_pdf_g = df_pdf[df_pdf['Grupo_Máquina'] == g] if not df_pdf.empty else pd.DataFrame()
        df_prod_pdf_g = df_prod_pdf[df_prod_pdf['Grupo_Máquina'] == g] if not df_prod_pdf.empty else pd.DataFrame()
        
        m_g = {'OEE': 0, 'DISPONIBILIDAD': 0, 'PERFORMANCE': 0, 'CALIDAD': 0}
        maq_del_grupo = [m for m, grp in MAQUINAS_MAP.items() if grp == g]
        if not oee_target_df.empty:
            df_g_oee = oee_target_df[oee_target_df['Máquina'].isin(maq_del_grupo)]
            if not df_g_oee.empty:
                m_g = df_g_oee[['OEE', 'DISPONIBILIDAD', 'PERFORMANCE', 'CALIDAD']].mean().to_dict()

        if df_pdf_g.empty and df_prod_pdf_g.empty and m_g.get('OEE', 0) == 0:
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, clean_text("No hay registros documentados para este grupo en el periodo."), ln=True)
            continue

        print_section_title(pdf, "1. Resumen OEE del Grupo", theme_color)
        print_pdf_metric_row(pdf, f"Total {g}", m_g)
        
        for maq in maq_del_grupo:
            if not oee_target_df.empty:
                df_m_oee = oee_target_df[oee_target_df['Máquina'] == maq]
                if not df_m_oee.empty:
                    print_pdf_metric_row(pdf, f"   > {maq}", df_m_oee.iloc[0].to_dict())
        pdf.ln(3)

        check_space(pdf, 50)
        print_section_title(pdf, "2. Horarios y Tiempo de Apertura", theme_color)
        
        if not df_pdf_g.empty and 'Inicio_Str' in df_pdf_g.columns:
            tiempos_list = []
            for (maq, fecha), grp in df_pdf_g.groupby(['Máquina', 'Fecha_Filtro']):
                intervals = []
                for _, r in grp.iterrows():
                    ini = parse_time_to_mins(r['Inicio_Str'])
                    fin = parse_time_to_mins(r['Fin_Str'])
                    if ini is not None and fin is not None:
                        if fin < ini and (ini - fin) > 720: fin += 1440
                        intervals.append([ini, fin])
                
                if not intervals: continue
                intervals.sort(key=lambda x: x[0])
                merged = [intervals[0]]
                for current in intervals[1:]:
                    last = merged[-1]
                    if current[0] <= last[1]: last[1] = max(last[1], current[1])
                    else: merged.append(current)
                
                total_active = sum(iv[1] - iv[0] for iv in merged)
                min_i, max_f = merged[0][0], merged[-1][1]
                tiempo_bruto = max_f - min_i
                unregistered_time = max(0, tiempo_bruto - total_active)
                tiempos_list.append({'Máquina': maq, 'Inicio': min_i, 'Fin': max_f, 'Total': total_active, 'NoReg': unregistered_time, 'Fecha': fecha})
                
            df_horarios = pd.DataFrame(tiempos_list)
            
            if not df_horarios.empty:
                df_res = df_horarios.sort_values('Máquina') if p_tipo == "Diario" else df_horarios.groupby('Máquina').mean().reset_index().sort_values('Máquina')
                col_h1, col_h2, col_h3, col_h4 = ("Hora Inicio", "Hora Cierre", "Apertura Neta", "No Registrado") if p_tipo == "Diario" else ("Inicio Prom.", "Cierre Prom.", "Apertura Neta Prom.", "No Reg. Prom.")
                
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(46, 7, clean_text("Maquina"), border=1, align='L', fill=True)
                pdf.cell(28, 7, clean_text(col_h1), border=1, align='C', fill=True)
                pdf.cell(28, 7, clean_text(col_h2), border=1, align='C', fill=True)
                pdf.cell(44, 7, clean_text(col_h3), border=1, align='C', fill=True)
                pdf.cell(44, 7, clean_text(col_h4), border=1, align='C', ln=True, fill=True)
                
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 9)
                for _, r in df_res.iterrows():
                    pdf.cell(46, 7, " " + clean_text(str(r['Máquina'])[:22]), border=1, align='L')
                    pdf.cell(28, 7, clean_text(mins_to_time_str(r['Inicio'])), border=1, align='C')
                    pdf.cell(28, 7, clean_text(mins_to_time_str(r['Fin'])), border=1, align='C')
                    pdf.cell(44, 7, clean_text(mins_to_duration_str(r['Total'])), border=1, align='C')
                    pdf.cell(44, 7, clean_text(mins_to_duration_str(r['NoReg'])), border=1, align='C', ln=True)
                pdf.ln(5)
            else:
                pdf.cell(0, 8, clean_text("No hay datos de horarios validos en este grupo."), ln=True)
        else:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, clean_text("Sin datos de horarios documentados para el grupo."), ln=True)

        check_space(pdf, 40)
        print_section_title(pdf, "3. Analisis de Tiempos por Máquina", theme_color)
        
        if not df_pdf_g.empty:
            
            for maq in sorted(df_pdf_g['Máquina'].unique()):
                df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
                
                # Distribución de horas según el Clasificador Estricto
                t_prod = df_maq[df_maq['Estado_Global'] == 'Producción']['Tiempo (Min)'].sum()
                t_falla = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']['Tiempo (Min)'].sum()
                t_parada = df_maq[df_maq['Estado_Global'] == 'Parada Programada']['Tiempo (Min)'].sum()
                t_proy = df_maq[df_maq['Estado_Global'] == 'Proyecto']['Tiempo (Min)'].sum()
                t_desc = df_maq[df_maq['Estado_Global'] == 'Descanso']['Tiempo (Min)'].sum()
                
                if sum([t_prod, t_falla, t_parada, t_proy, t_desc]) == 0: continue
                    
                check_space(pdf, 60)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(*comp_color)
                pdf.cell(0, 9, clean_text(f"  MÁQUINA: {maq}"), border=0, ln=True, fill=True)
                pdf.ln(2)
                
                # --- NUEVA TABLA RESUMEN 5 COLUMNAS ---
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(38, 7, "Produccion", border=1, align='C', fill=True)
                pdf.cell(38, 7, "Fallas/Gestion", border=1, align='C', fill=True)
                pdf.cell(38, 7, "Paradas Prog.", border=1, align='C', fill=True)
                pdf.cell(38, 7, "Proyecto", border=1, align='C', fill=True)
                pdf.cell(38, 7, "Descansos", border=1, align='C', ln=True, fill=True)
                
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 9)
                pdf.cell(38, 7, clean_text(mins_to_duration_str(t_prod)), border=1, align='C')
                pdf.cell(38, 7, clean_text(mins_to_duration_str(t_falla)), border=1, align='C')
                pdf.cell(38, 7, clean_text(mins_to_duration_str(t_parada)), border=1, align='C')
                pdf.cell(38, 7, clean_text(mins_to_duration_str(t_proy)), border=1, align='C')
                pdf.cell(38, 7, clean_text(mins_to_duration_str(t_desc)), border=1, align='C', ln=True)
                pdf.ln(4)
                
                # --- DETALLE FALLAS Y GESTIÓN ---
                df_maq_fallas = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']
                if not df_maq_fallas.empty:
                    check_space(pdf, 60)
                    pdf.set_font("Arial", 'B', 10)
                    pdf.set_text_color(*comp_color)
                    pdf.cell(0, 6, clean_text("> Top 3 Fallas (por tiempo):"), ln=True)

                    agg_f = df_maq_fallas.groupby('Detalle_Final')['Tiempo (Min)'].sum().reset_index().sort_values('Tiempo (Min)', ascending=False).head(3)
                    total_falla_maq = t_falla if t_falla > 0 else 1
                    agg_f['Label'] = agg_f.apply(lambda r: f" {str(r['Detalle_Final'])[:45]} — {r['Tiempo (Min)']:.0f} min ({(r['Tiempo (Min)']/total_falla_maq)*100:.1f}%)", axis=1)
                    
                    fig_top3 = px.bar(agg_f, x='Tiempo (Min)', y='Detalle_Final', orientation='h', text='Label')
                    fig_top3.update_traces(marker_color=hex_comp, textposition='outside', textfont=dict(size=13, color='black'), cliponaxis=False)
                    fig_top3.update_layout(height=140, width=700, margin=dict(t=5, b=5, l=10, r=400), plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(title='', autorange="reversed", showticklabels=False))
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
                        fig_top3.write_image(tmp_chart.name, engine="kaleido")
                        pdf.image(tmp_chart.name, w=150)
                        os.remove(tmp_chart.name)
                
                    pdf.set_font("Arial", 'B', 9)
                    pdf.set_text_color(*comp_color)
                    pdf.cell(0, 6, clean_text(">> Detalle de Tiempos Perdidos (Fallas y Gestión):"), ln=True)
                    dibujar_tabla_eventos_detallada(df_maq_fallas, 'Detalle_Final')
                    pdf.ln(4)

                # --- DETALLE PARADAS PROGRAMADAS ---
                df_maq_paradas = df_maq[df_maq['Estado_Global'] == 'Parada Programada']
                if not df_maq_paradas.empty:
                    check_space(pdf, 40)
                    pdf.set_font("Arial", 'B', 9)
                    pdf.set_text_color(*theme_color) 
                    pdf.cell(0, 6, clean_text(">> Detalle de Paradas Programadas:"), ln=True)
                    dibujar_tabla_eventos_detallada(df_maq_paradas, 'Detalle_Final')
                    pdf.ln(4)

                # --- APARTADO EXCLUSIVO DE PROYECTOS ---
                df_maq_proy = df_maq[df_maq['Estado_Global'] == 'Proyecto']
                if not df_maq_proy.empty:
                    check_space(pdf, 40)
                    pdf.set_font("Arial", 'B', 9)
                    pdf.set_text_color(0, 102, 204) # Azul Proyectos
                    pdf.cell(0, 6, clean_text(">> Detalle de Horas de Proyecto Registradas:"), ln=True)
                    dibujar_tabla_eventos_detallada(df_maq_proy, 'Detalle_Final')
                    pdf.ln(4)
                    
        if not df_pdf_g.empty:
            check_space(pdf, 90)
            print_section_title(pdf, "4. Resumen Visual de Tiempos (Global y Paradas)", theme_color)
            
            col1_x = 10
            col2_x = 105
            y_base = pdf.get_y()
            
            # --- TORTA 1: ESTADO GLOBAL ---
            resumen_global = df_pdf_g.groupby('Estado_Global')['Tiempo (Min)'].sum().reset_index()
            fig_g = px.pie(resumen_global, values='Tiempo (Min)', names='Estado_Global', hole=0.4, 
                           title="Distribución General (Hs)", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_g.update_layout(width=350, height=270, margin=dict(t=30, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.1))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
                fig_g.write_image(tmp1.name, engine="kaleido")
                pdf.image(tmp1.name, x=col1_x, y=y_base, w=90)
                os.remove(tmp1.name)

            # --- TORTA 2: ESPECÍFICO FALLAS / GESTIÓN (POR ÁREA/MACRO) ---
            df_fallas_grupo = df_pdf_g[df_pdf_g['Estado_Global'] == 'Falla/Gestión']
            if not df_fallas_grupo.empty:
                resumen_fallas = df_fallas_grupo.groupby('Categoria_Macro')['Tiempo (Min)'].sum().reset_index()
                
                fig_p = px.pie(resumen_fallas, values='Tiempo (Min)', names='Categoria_Macro', hole=0.4, 
                               title="Fallas y Gestión por Área (Hs)", color_discrete_sequence=px.colors.qualitative.Set1)
                
                fig_p.update_layout(width=350, height=270, margin=dict(t=30, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.1))
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
                    fig_p.write_image(tmp2.name, engine="kaleido")
                    pdf.image(tmp2.name, x=col2_x, y=y_base, w=90)
                    os.remove(tmp2.name)
            else:
                pdf.set_xy(col2_x + 10, y_base + 30)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(100)
                pdf.cell(0, 10, clean_text("Sin Fallas o Gestión registradas."))

            pdf.set_y(y_base + 75)
            pdf.ln(5)

        if not df_prod_pdf_g.empty:
            check_space(pdf, 80)
            print_section_title(pdf, "5. Produccion por Maquina", theme_color)
            prod_maq = df_prod_pdf_g.groupby('Máquina')[['Buenas', 'Retrabajo', 'Observadas']].sum().reset_index()
            fig_prod = px.bar(prod_maq, x='Máquina', y=['Buenas', 'Retrabajo', 'Observadas'], barmode='stack', color_discrete_sequence=chart_bars, text_auto=True)
            fig_prod.update_layout(width=800, height=300, margin=dict(t=20, b=40, l=20, r=20), plot_bgcolor='rgba(0,0,0,0)')
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile3:
                fig_prod.write_image(tmpfile3.name, engine="kaleido")
                pdf.image(tmpfile3.name, w=155)
                os.remove(tmpfile3.name)
                
            pdf.ln(3)
            check_space(pdf, 30)
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(*theme_color)
            pdf.cell(0, 7, clean_text("Desglose por Codigo de Producto:"), ln=True)
            
            setup_table_header(pdf, theme_color)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(40, 7, "Maquina", border=1, fill=True)
            pdf.cell(60, 7, "Codigo de Producto", border=1, fill=True)
            pdf.cell(25, 7, "Buenas", border=1, align='C', fill=True)
            pdf.cell(25, 7, "Retrabajo", border=1, align='C', fill=True)
            pdf.cell(30, 7, "Observadas", border=1, align='C', ln=True, fill=True)
            
            setup_table_row(pdf)
            pdf.set_font("Arial", '', 9)
            
            df_prod_group = df_prod_pdf_g.groupby(['Máquina', 'Código'])[['Buenas', 'Retrabajo', 'Observadas']].sum().reset_index().sort_values('Máquina')
            for _, row in df_prod_group.iterrows():
                pdf.cell(40, 7, " " + clean_text(str(row['Máquina'])[:25]), border='B')
                pdf.cell(60, 7, " " + clean_text(str(row['Código'])[:40]), border='B') 
                pdf.cell(25, 7, clean_text(str(int(row['Buenas']))), border='B', align='C')
                pdf.cell(25, 7, clean_text(str(int(row['Retrabajo']))), border='B', align='C')
                pdf.cell(30, 7, clean_text(str(int(row['Observadas']))), border='B', align='C', ln=True)
            pdf.ln(5)

    # ==================================
    # SECCIÓN FINAL OPERARIOS
    # ==================================
    pdf.add_page()
    pdf.set_link(link_perfo)
    pdf.set_font("Times", 'B', 16)
    pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text(f"SECCIÓN FINAL: PERFORMANCE Y TIEMPOS"), ln=True, align='L', border='B')
    pdf.ln(5)
    
    print_section_title(pdf, "Performance de Operarios General", theme_color)
    
    if not op_target_df.empty:
        df_filt = op_target_df[op_target_df['Fábrica'].astype(str).str.contains(area, case=False, na=False)].sort_values('PERFORMANCE', ascending=False)
        
        check_space(pdf, 30)
        setup_table_header(pdf, theme_color)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(100, 7, clean_text("Operador"), border=1, fill=True)
        pdf.cell(60, 7, clean_text("Fabrica"), border=1, fill=True)
        pdf.cell(30, 7, clean_text("Performance"), border=1, align='C', ln=True, fill=True)
        
        setup_table_row(pdf)
        pdf.set_font("Arial", '', 9)
        
        for _, row in df_filt.iterrows():
            perf_val = int(round(pd.to_numeric(row['PERFORMANCE'], errors='coerce') or 0))
            pdf.cell(100, 7, " " + clean_text(str(row['Operador'])[:50]), border='B')
            pdf.cell(60, 7, " " + clean_text(str(row['Fábrica'])[:30]), border='B')
            
            if perf_val >= 90: pdf.set_text_color(33, 195, 84)
            elif perf_val >= 80: pdf.set_text_color(200, 150, 0)
            else: pdf.set_text_color(220, 20, 20)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(30, 7, clean_text(str(perf_val) + "%"), border='B', align='C', ln=True)
            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Arial", '', 9)
        pdf.ln(5)

    pdf.set_link(link_tiempos) 
    def agregar_tabla_tiempos(titulo, db_col):
        check_space(pdf, 30)
        print_section_title(pdf, titulo, theme_color)
        
        if not op_target_df.empty and db_col in op_target_df.columns:
            df_temp = op_target_df[op_target_df['Fábrica'].astype(str).str.contains(area, case=False, na=False)]
            df_filtrado = df_temp[df_temp[db_col] > 0].sort_values(db_col, ascending=False)
            
            if not df_filtrado.empty:
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(100, 7, clean_text("Operador"), border=1, align='L', fill=True)
                pdf.cell(90, 7, clean_text("Total Acumulado (Min)"), border=1, align='C', ln=True, fill=True)
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 9)
                for _, r in df_filtrado.iterrows():
                    pdf.cell(100, 7, " " + clean_text(r['Operador']), border=1)
                    pdf.cell(90, 7, f"{r[db_col]:.1f}", border=1, align='C', ln=True)
                pdf.ln(5)
            else:
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 8, clean_text("No se registraron tiempos para este evento en el periodo."), ln=True)

    agregar_tabla_tiempos("Tiempo de Bano Acumulado (Min)", "BathTime")
    agregar_tabla_tiempos("Tiempo de Refrigerio Acumulado (Min)", "BreakTime")

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    with open(temp_pdf.name, "rb") as f: pdf_bytes = f.read()
    os.remove(temp_pdf.name)
    return pdf_bytes

# ==========================================
# 6. BOTONES DE EXPORTACIÓN EN PANTALLA
# ==========================================
with col_p3:
    st.write("**3. Generar y Descargar:**")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Preparar Reporte ESTAMPADO", use_container_width=True):
            with st.spinner("Conectando con wii_bi y construyendo PDF..."):
                try:
                    pdf_data = crear_pdf("Estampado", pdf_label, pdf_df_oee_target, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo)
                    st.download_button("Descargar PDF Estampado", data=pdf_data, file_name=f"Estampado_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    with col_btn2:
        if st.button("Preparar Reporte SOLDADURA", use_container_width=True):
            with st.spinner("Conectando con wii_bi y construyendo PDF..."):
                try:
                    pdf_data = crear_pdf("Soldadura", pdf_label, pdf_df_oee_target, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo)
                    st.download_button("Descargar PDF Soldadura", data=pdf_data, file_name=f"Soldadura_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
