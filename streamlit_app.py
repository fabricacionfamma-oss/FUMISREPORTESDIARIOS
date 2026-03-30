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
    # === SOLDADURA ===
    "SOP-003": "PRP", "SOP-005": "PRP", "SOP-008": "PRP", "SOP-009": "PRP", "SOP-010": "PRP",
    "SOP-017": "PRP", "SOP-018": "PRP", "SOP-019": "PRP", "SOP-020": "PRP", "SOP-022": "PRP",
    "DOB-001": "DOBLADORA", "DOB-002": "DOBLADORA", "DOB-003": "DOBLADORA", "DOB-004": "DOBLADORA",
    "Cel1 - Rob13 - RUEDA AUX.": "CELDA SOLDADURA", "Cel2 - Rob1 - ALMOHADON": "CELDA SOLDADURA",
    "Celda 01 Fumis": "CELDA SOLDADURA RENAULT", "Celda 02 Fumis": "CELDA SOLDADURA RENAULT",
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
            q_op = f"SELECT op.Name as Operador, p.Factory as Fábrica, AVG(p.Performance) as PERFORMANCE, SUM(p.BathTime) as BathTime, SUM(p.BreakTime) as BreakTime FROM OPER_M_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Month = {mes} AND p.Year = {anio} GROUP BY op.Name, p.Factory"
        else:
            q_oee = f"SELECT c.Name as Máquina, AVG(p.Oee) as OEE, AVG(p.Availability) as DISPONIBILIDAD, AVG(p.Performance) as PERFORMANCE, AVG(p.Quality) as CALIDAD FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name"
            q_prod = f"SELECT c.Name as Máquina, pr.Code as Código, SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY c.Name, pr.Code"
            q_op = f"SELECT op.Name as Operador, p.Factory as Fábrica, AVG(p.Performance) as PERFORMANCE, SUM(p.BathTime) as BathTime, SUM(p.BreakTime) as BreakTime FROM OPER_D_01 p JOIN OPERATOR op ON p.OperatorId = op.OperatorId WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' GROUP BY op.Name, p.Factory"

        # Consulta de Eventos Crudos (Nivel 4 + ID para evitar duplicados)
        q_event = f"""
            SELECT e.Id as Evento_Id, c.Name as Máquina, e.Started as Inicio, e.Finish as Fin, 
                   e.Interval as [Tiempo (Min)], 
                   t1.Name as [Nivel Evento 1], t2.Name as [Nivel Evento 2], 
                   t3.Name as [Nivel Evento 3], t4.Name as [Nivel Evento 4],
                   op.Name as Operador, e.Date as Fecha_Filtro, f.Name as Fábrica
            FROM EVENT_01 e
            LEFT JOIN CELL c ON e.CellId = c.CellId
            LEFT JOIN EVENTTYPE t1 ON e.EventTypeLevel1 = t1.EventTypeId
            LEFT JOIN EVENTTYPE t2 ON e.EventTypeLevel2 = t2.EventTypeId
            LEFT JOIN EVENTTYPE t3 ON e.EventTypeLevel3 = t3.EventTypeId
            LEFT JOIN EVENTTYPE t4 ON e.EventTypeLevel4 = t4.EventTypeId
            LEFT JOIN FACTORY f ON e.FactoryId = f.FactoryId
            LEFT JOIN EVENT_OPERATOR_01 eo ON e.Id = eo.EventId
            LEFT JOIN OPERATOR op ON eo.OperatorId = op.OperatorId
            WHERE e.Date BETWEEN '{ini_str}' AND '{fin_str}'
        """
        df_raw = conn.query(q_event)
        df_oee_target = conn.query(q_oee)
        df_prod_target = conn.query(q_prod)
        df_op_target = conn.query(q_op)

        if not df_raw.empty:
            df_raw['Fecha_Filtro'] = pd.to_datetime(df_raw['Fecha_Filtro']).dt.date
            df_raw['Inicio_Str'] = pd.to_datetime(df_raw['Inicio']).dt.strftime('%H:%M')
            df_raw['Fin_Str'] = pd.to_datetime(df_raw['Fin']).dt.strftime('%H:%M')
            df_raw['Tiempo (Min)'] = pd.to_numeric(df_raw['Tiempo (Min)'], errors='coerce').fillna(0)
            
            # --- CONSOLIDAR OPERADORES DUPLICADOS ---
            cols_grupo = [c for c in df_raw.columns if c != 'Operador']
            df_raw = df_raw.groupby(cols_grupo, dropna=False).agg({'Operador': lambda x: ' / '.join(x.dropna().unique())}).reset_index()

            # --- LÓGICA DE CLASIFICACIÓN ---
            def categorizar_estado(row):
                texto = f"{row['Nivel Evento 1']} {row['Nivel Evento 2']} {row['Nivel Evento 3']} {row['Nivel Evento 4']}".upper()
                if 'PRODUCCION' in texto or 'PRODUCCIÓN' in texto: return 'Producción'
                if 'PROYECTO' in texto: return 'Proyecto'
                if any(kw in texto for kw in ['BAÑO', 'BANO', 'REFRIGERIO']): return 'Descanso'
                if 'PARADA PROGRAMADA' in texto: return 'Parada Programada'
                return 'Falla/Gestión'

            def clasificar_macro(row):
                n1, n2 = str(row['Nivel Evento 1']).upper(), str(row['Nivel Evento 2']).upper()
                if 'GESTION' in n1 or 'GESTIÓN' in n1: return 'Gestión'
                if 'FALLA' in n1: return n2.title() if n2 not in ['NAN', 'NONE', ''] else 'Falla'
                return n1.title() if n1 not in ['NAN', 'NONE', ''] else 'Sin Clasificar'

            df_raw['Estado_Global'] = df_raw.apply(categorizar_estado, axis=1)
            df_raw['Categoria_Macro'] = df_raw.apply(clasificar_macro, axis=1)

            def obtener_detalle(row):
                niveles = [str(row[f'Nivel Evento {i}']) for i in range(1, 5)]
                validos = [n for n in niveles if n.lower() not in ['none', 'nan', '']]
                if not validos: return "Sin detalle"
                ultimo = validos[-1]
                if row['Estado_Global'] == 'Falla/Gestión':
                    return f"[{row['Categoria_Macro']}] {ultimo}"
                return ultimo

            df_raw['Detalle_Final'] = df_raw.apply(obtener_detalle, axis=1)

        return df_raw, df_oee_target, df_prod_target, df_op_target
    except Exception as e:
        st.error(f"Error DB: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# 3. INTERFAZ: CONFIGURACIÓN
# ==========================================
col_p1, col_p2, col_p3 = st.columns([1, 1.2, 1.5])
today = pd.to_datetime("today").date()

with col_p1:
    pdf_tipo = st.radio("Período:", ["Diario", "Semanal", "Mensual"], horizontal=True)

with col_p2:
    if pdf_tipo == "Diario":
        pdf_fecha = st.date_input("Día:", value=today)
        pdf_ini = pdf_fin = pd.to_datetime(pdf_fecha)
        pdf_label = f"Dia {pdf_fecha.strftime('%d-%m-%Y')}"
    elif pdf_tipo == "Semanal":
        fecha_ref = st.date_input("Semana de:", value=today)
        pdf_ini = pd.to_datetime(fecha_ref) - timedelta(days=pd.to_datetime(fecha_ref).weekday())
        pdf_fin = pdf_ini + timedelta(days=6)
        pdf_label = f"Semana {pdf_ini.strftime('%d/%m')} al {pdf_fin.strftime('%d/%m')}"
    else:
        mes_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        m_sel = st.selectbox("Mes", mes_list, index=today.month-1)
        a_sel = st.selectbox("Año", range(2024, 2030))
        pdf_ini = pd.to_datetime(f"{a_sel}-{mes_list.index(m_sel)+1}-01")
        pdf_fin = pdf_ini + timedelta(days=calendar.monthrange(a_sel, mes_list.index(m_sel)+1)[1]-1)
        pdf_label = f"{m_sel} {a_sel}"

df_raw, df_oee_target, df_prod_target, df_op_target = fetch_data_from_db(pdf_ini, pdf_fin, pdf_tipo)

# ==========================================
# 4. FUNCIONES PDF HELPERS
# ==========================================
def parse_time_to_mins(t_str):
    try:
        parts = str(t_str).split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except: return None

def mins_to_time_str(m):
    if pd.isna(m): return "-"
    return f"{int(m)//60:02d}:{int(m)%60:02d}"

class ReportePDF(FPDF):
    def __init__(self, area, fecha_str, theme_color):
        super().__init__()
        self.area, self.fecha_str, self.theme_color = area, fecha_str, theme_color
    def header(self):
        self.set_font("Arial", 'B', 16)
        self.set_text_color(*self.theme_color)
        self.cell(0, 10, f"REPORTE GERENCIAL - {self.area.upper()}", ln=True, align='R')
        self.set_font("Arial", '', 10); self.set_text_color(100)
        self.cell(0, 6, f"Periodo: {self.fecha_str}", ln=True, align='R'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font("Arial", "I", 8); self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

def clean_text(text): return str(text).encode('latin-1', 'replace').decode('latin-1')
def check_space(pdf, h):
    if pdf.get_y() + h > 270: pdf.add_page()
def setup_table_header(pdf, color):
    pdf.set_fill_color(*color); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 9)
def setup_table_row(pdf):
    pdf.set_fill_color(255); pdf.set_text_color(50); pdf.set_font("Arial", '', 9); pdf.set_draw_color(200)

def print_section_title(pdf, title, color):
    pdf.ln(4); pdf.set_font("Arial", 'B', 12); pdf.set_text_color(*color)
    pdf.cell(0, 6, clean_text(title), ln=True)
    pdf.set_draw_color(*color); pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x()+190, pdf.get_y()); pdf.ln(3)

