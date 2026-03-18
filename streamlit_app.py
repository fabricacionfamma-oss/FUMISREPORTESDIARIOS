import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tempfile
import os
from fpdf import FPDF

# ==========================================
# 0. DICCIONARIO DE MÁQUINAS Y GRUPOS FUMISCOR
# ==========================================
MAQUINAS_MAP = {
    # === ESTAMPADO (Base actual según imagen) ===
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

    # === SOLDADURA (Base actual según imagen) ===
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
    st.write("Seleccione los parámetros para generar y descargar los reportes consolidados.")
with col_btn:
    st.write("") 
    if st.button("Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ==========================================
# 2. CARGA DE DATOS
# ==========================================
@st.cache_data(ttl=300)
def load_data():
    try:
        try:
            url_base = st.secrets["connections"]["gsheets"]["spreadsheet"].strip()
        except Exception:
            st.error("Atención: No se encontró la configuración de secretos (.streamlit/secrets.toml).")
            return [pd.DataFrame()] * 8

        gid_datos = "0"
        gid_oee_diario = "1767654796"
        gid_prod = "315437448"
        gid_op_diario = "354131379"
        gid_oee_sem = "2079886194"
        gid_oee_men = "1696631148"
        gid_op_sem = "2038636509"
        gid_op_men = "1171574188"
        
        base_export = url_base.split("/edit")[0] + "/export?format=csv&gid="
        
        def process_df(url, is_daily=False):
            try:
                df = pd.read_csv(url)
            except Exception: return pd.DataFrame()
            
            cols_num = ['Tiempo (Min)', 'Buenas', 'Retrabajo', 'Observadas', 'OEE', 'Disponibilidad', 'Performance', 'Calidad', 'Eficiencia']
            for c in cols_num:
                matches = [col for col in df.columns if c.lower() in col.lower()]
                for match in matches:
                    df[match] = df[match].astype(str).str.replace(',', '.')
                    df[match] = df[match].str.replace('%', '')
                    df[match] = pd.to_numeric(df[match], errors='coerce').fillna(0.0)
            
            col_fecha = next((c for c in df.columns if 'fecha' in c.lower() and 'inicio' not in c.lower() and 'fin' not in c.lower()), None)
            if col_fecha:
                df['Fecha_DT'] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
                df['Fecha_Filtro'] = df['Fecha_DT'].dt.normalize()
                if is_daily:
                    df = df.dropna(subset=['Fecha_Filtro'])
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('').astype(str).str.strip()
            return df

        return (
            process_df(base_export + gid_datos, is_daily=True), 
            process_df(base_export + gid_oee_diario, is_daily=True), 
            process_df(base_export + gid_prod, is_daily=True), 
            process_df(base_export + gid_op_diario, is_daily=True),
            process_df(base_export + gid_oee_sem, is_daily=False),
            process_df(base_export + gid_oee_men, is_daily=False),
            process_df(base_export + gid_op_sem, is_daily=False),
            process_df(base_export + gid_op_men, is_daily=False)
        )
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return [pd.DataFrame()] * 8

df_raw, df_oee_diario, df_prod_raw, df_op_diario_raw, df_oee_sem, df_oee_men, df_op_sem_raw, df_op_men_raw = load_data()

if df_raw.empty:
    st.warning("No hay datos cargados en la base principal.")
    st.stop()

# ==========================================
# 3. INTERFAZ: CONFIGURACIÓN PDF
# ==========================================
col_p1, col_p2, col_p3 = st.columns([1, 1.2, 1.5])

with col_p1:
    st.write("**1. Tipo de Reporte:**")
    pdf_tipo = st.radio("Período:", ["Diario", "Semanal", "Mensual"], horizontal=True, label_visibility="collapsed")

pdf_ini, pdf_fin = None, None
pdf_df_oee_target = pd.DataFrame()
pdf_df_op_target = pd.DataFrame()
pdf_label = ""

with col_p2:
    st.write("**2. Seleccione el Período:**")
    if pdf_tipo == "Diario":
        min_d = df_raw['Fecha_Filtro'].min().date() if not df_raw.empty else pd.to_datetime("today").date()
        max_d = df_raw['Fecha_Filtro'].max().date() if not df_raw.empty else pd.to_datetime("today").date()
        pdf_fecha = st.date_input("Día para PDF:", value=max_d, min_value=min_d, max_value=max_d, label_visibility="collapsed")
        
        pdf_ini, pdf_fin = pd.to_datetime(pdf_fecha), pd.to_datetime(pdf_fecha)
        pdf_df_oee_target = df_oee_diario[df_oee_diario['Fecha_Filtro'] == pdf_ini]
        pdf_df_op_target = df_op_diario_raw[df_op_diario_raw['Fecha_Filtro'] == pdf_ini]
        pdf_label = f"Día {pdf_fecha.strftime('%d-%m-%Y')}"
        
    elif pdf_tipo == "Semanal":
        if not df_oee_sem.empty:
            col_sem = df_oee_sem.columns[0]
            opciones_sem = [s for s in df_oee_sem[col_sem].unique() if s.strip() != "" and str(s).lower() != "nan"]
            pdf_sem = st.selectbox("Semana para PDF:", opciones_sem, label_visibility="collapsed")
            pdf_df_oee_target = df_oee_sem[df_oee_sem[col_sem].astype(str) == str(pdf_sem)]
            col_sem_op = df_op_sem_raw.columns[0] if not df_op_sem_raw.empty else None
            if col_sem_op:
                pdf_df_op_target = df_op_sem_raw[df_op_sem_raw[col_sem_op].astype(str) == str(pdf_sem)]
            pdf_label = f"Semana {pdf_sem}"
            col_ini_p = next((c for c in pdf_df_oee_target.columns if 'inicio' in c.lower()), None)
            col_fin_p = next((c for c in pdf_df_oee_target.columns if 'fin' in c.lower()), None)
            if col_ini_p and col_fin_p and not pdf_df_oee_target.empty:
                pdf_ini = pd.to_datetime(pdf_df_oee_target.iloc[0][col_ini_p], dayfirst=True, errors='coerce')
                pdf_fin = pd.to_datetime(pdf_df_oee_target.iloc[0][col_fin_p], dayfirst=True, errors='coerce')
        else:
            st.warning("No hay datos semanales.")
                
    elif pdf_tipo == "Mensual":
        if not df_oee_men.empty:
            col_mes = df_oee_men.columns[0]
            opciones_mes = [m for m in df_oee_men[col_mes].unique() if m.strip() != "" and str(m).lower() != "nan"]
            pdf_mes = st.selectbox("Mes para PDF:", opciones_mes, label_visibility="collapsed")
            pdf_df_oee_target = df_oee_men[df_oee_men[col_mes].astype(str) == str(pdf_mes)]
            col_mes_op = df_op_men_raw.columns[0] if not df_op_men_raw.empty else None
            if col_mes_op:
                pdf_df_op_target = df_op_men_raw[df_op_men_raw[col_mes_op].astype(str) == str(pdf_mes)]
            pdf_label = f"Mes {pdf_mes}"
            col_ini_p = next((c for c in pdf_df_oee_target.columns if 'inicio' in c.lower()), None)
            col_fin_p = next((c for c in pdf_df_oee_target.columns if 'fin' in c.lower()), None)
            if col_ini_p and col_fin_p and not pdf_df_oee_target.empty:
                pdf_ini = pd.to_datetime(pdf_df_oee_target.iloc[0][col_ini_p], dayfirst=True, errors='coerce')
                pdf_fin = pd.to_datetime(pdf_df_oee_target.iloc[0][col_fin_p], dayfirst=True, errors='coerce')
        else:
            st.warning("No hay datos mensuales.")

# ==========================================
# 4. FUNCIONES HELPER
# ==========================================
def parse_time_to_mins(t_str):
    try:
        t = str(t_str).strip()
        if t in ['nan', 'None', '', '-']: return None
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

def mins_to_time_str(m):
    if pd.isna(m) or m is None: return "-"
    m = int(m) % 1440
    return f"{m//60:02d}:{m%60:02d}"

def mins_to_duration_str(m):
    if pd.isna(m) or m is None: return "-"
    m = int(m)
    return f"{m//60:02d}:{m%60:02d} hs"

class ReportePDF(FPDF):
    def __init__(self, area, fecha_str, theme_color):
        super().__init__()
        self.area = area
        self.fecha_str = fecha_str
        self.theme_color = theme_color

    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 30)
        self.set_font("Times", 'B', 16)
        self.set_text_color(*self.theme_color)
        self.cell(0, 10, clean_text(f"REPORTE GERENCIAL - {self.area.upper()}"), ln=True, align='R')
        self.set_font("Arial", 'I', 9)
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
    if pdf.get_y() + required_height > (pdf.h - 15):
        pdf.add_page()

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

def get_metrics_direct(name_filter, target_df):
    m = {'OEE': 0.0, 'DISP': 0.0, 'PERF': 0.0, 'CAL': 0.0}
    if target_df.empty: return m
    mask = target_df.apply(lambda row: row.astype(str).str.upper().str.contains(name_filter.upper()), axis=1)
    datos = target_df[mask.any(axis=1)]
    if not datos.empty:
        fila = datos.iloc[0] 
        for key, col_search in {'OEE':['OEE'], 'DISP':['DISPONIBILIDAD', 'DISP'], 'PERF':['PERFORMANCE', 'PERFO'], 'CAL':['CALIDAD', 'CAL']}.items():
            actual_col = next((c for c in datos.columns if any(x in c.upper() for x in col_search)), None)
            if actual_col:
                val_str = str(fila[actual_col]).replace('%', '').replace(',', '.').strip()
                v = pd.to_numeric(val_str, errors='coerce')
                if pd.notna(v): m[key] = float(v/100 if v > 1.1 else v)
    return m

def set_pdf_color(pdf, val):
    if val < 0.85: pdf.set_text_color(220, 20, 20)
    elif val <= 0.95: pdf.set_text_color(200, 150, 0)
    else: pdf.set_text_color(33, 195, 84)

def print_pdf_metric_row(pdf, prefix, m):
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text(f"{prefix} | OEE: "))
    set_pdf_color(pdf, m['OEE'])
    pdf.write(7, f"{m['OEE']:.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Disp: "))
    set_pdf_color(pdf, m['DISP'])
    pdf.write(7, f"{m['DISP']:.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Perf: "))
    set_pdf_color(pdf, m['PERF'])
    pdf.write(7, f"{m['PERF']:.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text("  |  Cal: "))
    set_pdf_color(pdf, m['CAL'])
    pdf.write(7, f"{m['CAL']:.1%}")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)