# ==========================================
# 5. MOTOR GENERADOR PDF
# ==========================================
def crear_pdf(area, label_reporte, oee_target_df, op_target_df, prod_target_df, df_pdf_raw):
    if area.upper() == "ESTAMPADO":
        theme_color = (15, 76, 129) # Azul Marino
        comp_color = (52, 152, 219)  # Azul Claro
        chart_bars = ['#0F4C81', '#3498DB', '#AED6F1']
        pie_colors = px.colors.sequential.Blues_r
        grupos_area = GRUPOS_ESTAMPADO
    else:
        theme_color = (211, 84, 0) # Naranja Oscuro
        comp_color = (230, 126, 34) # Naranja
        chart_bars = ['#D35400', '#E67E22', '#FAD7A1']
        pie_colors = px.colors.sequential.Oranges_r
        grupos_area = GRUPOS_SOLDADURA

    pdf = ReportePDF(area, label_reporte, theme_color)
    pdf.add_page()
    
    # --- FILTRADO DE DATOS ---
    df_pdf = df_pdf_raw[df_pdf_raw['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
    
    # --- SECCIÓN POR GRUPO ---
    for g in grupos_area:
        pdf.add_page()
        print_section_title(pdf, f"SECCIÓN GRUPO: {g}", theme_color)
        
        maq_del_grupo = [m for m, grp in MAQUINAS_MAP.items() if grp == g]
        df_pdf_g = df_pdf[df_pdf['Máquina'].isin(maq_del_grupo)]
        
        for idx, maq in enumerate(sorted(df_pdf_g['Máquina'].unique())):
            df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
            
            t_prod = df_maq[df_maq['Estado_Global'] == 'Producción']['Tiempo (Min)'].sum()
            t_falla = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']['Tiempo (Min)'].sum()
            t_parada = df_maq[df_maq['Estado_Global'] == 'Parada Programada']['Tiempo (Min)'].sum()
            t_proy = df_maq[df_maq['Estado_Global'] == 'Proyecto']['Tiempo (Min)'].sum()
            t_desc = df_maq[df_maq['Estado_Global'] == 'Descanso']['Tiempo (Min)'].sum()
            
            if sum([t_prod, t_falla, t_parada, t_proy, t_desc]) == 0: continue

            check_space(pdf, 110)
            if idx > 0:
                pdf.ln(5); pdf.set_draw_color(220); pdf.set_line_width(0.8)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.set_line_width(0.2); pdf.ln(5)

            # Encabezado Máquina
            pdf.set_font("Arial", 'B', 12); pdf.set_text_color(255); pdf.set_fill_color(*comp_color)
            pdf.cell(0, 9, f"  MAQUINA: {maq}", ln=True, fill=True)
            pdf.set_font("Arial", 'I', 8); pdf.set_text_color(100); pdf.cell(0, 5, f"   Grupo: {g}", ln=True); pdf.ln(2)

            # Tabla Resumen 5 Columnas
            setup_table_header(pdf, theme_color)
            for c in ["Produccion", "Fallas/Gestion", "Paradas Prog.", "Proyecto", "Descansos"]:
                pdf.cell(38, 7, c, border=1, align='C', fill=True)
            pdf.ln()
            setup_table_row(pdf)
            for t in [t_prod, t_falla, t_parada, t_proy, t_desc]:
                pdf.cell(38, 7, f"{mins_to_time_str(t)} hs", border=1, align='C')
            pdf.ln(10)

            # Tablas de Detalle
            def dibujar_detalle(df_sub, titulo, color_t):
                if not df_sub.empty:
                    pdf.set_font("Arial", 'B', 9); pdf.set_text_color(*color_t)
                    pdf.cell(0, 6, f">> {titulo}:", ln=True); pdf.ln(1)
                    setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                    pdf.cell(18, 6, "Fecha", 1, 0, 'C', True); pdf.cell(14, 6, "Ini", 1, 0, 'C', True)
                    pdf.cell(14, 6, "Fin", 1, 0, 'C', True); pdf.cell(86, 6, "Detalle Sistema", 1, 0, 'L', True)
                    pdf.cell(13, 6, "Min", 1, 0, 'C', True); pdf.cell(45, 6, "Operador", 1, 1, 'L', True)
                    setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                    for _, r in df_sub.iterrows():
                        pdf.cell(18, 6, str(r['Fecha_Filtro'])[5:], 'B', 0, 'C')
                        pdf.cell(14, 6, r['Inicio_Str'], 'B', 0, 'C')
                        pdf.cell(14, 6, r['Fin_Str'], 'B', 0, 'C')
                        pdf.cell(86, 6, clean_text(r['Detalle_Final'][:55]), 'B', 0, 'L')
                        pdf.cell(13, 6, str(int(r['Tiempo (Min)'])), 'B', 0, 'C')
                        pdf.cell(45, 6, clean_text(str(r['Operador'])[:25]), 'B', 1, 'L')
                    pdf.ln(4)

            dibujar_detalle(df_maq[df_maq['Estado_Global'] == 'Falla/Gestión'], "Detalle Fallas y Gestión", (200, 0, 0))
            dibujar_detalle(df_maq[df_maq['Estado_Global'] == 'Parada Programada'], "Detalle Paradas Programadas", theme_color)
            dibujar_detalle(df_maq[df_maq['Estado_Global'] == 'Proyecto'], "Detalle de Proyectos", comp_color)

    # --- SECCIÓN 4: TORTAS GLOBALES ---
    pdf.add_page(); print_section_title(pdf, "4. Resumen Visual de Tiempos (Global del Grupo)", theme_color)
    y_base = pdf.get_y()
    
    # Torta 1: General
    fig1 = px.pie(df_pdf.groupby('Estado_Global')['Tiempo (Min)'].sum().reset_index(), values='Tiempo (Min)', names='Estado_Global', hole=0.4, color_discrete_sequence=pie_colors)
    fig1.update_layout(width=350, height=270, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
        fig1.write_image(tmp1.name, engine="kaleido"); pdf.image(tmp1.name, x=10, y=y_base, w=90); os.remove(tmp1.name)

    # Torta 2: Fallas por Área
    df_f_g = df_pdf[df_pdf['Estado_Global'] == 'Falla/Gestión']
    if not df_f_g.empty:
        fig2 = px.pie(df_f_g.groupby('Categoria_Macro')['Tiempo (Min)'].sum().reset_index(), values='Tiempo (Min)', names='Categoria_Macro', hole=0.4, color_discrete_sequence=pie_colors)
        fig2.update_layout(width=350, height=270, margin=dict(t=10, b=10, l=10, r=10))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
            fig2.write_image(tmp2.name, engine="kaleido"); pdf.image(tmp2.name, x=105, y=y_base, w=90); os.remove(tmp2.name)

    # --- SECCIÓN FINAL: OPERARIOS ---
    pdf.add_page(); print_section_title(pdf, "SECCIÓN FINAL: PERFORMANCE Y DESCANSOS", theme_color)
    
    # Tabla Performance
    df_p = df_op_target[df_op_target['Operador'].isin([o.strip() for sl in df_pdf['Operador'].dropna().unique() for o in sl.split('/')])].sort_values('PERFORMANCE', ascending=False)
    if not df_p.empty:
        print_section_title(pdf, "Performance de Operarios", comp_color)
        setup_table_header(pdf, theme_color); pdf.cell(100, 7, "Operador", 1); pdf.cell(60, 7, "Fabrica", 1); pdf.cell(30, 7, "Perf.", 1, 1, 'C', True)
        setup_table_row(pdf)
        for _, r in df_p.iterrows():
            pdf.cell(100, 7, f" {r['Operador']}", 'B'); pdf.cell(60, 7, area, 'B'); pdf.cell(30, 7, f"{r['PERFORMANCE']:.1f}%", 'B', 1, 'C')

    # Tablas de Descanso (Baño y Refrigerio separadas)
    def tabla_descansos_final(tipo_nombre, keywords):
        mask = df_pdf[['Nivel Evento 1','Nivel Evento 2','Nivel Evento 3','Nivel Evento 4']].apply(lambda x: any(isinstance(v, str) and any(k in v.upper() for k in keywords) for v in x), axis=1)
        df_d = df_pdf[mask]
        if not df_d.empty:
            print_section_title(pdf, f"Tiempo de {tipo_nombre} Acumulado", comp_color)
            # Agrupar por operador (considerando las barras '/')
            res = {}
            for _, r in df_d.iterrows():
                for o in str(r['Operador']).split('/'):
                    o = o.strip()
                    if o and o != '-':
                        if o not in res: res[o] = {'t': 0, 'c': 0}
                        res[o]['t'] += r['Tiempo (Min)']; res[o]['c'] += 1
            
            setup_table_header(pdf, theme_color); pdf.cell(100, 7, "Operador", 1); pdf.cell(45, 7, "Minutos", 1, 0, 'C', True); pdf.cell(45, 7, "Eventos", 1, 1, 'C', True)
            setup_table_row(pdf)
            for op, val in sorted(res.items(), key=lambda x: x[1]['t'], reverse=True):
                pdf.cell(100, 7, f" {op}", 'B'); pdf.cell(45, 7, f"{val['t']:.1f}", 'B', 0, 'C'); pdf.cell(45, 7, str(val['c']), 'B', 1, 'C')

    tabla_descansos_final("Bano", ["BAÑO", "BANO"])
    tabla_descansos_final("Refrigerio", ["REFRIGERIO"])

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    with open(temp_pdf.name, "rb") as f: bytes_data = f.read()
    os.remove(temp_pdf.name)
    return bytes_data

# ==========================================
# 6. BOTONES DE EXPORTACIÓN
# ==========================================
with col_p3:
    st.write("**Descargar Reportes:**")
    c1, c2 = st.columns(2)
    if c1.button("PDF ESTAMPADO", use_container_width=True):
        data = crear_pdf("Estampado", pdf_label, df_oee_target, df_op_target, df_prod_target, df_raw)
        st.download_button("Click aquí para descargar", data, f"Estampado_{pdf_label}.pdf", "application/pdf")
    if c2.button("PDF SOLDADURA", use_container_width=True):
        data = crear_pdf("Soldadura", pdf_label, df_oee_target, df_op_target, df_prod_target, df_raw)
        st.download_button("Click aquí para descargar", data, f"Soldadura_{pdf_label}.pdf", "application/pdf")