# ==========================================
# 5. MOTOR GENERADOR DEL PDF
# ==========================================
def crear_pdf(area, label_reporte, oee_target_df, op_target_df, ini_date, fin_date, p_tipo):
    if area.upper() == "ESTAMPADO":
        theme_color = (0, 128, 128) # Teal
        chart_bars = ['#008080', '#66B2B2', '#B2D8D8']
        grupos_area = GRUPOS_ESTAMPADO
    else:
        theme_color = (178, 34, 34) # Crimson
        chart_bars = ['#B22222', '#D98880', '#F2D7D5']
        grupos_area = GRUPOS_SOLDADURA
        
    hex_theme = '#%02x%02x%02x' % theme_color

    if ini_date is not None and fin_date is not None:
        df_pdf_raw = df_raw[(df_raw['Fecha_Filtro'] >= ini_date) & (df_raw['Fecha_Filtro'] <= fin_date)]
        df_prod_pdf_raw = df_prod_raw[(df_prod_raw['Fecha_Filtro'] >= ini_date) & (df_prod_raw['Fecha_Filtro'] <= fin_date)] if not df_prod_raw.empty else pd.DataFrame()
    else:
        df_pdf_raw = pd.DataFrame(columns=df_raw.columns)
        df_prod_pdf_raw = pd.DataFrame(columns=df_prod_raw.columns)

    # --- LIMPIEZA DE NOMBRES DE MÁQUINAS ---
    mapa_limpio = {str(k).strip().upper(): v for k, v in MAQUINAS_MAP.items()}

    # Filtramos la fábrica
    df_pdf = df_pdf_raw[df_pdf_raw['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
    
    # Mapeamos limpiando la columna 'Máquina'
    df_pdf['Grupo_Máquina'] = df_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')
    
    df_prod_pdf = pd.DataFrame()
    if not df_prod_pdf_raw.empty:
        df_prod_pdf = df_prod_pdf_raw[(df_prod_pdf_raw['Máquina'].astype(str).str.contains(area, case=False, na=False)) | 
                                      (df_prod_pdf_raw['Máquina'].isin(df_pdf['Máquina'].unique()))].copy()
        df_prod_pdf['Grupo_Máquina'] = df_prod_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    pdf = ReportePDF(area, label_reporte, theme_color)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- CREACIÓN DE LINKS PARA ÍNDICE ---
    links_grupos = {g: pdf.add_link() for g in grupos_area}
    link_perfo = pdf.add_link()
    link_tiempos = pdf.add_link()

    # --- PORTADA / ÍNDICE ---
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

    # =========================================================
    # RECORRIDO POR CADA GRUPO (NÚCLEO DEL REPORTE)
    # =========================================================
    for g in grupos_area:
        pdf.add_page()
        pdf.set_link(links_grupos[g]) 
        
        pdf.set_font("Times", 'B', 16)
        pdf.set_text_color(*theme_color)
        pdf.cell(0, 10, clean_text(f"SECCIÓN GRUPO: {g}"), ln=True, align='L', border='B')
        pdf.ln(5)

        df_pdf_g = df_pdf[df_pdf['Grupo_Máquina'] == g]
        df_prod_pdf_g = df_prod_pdf[df_prod_pdf['Grupo_Máquina'] == g]
        m_g = get_metrics_direct(g, oee_target_df)
        
        if df_pdf_g.empty and df_prod_pdf_g.empty and m_g['OEE'] == 0:
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, clean_text("No hay registros documentados para este grupo en el periodo seleccionado."), ln=True)
            continue

        # --- 1. OEE DEL GRUPO Y SUS MÁQUINAS ---
        print_section_title(pdf, "1. Resumen OEE del Grupo", theme_color)
        print_pdf_metric_row(pdf, f"Total {g}", m_g)
        
        maquinas_del_grupo = [m for m, grp in MAQUINAS_MAP.items() if grp == g]
        for maq in maquinas_del_grupo:
            m_maq = get_metrics_direct(maq, oee_target_df)
            if any(v > 0 for v in m_maq.values()):
                print_pdf_metric_row(pdf, f"   > {maq}", m_maq)
        pdf.ln(3)

        # --- 2. HORARIOS Y APERTURA ---
        check_space(pdf, 50)
        print_section_title(pdf, "2. Horarios y Tiempo de Apertura", theme_color)
        col_inicio = next((c for c in df_pdf_g.columns if 'inicio' in c.lower() or 'desde' in c.lower()), None)
        col_fin = next((c for c in df_pdf_g.columns if 'fin' in c.lower() or 'hasta' in c.lower()), None)
        
        if col_inicio and col_fin and not df_pdf_g.empty:
            tiempos_list = []
            for (maq, fecha), grp in df_pdf_g.groupby(['Máquina', 'Fecha_Filtro']):
                g_ini = grp[col_inicio].apply(parse_time_to_mins).dropna()
                g_fin = grp[col_fin].apply(parse_time_to_mins).dropna()
                if g_ini.empty or g_fin.empty: continue
                
                min_i, max_f = g_ini.min(), g_fin.max()
                if max_f < min_i and (min_i - max_f) > 720: max_f += 1440
                tiempos_list.append({'Máquina': maq, 'Inicio': min_i, 'Fin': max_f, 'Total': max_f - min_i})
                
            df_horarios = pd.DataFrame(tiempos_list)
            
            if not df_horarios.empty:
                df_res = df_horarios.sort_values('Máquina') if p_tipo == "Diario" else df_horarios.groupby('Máquina').mean().reset_index().sort_values('Máquina')
                col_h1, col_h2, col_h3 = ("Hora Inicio", "Hora Cierre", "Tiempo Operativo") if p_tipo == "Diario" else ("Inicio Prom.", "Cierre Prom.", "Apertura Prom.")
                
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(60, 7, clean_text("Maquina"), border=1, fill=True)
                pdf.cell(45, 7, clean_text(col_h1), border=1, align='C', fill=True)
                pdf.cell(45, 7, clean_text(col_h2), border=1, align='C', fill=True)
                pdf.cell(40, 7, clean_text(col_h3), border=1, align='C', ln=True, fill=True)
                
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 9)
                for _, r in df_res.iterrows():
                    pdf.cell(60, 7, clean_text(str(r['Máquina'])[:30]), border=1)
                    pdf.cell(45, 7, clean_text(mins_to_time_str(r['Inicio'])), border=1, align='C')
                    pdf.cell(45, 7, clean_text(mins_to_time_str(r['Fin'])), border=1, align='C')
                    pdf.cell(40, 7, clean_text(mins_to_duration_str(r['Total'])), border=1, align='C', ln=True)
            else:
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 8, clean_text("No hay datos de horarios validos en este grupo."), ln=True)
        else:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, clean_text("Sin datos de horarios documentados para el grupo."), ln=True)

        # --- 3. ANÁLISIS DE FALLAS (PARETO OPTIMIZADO) ---
        df_fallas_area = df_pdf_g[df_pdf_g['Nivel Evento 1'].astype(str).str.contains('FALLAS', case=False, na=False)]
        
        if not df_fallas_area.empty and 'Nivel Evento 3' in df_fallas_area.columns:
            check_space(pdf, 110)
            print_section_title(pdf, "3. Analisis de Fallas del Grupo", theme_color)
            
            agg_fallas = df_fallas_area.groupby('Nivel Evento 3').agg(
                Tiempo=('Tiempo (Min)', 'sum'),
                Maquinas=('Máquina', lambda x: ', '.join(sorted(set(str(m) for m in x if str(m).strip() and str(m).lower() != 'nan'))))
            ).reset_index()
            
            top_fallas = agg_fallas.sort_values('Tiempo', ascending=False).head(5)
            top_fallas['Falla_Label'] = top_fallas.apply(lambda r: f"{r['Nivel Evento 3']} ({r['Maquinas']})" if r['Maquinas'] else r['Nivel Evento 3'], axis=1)
            top_fallas['% Acumulado'] = (top_fallas['Tiempo'].cumsum() / top_fallas['Tiempo'].sum()) * 100
            
            fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
            fig_pareto.add_trace(go.Bar(x=top_fallas['Falla_Label'], y=top_fallas['Tiempo'], marker_color=hex_theme, text=top_fallas['Tiempo'].round(1), textposition='outside'), secondary_y=False)
            fig_pareto.add_trace(go.Scatter(x=top_fallas['Falla_Label'], y=top_fallas['% Acumulado'], mode='lines+markers', line=dict(color='red', width=3)), secondary_y=True)
            
            # --- AJUSTE DE MARGENES PARA QUE RESPIRE EL GRÁFICO ---
            fig_pareto.update_layout(
                width=800, 
                height=500, # Más alto
                margin=dict(t=20, b=160, l=20, r=20), # Margen inferior mucho más grande (b=160)
                plot_bgcolor='rgba(0,0,0,0)', 
                showlegend=False
            )
            fig_pareto.update_xaxes(tickangle=-45) # Letras en diagonal
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                fig_pareto.write_image(tmpfile.name, engine="kaleido")
                pdf.image(tmpfile.name, w=160)
                os.remove(tmpfile.name)
            
            pdf.ln(3)
            maquinas_con_fallas = sorted(df_fallas_area['Máquina'].unique())
            for maq in maquinas_con_fallas:
                check_space(pdf, 25)
                pdf.set_font("Arial", 'B', 9)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 7, clean_text(f"Maquina: {maq}"), ln=True)
                
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(20, 7, clean_text("Fecha"), border=1, align='C', fill=True)
                pdf.cell(15, 7, clean_text("Inicio"), border=1, align='C', fill=True)
                pdf.cell(15, 7, clean_text("Fin"), border=1, align='C', fill=True)
                pdf.cell(80, 7, clean_text("Falla"), border=1, fill=True)
                pdf.cell(15, 7, clean_text("Min"), border=1, align='C', fill=True)
                pdf.cell(45, 7, clean_text("Operador"), border=1, ln=True, fill=True)
                
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 8)
                df_maq = df_fallas_area[df_fallas_area['Máquina'] == maq]
                
                cols_dup = [c for c in [col_inicio, col_fin, 'Nivel Evento 3', 'Operador'] if c is not None]
                if cols_dup: df_maq = df_maq.drop_duplicates(subset=cols_dup)
                df_maq = df_maq.sort_values(['Fecha_Filtro', 'Tiempo (Min)'], ascending=[False, False])
                
                for _, row in df_maq.iterrows():
                    val_fecha = pd.to_datetime(row['Fecha_Filtro']).strftime('%d/%m') if pd.notna(row['Fecha_Filtro']) else "-"
                    val_inicio = str(row[col_inicio])[:5] if col_inicio and str(row[col_inicio]) != 'nan' else "-"
                    val_fin = str(row[col_fin])[:5] if col_fin and str(row[col_fin]) != 'nan' else "-"
                    pdf.cell(20, 6, clean_text(val_fecha), border='B', align='C')
                    pdf.cell(15, 6, clean_text(val_inicio), border='B', align='C')
                    pdf.cell(15, 6, clean_text(val_fin), border='B', align='C')
                    pdf.cell(80, 6, clean_text(str(row['Nivel Evento 3'])[:55]), border='B')
                    pdf.cell(15, 6, clean_text(f"{row['Tiempo (Min)']:.1f}"), border='B', align='C')
                    pdf.cell(45, 6, clean_text(str(row['Operador'])[:25]), border='B', ln=True)
                pdf.ln(3) 
        else:
            check_space(pdf, 25)
            print_section_title(pdf, "3. Analisis de Fallas", theme_color)
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 7, clean_text("No se registraron fallas para este grupo en el periodo."), ln=True)

        # --- 4. PRODUCCIÓN VS PARADA ---
        if not df_pdf_g.empty:
            check_space(pdf, 70)
            print_section_title(pdf, "4. Relacion Produccion vs Parada", theme_color)
            df_pdf_g['Tipo'] = df_pdf_g['Evento'].apply(lambda x: 'Producción' if 'Producción' in str(x) else 'Parada')
            fig_pie = px.pie(df_pdf_g, values='Tiempo (Min)', names='Tipo', hole=0.4, color='Tipo', color_discrete_map={'Producción':hex_theme, 'Parada':'#D62728'})
            
            fig_pie.update_layout(width=400, height=250, margin=dict(t=10, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile2:
                fig_pie.write_image(tmpfile2.name, engine="kaleido")
                pdf.image(tmpfile2.name, w=100)
                os.remove(tmpfile2.name)
            pdf.ln(3)
        
        # --- 5. PRODUCCIÓN POR MÁQUINA ---
        if not df_prod_pdf_g.empty and 'Buenas' in df_prod_pdf_g.columns:
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
            pdf.cell(40, 7, clean_text("Maquina"), border=1, fill=True)
            pdf.cell(60, 7, clean_text("Codigo de Producto"), border=1, fill=True)
            pdf.cell(25, 7, clean_text("Buenas"), border=1, align='C', fill=True)
            pdf.cell(25, 7, clean_text("Retrabajo"), border=1, align='C', fill=True)
            pdf.cell(30, 7, clean_text("Observadas"), border=1, align='C', ln=True, fill=True)
            
            setup_table_row(pdf)
            pdf.set_font("Arial", '', 9)
            c_cod = next((c for c in df_prod_pdf_g.columns if 'código' in c.lower() or 'codigo' in c.lower()), 'Código')
            
            df_prod_group = df_prod_pdf_g.groupby(['Máquina', c_cod])[['Buenas', 'Retrabajo', 'Observadas']].sum().reset_index().sort_values('Máquina')
            for _, row in df_prod_group.iterrows():
                pdf.cell(40, 7, clean_text(str(row['Máquina'])[:25]), border='B')
                pdf.cell(60, 7, clean_text(str(row[c_cod])[:40]), border='B') 
                pdf.cell(25, 7, clean_text(str(int(row['Buenas']))), border='B', align='C')
                pdf.cell(25, 7, clean_text(str(int(row['Retrabajo']))), border='B', align='C')
                pdf.cell(30, 7, clean_text(str(int(row['Observadas']))), border='B', align='C', ln=True)
            pdf.ln(5)

    # =========================================================
    # SECCIÓN FINAL: PERFORMANCE DE OPERARIOS (GENERAL)
    # =========================================================
    pdf.add_page()
    pdf.set_link(link_perfo)
    pdf.set_font("Times", 'B', 16)
    pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text(f"SECCIÓN FINAL: PERFORMANCE Y TIEMPOS"), ln=True, align='L', border='B')
    pdf.ln(5)
    
    print_section_title(pdf, "Performance de Operarios General", theme_color)
    
    if not op_target_df.empty:
        col_op = next((c for c in op_target_df.columns if 'operador' in c.lower() or 'nombre' in c.lower()), op_target_df.columns[1] if len(op_target_df.columns)>1 else op_target_df.columns[0])
        col_perf = op_target_df.columns[5] if p_tipo == "Diario" else (op_target_df.columns[7] if len(op_target_df.columns) > 7 else None)
        col_area = op_target_df.columns[14] if p_tipo == "Diario" else (op_target_df.columns[1] if len(op_target_df.columns) > 1 else None)
        
        if col_perf and col_area:
            op_maq_map = {}
            if not df_prod_pdf.empty:
                col_maq_prod = next((c for c in df_prod_pdf.columns if 'máquina' in c.lower() or 'maquina' in c.lower()), None)
                cols_ops = df_prod_pdf.columns[14:min(20, len(df_prod_pdf.columns))] if len(df_prod_pdf.columns) > 14 else []
                
                if col_maq_prod and len(cols_ops) > 0:
                    for _, r in df_prod_pdf.iterrows():
                        maq = str(r.get(col_maq_prod, '')).strip()
                        if maq and maq.lower() != 'nan':
                            for c in cols_ops:
                                op = str(r.get(c, '')).strip().upper()
                                if op and op not in ('NAN', 'NONE'):
                                    op_maq_map.setdefault(op, set()).add(maq)

            op_target_df['Perf_Clean'] = pd.to_numeric(op_target_df[col_perf].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce').fillna(0)
            if op_target_df['Perf_Clean'].mean() <= 1.5 and op_target_df['Perf_Clean'].mean() > 0:
                op_target_df['Perf_Clean'] = op_target_df['Perf_Clean'] * 100
            
            df_grouped = op_target_df.copy()
            df_grouped['Perf_Int'] = df_grouped['Perf_Clean'].round().astype(int)
            df_grouped['Op_Upper'] = df_grouped[col_op].astype(str).str.strip().str.upper()
            df_grouped['Maquinas'] = df_grouped['Op_Upper'].apply(lambda x: ', '.join(sorted(op_maq_map.get(x, []))) if op_maq_map.get(x) else '-')

            if p_tipo == "Diario":
                df_grouped = df_grouped.groupby(['Op_Upper', col_op, col_area, 'Maquinas']).agg(Perf_Int=('Perf_Int', 'mean')).reset_index()
                df_grouped['Perf_Int'] = df_grouped['Perf_Int'].round().astype(int)

            df_filt = df_grouped[df_grouped[col_area].astype(str).str.contains(area, case=False, na=False)].sort_values('Perf_Int', ascending=False)
            
            check_space(pdf, 30)
            setup_table_header(pdf, theme_color)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(60, 7, clean_text("Operador"), border=1, fill=True)
            pdf.cell(100, 7, clean_text("Maquina(s) Asignada(s)"), border=1, fill=True)
            pdf.cell(30, 7, clean_text("Performance"), border=1, align='C', ln=True, fill=True)
            
            setup_table_row(pdf)
            pdf.set_font("Arial", '', 9)
            
            if df_filt.empty:
                pdf.cell(190, 7, clean_text("Sin registros para esta area."), border='B', align='C', ln=True)
            else:
                for _, row in df_filt.iterrows():
                    perf_val = row['Perf_Int']
                    pdf.cell(60, 7, clean_text(str(row[col_op])[:35]), border='B')
                    m_str = str(row.get('Maquinas', '-'))
                    pdf.cell(100, 7, clean_text(m_str[:57] + "..." if len(m_str)>60 else m_str), border='B')
                    
                    if perf_val >= 90: pdf.set_text_color(33, 195, 84)
                    elif perf_val >= 80: pdf.set_text_color(200, 150, 0)
                    else: pdf.set_text_color(220, 20, 20)
                    
                    pdf.set_font("Arial", 'B', 9)
                    pdf.cell(30, 7, clean_text(str(perf_val) + "%"), border='B', align='C', ln=True)
                    pdf.set_text_color(50, 50, 50)
                    pdf.set_font("Arial", '', 9)
            pdf.ln(5)
        else:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, clean_text("Faltan columnas de base de datos para generar este cuadro."), ln=True)

    # =========================================================
    # TABLAS DE PROMEDIO: BAÑO Y REFRIGERIO
    # =========================================================
    pdf.set_link(link_tiempos) 
    
    def agregar_tabla_tiempos(titulo, regex_keyword):
        check_space(pdf, 30)
        print_section_title(pdf, titulo, theme_color)
        
        req_cols = ['Operador', 'Tiempo (Min)', 'Nivel Evento 1']
        if all(col in df_pdf.columns for col in req_cols):
            df_temp = pd.DataFrame({
                'Operario': df_pdf['Operador'],
                'Tiempo': pd.to_numeric(df_pdf['Tiempo (Min)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0),
                'Evento': df_pdf['Nivel Evento 1'].astype(str)
            })
            df_filtrado = df_temp[df_temp['Evento'].str.contains(regex_keyword, case=False, na=False)]
            
            if not df_filtrado.empty:
                resumen = df_filtrado.groupby('Operario').agg(Total_Min=('Tiempo', 'sum'), Eventos=('Tiempo', 'count'), Promedio=('Tiempo', 'mean')).reset_index().sort_values('Promedio', ascending=False)
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(70, 7, clean_text("Operador"), border=1, align='C', fill=True)
                pdf.cell(30, 7, clean_text("Cant. Eventos"), border=1, align='C', fill=True)
                pdf.cell(30, 7, clean_text("Total (Min)"), border=1, align='C', fill=True)
                pdf.cell(30, 7, clean_text("Promedio"), border=1, align='C', ln=True, fill=True)
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 9)
                for _, r in resumen.iterrows():
                    pdf.cell(70, 7, clean_text(r['Operario'] if str(r['Operario']).strip() else "Desconocido"), border=1)
                    pdf.cell(30, 7, str(int(r['Eventos'])), border=1, align='C')
                    pdf.cell(30, 7, f"{r['Total_Min']:.1f}", border=1, align='C')
                    pdf.cell(30, 7, f"{r['Promedio']:.1f}", border=1, align='C', ln=True)
                pdf.ln(5)
            else:
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 8, clean_text("No se registraron tiempos para este evento en el periodo."), ln=True)
        else:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, clean_text("Faltan las columnas 'Operador', 'Tiempo (Min)' o 'Nivel Evento 1' en los datos."), ln=True)

    agregar_tabla_tiempos("Tiempo Promedio de Bano por Operario (Planta)", "BAÑO|BANO")
    agregar_tabla_tiempos("Tiempo Promedio de Refrigerio por Operario (Planta)", "REFRIGERIO")

    # FINALIZAR PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    with open(temp_pdf.name, "rb") as f: pdf_bytes = f.read()
    os.remove(temp_pdf.name)
    return pdf_bytes

# ==========================================
# 7. BOTONES DE EXPORTACIÓN EN PANTALLA
# ==========================================
with col_p3:
    st.write("**3. Generar y Descargar:**")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Preparar Reporte ESTAMPADO", use_container_width=True):
            with st.spinner("Construyendo documento PDF modular..."):
                try:
                    pdf_data = crear_pdf("Estampado", pdf_label, pdf_df_oee_target, pdf_df_op_target, pdf_ini, pdf_fin, pdf_tipo)
                    st.download_button("Descargar PDF Estampado", data=pdf_data, file_name=f"Estampado_{pdf_label.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    with col_btn2:
        if st.button("Preparar Reporte SOLDADURA", use_container_width=True):
            with st.spinner("Construyendo documento PDF modular..."):
                try:
                    pdf_data = crear_pdf("Soldadura", pdf_label, pdf_df_oee_target, pdf_df_op_target, pdf_ini, pdf_fin, pdf_tipo)
                    st.download_button("Descargar PDF Soldadura", data=pdf_data, file_name=f"Soldadura_{pdf_label.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
