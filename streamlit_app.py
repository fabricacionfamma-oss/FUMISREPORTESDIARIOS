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
# REQUISITO PARA IMÁGENES PNG (Kaleido)
# Asegúrate de tener instalado en tu entorno: pip install kaleido==0.2.1
# ==========================================

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
# FUNCION PARA LEER PIEZAS "H" DE GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=3600)
def get_piezas_h():
    url = "https://docs.google.com/spreadsheets/d/1mLnIC8B7mwmFZwthO0A32H3ZFfXSKt7vIUMBXEZxDJ0/export?format=csv&gid=0"
    try:
        df_h = pd.read_csv(url, header=None)
        piezas = df_h.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        return [p for p in piezas if p and p.lower() not in ['codigo', 'código', 'pieza', 'piezas']]
    except Exception as e:
        st.error(f"Error al cargar piezas H desde Google Sheets: {e}")
        return []

# ==========================================
# 2. CARGA Y LIMPIEZA DE DATOS DESDE SQL SERVER
# ==========================================
@st.cache_data(ttl=300)
def fetch_data_from_db(fecha_ini, fecha_fin, tipo_periodo, mes=None, anio=None, lista_piezas_h=None):
    try:
        conn = st.connection("wii_bi", type="sql")
        ini_str = fecha_ini.strftime('%Y-%m-%d')
        fin_str = fecha_fin.strftime('%Y-%m-%d')

        df_trend = pd.DataFrame()
        df_horarios = pd.DataFrame()
        df_piezas_excluidas = pd.DataFrame(columns=['Máquina', 'Code'])

        prod_where = ""
        if lista_piezas_h:
            piezas_str = ", ".join([f"'{p}'" for p in lista_piezas_h])
            prod_where = f" AND pr.Code NOT IN ({piezas_str}) "

        if tipo_periodo == "Mensual":
            # Extraer las piezas que EFECTIVAMENTE tuvieron producción para informar
            if lista_piezas_h:
                q_excluidas = f"""
                    SELECT DISTINCT c.Name as Máquina, pr.Code
                    FROM PROD_M_01 p 
                    JOIN CELL c ON p.CellId = c.CellId 
                    JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                    WHERE p.Month = {mes} AND p.Year = {anio} AND pr.Code IN ({piezas_str})
                """
                df_piezas_excluidas = conn.query(q_excluidas)

            q_prod = f"""
                SELECT c.Name as Máquina, pr.Code as Código, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas
                FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                WHERE p.Month = {mes} AND p.Year = {anio} {prod_where}
                GROUP BY c.Name, pr.Code
            """
            
            if lista_piezas_h:
                q_metrics = f"""
                    SELECT c.Name as Máquina, 
                           SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas,
                           SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada,
                           (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE,
                           (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD,
                           (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD,
                           (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE
                    FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                    WHERE p.Month = {mes} AND p.Year = {anio} {prod_where}
                    GROUP BY c.Name
                """
            else:
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

            q_metrics_std = f"""
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
            df_op_target = conn.query(q_op)
            
            if lista_piezas_h:
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
                    FROM PROD_M_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                    WHERE p.Year = {anio} AND p.Month <= {mes} {prod_where}
                    GROUP BY p.Month, c.Name
                """
            else:
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
            if lista_piezas_h:
                q_excluidas = f"""
                    SELECT DISTINCT c.Name as Máquina, pr.Code
                    FROM PROD_D_01 p 
                    JOIN CELL c ON p.CellId = c.CellId 
                    JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                    WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' AND pr.Code IN ({piezas_str})
                """
                df_piezas_excluidas = conn.query(q_excluidas)

            q_prod = f"""
                SELECT c.Name as Máquina, pr.Code as Código, 
                       SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas
                FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' {prod_where}
                GROUP BY c.Name, pr.Code
            """
            
            if lista_piezas_h:
                q_metrics = f"""
                    SELECT c.Name as Máquina, 
                           SUM(p.Good) as Buenas, SUM(p.Rework) as Retrabajo, SUM(p.Scrap) as Observadas,
                           SUM(p.ProductiveTime) as T_Operativo, SUM(p.DownTime) as T_Parada,
                           (SUM(p.Performance * p.ProductiveTime) / NULLIF(SUM(p.ProductiveTime), 0)) as PERFORMANCE,
                           (SUM(p.Availability * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as DISPONIBILIDAD,
                           (SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) / NULLIF(SUM(p.Good + p.Rework + p.Scrap), 0)) as CALIDAD,
                           (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE
                    FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId
                    WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' {prod_where}
                    GROUP BY c.Name
                """
            else:
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

            q_metrics_std = f"""
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
                SELECT op.Name as Operador, p.Factory as Fábrica,
                       p.Performance, p.ProductiveTime
                FROM OPER_D_01 p 
                JOIN OPERATOR op ON p.OperatorId = op.OperatorId 
                WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' 
            """
            df_op_raw = conn.query(q_op)
            
            if not df_op_raw.empty:
                df_op_raw['Performance'] = pd.to_numeric(df_op_raw['Performance'], errors='coerce').fillna(0)
                df_op_raw['ProductiveTime'] = pd.to_numeric(df_op_raw['ProductiveTime'], errors='coerce').fillna(0)
                df_op_raw['Perf_Num'] = df_op_raw['Performance'] * df_op_raw['ProductiveTime']
                
                df_op_raw['Fábrica'] = df_op_raw['Fábrica'].fillna('No Asignada')
                
                df_op_target = df_op_raw.groupby(['Operador', 'Fábrica']).agg(
                    Perf_Num=('Perf_Num', 'sum'),
                    ProductiveTime=('ProductiveTime', 'sum')
                ).reset_index()
                
                df_op_target['PERFORMANCE'] = df_op_target['Perf_Num'] / df_op_target['ProductiveTime'].replace(0, 1)
            else:
                df_op_target = pd.DataFrame()

            q_horarios = f"""
                WITH Tiempos_Turno AS (
                    SELECT CellId, TurnId, Date as Dia,
                           MIN(Started) as MinInicio,
                           MAX(Finish) as MaxFin
                    FROM EVENT_01
                    WHERE Date BETWEEN '{ini_str}' AND '{fin_str}'
                    GROUP BY CellId, TurnId, Date
                )
                SELECT c.Name as Máquina, tu.Name as Turno, t.Dia,
                       FORMAT(MIN(t.MinInicio), 'HH:mm') as Hora_Inicio,
                       FORMAT(MAX(t.MaxFin), 'HH:mm') as Hora_Cierre,
                       SUM(ISNULL(p.ProductiveTime, 0) + ISNULL(p.DownTime, 0)) as Apertura_Neta_Min,
                       CASE 
                           WHEN ISNULL(DATEDIFF(MINUTE, MIN(t.MinInicio), MAX(t.MaxFin)), 0) - SUM(ISNULL(p.ProductiveTime, 0) + ISNULL(p.DownTime, 0)) > 0 
                           THEN ISNULL(DATEDIFF(MINUTE, MIN(t.MinInicio), MAX(t.MaxFin)), 0) - SUM(ISNULL(p.ProductiveTime, 0) + ISNULL(p.DownTime, 0))
                           ELSE 0 
                       END as No_Registrado_Min
                FROM Tiempos_Turno t
                JOIN CELL c ON t.CellId = c.CellId
                JOIN TURN tu ON t.TurnId = tu.TurnId
                LEFT JOIN PROD_D_02 p ON t.CellId = p.CellId AND t.TurnId = p.TurnId AND t.Dia = p.Date
                GROUP BY c.Name, tu.Name, t.Dia
            """
            df_horarios = conn.query(q_horarios)

            if tipo_periodo == "Semanal":
                if lista_piezas_h:
                    q_trend_semanal = f"""
                        SELECT p.Date as Fecha_Filtro, c.Name as Máquina,
                               SUM(p.Oee * (p.ProductiveTime + p.DownTime)) as OEE_Num,
                               SUM(p.ProductiveTime + p.DownTime) as OEE_Den,
                               (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE,
                               SUM(p.Availability * (p.ProductiveTime + p.DownTime)) as Disp_Num,
                               SUM(p.Performance * p.ProductiveTime) as Perf_Num,
                               SUM(p.ProductiveTime) as T_Operativo,
                               SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) as Cal_Num,
                               SUM(p.Good + p.Rework + p.Scrap) as Piezas_Totales
                        FROM PROD_D_01 p JOIN CELL c ON p.CellId = c.CellId JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
                        WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}' {prod_where}
                        GROUP BY p.Date, c.Name
                    """
                else:
                    q_trend_semanal = f"""
                        SELECT p.Date as Fecha_Filtro, c.Name as Máquina,
                               SUM(p.Oee * (p.ProductiveTime + p.DownTime)) as OEE_Num,
                               SUM(p.ProductiveTime + p.DownTime) as OEE_Den,
                               (SUM(p.Oee * (p.ProductiveTime + p.DownTime)) / NULLIF(SUM(p.ProductiveTime + p.DownTime), 0)) as OEE,
                               SUM(p.Availability * (p.ProductiveTime + p.DownTime)) as Disp_Num,
                               SUM(p.Performance * p.ProductiveTime) as Perf_Num,
                               SUM(p.ProductiveTime) as T_Operativo,
                               SUM(p.Quality * (p.Good + p.Rework + p.Scrap)) as Cal_Num,
                               SUM(p.Good + p.Rework + p.Scrap) as Piezas_Totales
                        FROM PROD_D_03 p JOIN CELL c ON p.CellId = c.CellId
                        WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}'
                        GROUP BY p.Date, c.Name
                    """
                df_trend = conn.query(q_trend_semanal)
            else:
                df_trend = pd.DataFrame()

        df_prod_target = conn.query(q_prod)
        df_metrics = conn.query(q_metrics)
        df_metrics_std = conn.query(q_metrics_std)

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
                texto_completo = f"{row.get('Nivel Evento 1','')}\n{row.get('Nivel Evento 2','')}\n{row.get('Nivel Evento 3','')}\n{row.get('Nivel Evento 4','')} ".upper()
                if 'PRODUCCION' in texto_completo or 'PRODUCCIÓN' in texto_completo: return 'Producción'
                if 'PROYECTO' in texto_completo: return 'Proyecto'
                if 'BAÑO' in texto_completo or 'BANO' in texto_completo or 'REFRIGERIO' in texto_completo: return 'Descanso'
                if 'PARADA PROGRAMADA' in texto_completo: return 'Parada Programada'
                return 'Falla/Gestión'

            def clasificac_macro(row):
                n1 = str(row.get('Nivel Evento 1', '')).strip().upper()
                n2 = str(row.get('Nivel Evento 2', '')).strip().upper()
                if 'GESTION' in n1 or 'GESTIÓN' in n1: return 'Gestión'
                if 'FALLA' in n1: return n2.title() if n2 not in ['NAN', 'NONE', ''] else 'Falla (Sin área)'
                return n1.title() if n1 not in ['NAN', 'NONE', ''] else 'Sin Clasificar'

            df_raw['Estado_Global'] = df_raw.apply(categorizar_estado, axis=1)
            df_raw['Categoria_Macro'] = df_raw.apply(clasificac_macro, axis=1)

            def obtener_ultimo_nivel(row):
                niveles = [str(row.get(col, '')).strip() for col in ['Nivel Evento 1', 'Nivel Evento 2', 'Nivel Evento 3', 'Nivel Evento 4']]
                validos = [n for n in niveles if n.lower() not in ['none', 'nan', '', 'null']]
                if not validos: return "Sin detalle en sistema"
                ultimo = validos[-1]; macro = row['Categoria_Macro']
                if row['Estado_Global'] == 'Falla/Gestión':
                    if macro.upper() not in ultimo.upper(): return f"[{macro}] {ultimo}"
                return ultimo

            df_raw['Detalle_Final'] = df_raw.apply(obtener_ultimo_nivel, axis=1)

        return df_raw, df_prod_target, df_op_target, df_trend, df_metrics, df_horarios, df_metrics_std, df_piezas_excluidas

    except Exception as e:
        st.error(f"Error ejecutando consulta a base de datos wii_bi: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# 3. INTERFAZ: CONFIGURACIÓN PERIODO
# ==========================================
col_p1, col_p2, col_p3 = st.columns([1, 1.2, 2.0])

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

    st.markdown("---")
    ignorar_piezas_h = st.checkbox("Ignorar piezas H (Proyecto H)", value=False)
    lista_piezas_h = get_piezas_h() if ignorar_piezas_h else []
    
    if ignorar_piezas_h:
        st.success("✅ **Filtro Activado:** Se omitirán del reporte las piezas H que efectivamente hayan tenido producción en este período.")

df_raw, pdf_df_prod_target, pdf_df_op_target, df_trend, df_metrics, df_horarios, df_metrics_std, df_piezas_excluidas = fetch_data_from_db(pdf_ini, pdf_fin, pdf_tipo, mes=pdf_mes, anio=pdf_anio, lista_piezas_h=lista_piezas_h)

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
    if pd.isna(m) or m is None or m == 0: return "-"
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

def set_pdf_color_metric(pdf, val, metric_name):
    targets = {
        'OEE': 75.0,
        'DISPONIBILIDAD': 88.0,
        'PERFORMANCE': 90.0,
        'CALIDAD': 95.0
    }
    target = targets.get(metric_name.upper(), 85.0)
    
    if val >= target:
        pdf.set_text_color(33, 195, 84) # Verde
    else:
        pdf.set_text_color(220, 20, 20) # Rojo

def print_pdf_metric_row(pdf, prefix, m, m_std=None):
    pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
    pdf.write(7, clean_text(f"{prefix} | OEE: "))
    set_pdf_color_metric(pdf, m.get('OEE', 0), 'OEE'); pdf.write(7, f"{m.get('OEE', 0):.1f}%")
    
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Disp: "))
    set_pdf_color_metric(pdf, m.get('DISPONIBILIDAD', 0), 'DISPONIBILIDAD'); pdf.write(7, f"{m.get('DISPONIBILIDAD', 0):.1f}%")
    
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Perf: "))
    set_pdf_color_metric(pdf, m.get('PERFORMANCE', 0), 'PERFORMANCE'); pdf.write(7, f"{m.get('PERFORMANCE', 0):.1f}%")
    
    pdf.set_text_color(0, 0, 0); pdf.write(7, clean_text("  |  Cal: "))
    set_pdf_color_metric(pdf, m.get('CALIDAD', 0), 'CALIDAD'); pdf.write(7, f"{m.get('CALIDAD', 0):.1f}%")
    
    pdf.set_text_color(0, 0, 0); pdf.ln(7)

    # Imprimir línea secundaria con el OEE original (sin exclusiones)
    if m_std is not None and m_std.get('OEE', 0) != m.get('OEE', 0):
        pdf.set_font("Arial", 'I', 8); pdf.set_text_color(120, 120, 120)
        pdf.cell(10) # Margen izquierdo
        pdf.write(5, clean_text(f"(Usual c/ Piezas H - OEE: {m_std.get('OEE', 0):.1f}% | Disp: {m_std.get('DISPONIBILIDAD', 0):.1f}% | Perf: {m_std.get('PERFORMANCE', 0):.1f}% | Cal: {m_std.get('CALIDAD', 0):.1f}%)"))
        pdf.ln(5)

def add_image_safe(pdf, img_path, w_mm, h_mm, center=True):
    if pdf.get_y() + h_mm > 275:
        pdf.add_page()
    x = (210 - w_mm) / 2 if center else pdf.get_x()
    y = pdf.get_y()
    pdf.image(img_path, x=x, y=y, w=w_mm)
    pdf.set_y(y + h_mm + 5)


# ==========================================
# 5.A. MOTOR PARA RESUMEN EJECUTIVO (SOLO MENSUAL)
# ==========================================
def crear_pdf_resumen_ejecutivo(fecha_str, df_trend, df_metrics_pdf, df_metrics_std_pdf, df_piezas_excluidas):
    theme_color = (44, 62, 80) 
    pdf = ReportePDF("GLOBAL PLANTA - RESUMEN MENSUAL", fecha_str, theme_color)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ---------------------------------------------------------
    # PAGINA 1: RESUMEN EJECUTIVO POR PLANTA (GLOBAL)
    # ---------------------------------------------------------
    pdf.add_page()
    print_section_title(pdf, "RESUMEN EJECUTIVO: KPI POR PLANTA", theme_color)

    if not df_piezas_excluidas.empty:
        piezas_unicas = df_piezas_excluidas['Code'].unique()
        if len(piezas_unicas) > 0:
            pdf.set_font("Arial", 'I', 8); pdf.set_text_color(220, 20, 20)
            piezas_str = ", ".join(sorted(piezas_unicas))
            pdf.multi_cell(0, 4, clean_text(f"* Nota: Se calculan indicadores principales excluyendo los tiempos y producción de las siguientes piezas H detectadas en la planta: {piezas_str}"))
            pdf.ln(3)

    is_h_active = not df_piezas_excluidas.empty

    mapa_limpio = {str(k).strip().upper(): v for k, v in MAQUINAS_MAP.items()}
    def get_planta(maq_name):
        maq_upper = str(maq_name).strip().upper()
        grupo = mapa_limpio.get(maq_upper, 'OTRO')
        if grupo in GRUPOS_ESTAMPADO: return 'ESTAMPADO'
        if grupo == 'CELDA SOLDADURA RENAULT': return 'RENAULT' 
        if grupo in GRUPOS_SOLDADURA: return 'SOLDADURA'
        return 'OTRO'

    def process_metrics_df(df_met_raw):
        df_met_all = df_met_raw.copy()
        df_met_all['Planta'] = df_met_all['Máquina'].apply(get_planta)
        df_met_all['Grupo'] = df_met_all['Máquina'].apply(lambda x: mapa_limpio.get(str(x).strip().upper(), 'OTRO'))
        
        df_met_all['T_Planificado'] = df_met_all['T_Operativo'].fillna(0) + df_met_all['T_Parada'].fillna(0)
        df_met_all['Piezas_Totales'] = df_met_all['Buenas'].fillna(0) + df_met_all['Retrabajo'].fillna(0) + df_met_all['Observadas'].fillna(0)

        df_met_all['OEE_Num'] = df_met_all['OEE'].fillna(0) * df_met_all['T_Planificado']
        df_met_all['Disp_Num'] = df_met_all['DISPONIBILIDAD'].fillna(0) * df_met_all['T_Planificado']
        df_met_all['Perf_Num'] = df_met_all['PERFORMANCE'].fillna(0) * df_met_all['T_Operativo']
        df_met_all['Cal_Num'] = df_met_all['CALIDAD'].fillna(0) * df_met_all['Piezas_Totales']
        return df_met_all

    df_met_all = process_metrics_df(df_metrics_pdf)
    df_met_std = process_metrics_df(df_metrics_std_pdf)

    met_planta = df_met_all.groupby('Planta')[['OEE_Num', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Planificado', 'T_Operativo', 'Piezas_Totales']].sum()
    met_planta_std = df_met_std.groupby('Planta')[['OEE_Num', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Planificado', 'T_Operativo', 'Piezas_Totales']].sum()

    def calc_metrics(df_grp, idx_name):
        if idx_name in df_grp.index:
            row = df_grp.loc[idx_name]
            disp = row['Disp_Num'] / row['T_Planificado'] if row['T_Planificado'] > 0 else 0
            perf = row['Perf_Num'] / row['T_Operativo'] if row['T_Operativo'] > 0 else 0
            cal = row['Cal_Num'] / row['Piezas_Totales'] if row['Piezas_Totales'] > 0 else 0
            oee = (disp * perf * cal) / 10000 
            return oee, disp, perf, cal
        return 0, 0, 0, 0

    oee_est, disp_est, perf_est, cal_est = calc_metrics(met_planta, 'ESTAMPADO')
    std_est = calc_metrics(met_planta_std, 'ESTAMPADO') if is_h_active else None

    oee_sol, disp_sol, perf_sol, cal_sol = calc_metrics(met_planta, 'SOLDADURA')
    std_sol = calc_metrics(met_planta_std, 'SOLDADURA') if is_h_active else None

    def draw_kpi_row(pdf_obj, y, title, oee, disp, perf, cal, theme_col, std_metrics=None):
        pdf_obj.set_xy(10, y)
        pdf_obj.set_font("Arial", 'B', 12)
        pdf_obj.set_text_color(*theme_col)
        pdf_obj.cell(0, 6, clean_text(title), ln=1)
        y_boxes = pdf_obj.get_y() + 2
        
        w = 42; spacing = 5; x_start = 13.5
        
        def draw_box(pdf_inner, x, title_box, val, th_col):
            pdf_inner.set_xy(x, y_boxes)
            pdf_inner.set_font("Arial", 'B', 9)
            pdf_inner.set_fill_color(*th_col)
            pdf_inner.set_text_color(255, 255, 255)
            pdf_inner.cell(w, 8, clean_text(title_box), border=1, align='C', fill=True, ln=2)
            
            pdf_inner.set_fill_color(245, 245, 245)
            set_pdf_color_metric(pdf_inner, val, title_box)
            pdf_inner.set_font("Arial", 'B', 16)
            pdf_inner.cell(w, 12, f"{val:.1f}%", border=1, align='C', fill=True)
        
        draw_box(pdf_obj, x_start, "OEE", oee, theme_col)
        draw_box(pdf_obj, x_start + w + spacing, "DISPONIBILIDAD", disp, theme_col)
        draw_box(pdf_obj, x_start + 2*(w + spacing), "PERFORMANCE", perf, theme_col)
        draw_box(pdf_obj, x_start + 3*(w + spacing), "CALIDAD", cal, theme_col)
        
        y_boxes += 22
        if std_metrics and std_metrics[0] != oee:
            pdf_obj.set_xy(x_start, y_boxes)
            pdf_obj.set_font("Arial", 'I', 8)
            pdf_obj.set_text_color(100, 100, 100)
            pdf_obj.cell(0, 5, clean_text(f"* Usual c/ Piezas H (OEE: {std_metrics[0]:.1f}% | Disp: {std_metrics[1]:.1f}% | Perf: {std_metrics[2]:.1f}% | Cal: {std_metrics[3]:.1f}%)"), ln=1)
            y_boxes += 5

        return y_boxes + 5

    y_curr = pdf.get_y() + 5
    y_curr = draw_kpi_row(pdf, y_curr, "INDICADORES: ESTAMPADO", oee_est, disp_est, perf_est, cal_est, theme_color, std_est)
    y_curr += 8
    y_curr = draw_kpi_row(pdf, y_curr, "INDICADORES: SOLDADURA", oee_sol, disp_sol, perf_sol, cal_sol, theme_color, std_sol)

    meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}

    if not df_trend.empty:
        pdf.set_y(y_curr + 10)
        pdf.set_font("Arial", 'B', 12); pdf.set_text_color(*theme_color)
        pdf.cell(0, 6, clean_text("Evolución Mensual Histórica por Planta"), ln=True)

        df_trend_all = df_trend.copy()
        df_trend_all['Planta'] = df_trend_all['Máquina'].apply(get_planta)

        trend_planta = df_trend_all[df_trend_all['Planta'] != 'OTRO'].groupby(['Month', 'Planta'])[['OEE_Num', 'OEE_Den', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Operativo', 'Piezas_Totales']].sum().reset_index()
        
        trend_planta['DISP'] = (trend_planta['Disp_Num'] / trend_planta['OEE_Den']).fillna(0)
        trend_planta['PERF'] = (trend_planta['Perf_Num'] / trend_planta['T_Operativo']).fillna(0)
        trend_planta['CAL'] = (trend_planta['Cal_Num'] / trend_planta['Piezas_Totales']).fillna(0)
        trend_planta['OEE'] = (trend_planta['DISP'] * trend_planta['PERF'] * trend_planta['CAL']) / 10000

        trend_melt = trend_planta.melt(id_vars=['Month', 'Planta'], value_vars=['OEE', 'DISP', 'PERF', 'CAL'], var_name='Indicador', value_name='Valor')
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
        fig_glob.update_yaxes(rangemode="tozero")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_glob:
            fig_glob.write_image(tmp_glob.name, engine="kaleido")
            add_image_safe(pdf, tmp_glob.name, w_mm=190, h_mm=115, center=True)
            os.remove(tmp_glob.name)

    # ---------------------------------------------------------
    # PAGINA 2: OEE CONSOLIDADO POR GRUPOS
    # ---------------------------------------------------------
    pdf.add_page()
    print_section_title(pdf, "RESUMEN EJECUTIVO: OEE POR GRUPO", theme_color)
    
    met_grupo = df_met_all.groupby('Grupo')[['OEE_Num', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Planificado', 'T_Operativo', 'Piezas_Totales']].sum()
    met_grupo_std = df_met_std.groupby('Grupo')[['OEE_Num', 'Disp_Num', 'Perf_Num', 'Cal_Num', 'T_Planificado', 'T_Operativo', 'Piezas_Totales']].sum()
    
    y_curr = pdf.get_y() + 5
    for g in GRUPOS_ESTAMPADO + GRUPOS_SOLDADURA:
        if g in met_grupo.index:
            if y_curr > 230:
                pdf.add_page()
                print_section_title(pdf, "RESUMEN EJECUTIVO: OEE POR GRUPO (Cont.)", theme_color)
                y_curr = pdf.get_y() + 5
                
            oee_g, disp_g, perf_g, cal_g = calc_metrics(met_grupo, g)
            std_g = calc_metrics(met_grupo_std, g) if is_h_active else None

            y_curr = draw_kpi_row(pdf, y_curr, f"GRUPO: {g}", oee_g, disp_g, perf_g, cal_g, theme_color, std_g)
            y_curr += 8

    # ---------------------------------------------------------
    # PAGINAS 3..N : OEE Y GRÁFICA INDIVIDUAL POR MÁQUINA
    # ---------------------------------------------------------
    for g in GRUPOS_ESTAMPADO + GRUPOS_SOLDADURA:
        maquinas_grupo = sorted(df_met_all[df_met_all['Grupo'] == g]['Máquina'].unique())
        for maq in maquinas_grupo:
            pdf.add_page() 
            pdf.set_font("Times", 'B', 16)
            pdf.set_text_color(*theme_color)
            pdf.cell(0, 10, clean_text(f"REPORTE ESPECÍFICO DE MÁQUINA: {maq}"), ln=True, border='B')
            
            pdf.set_font("Arial", 'I', 10); pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, clean_text(f"Grupo perteneciente: {g}"), ln=True)
            pdf.ln(5)
            
            row_maq = df_met_all[df_met_all['Máquina'] == maq].iloc[0]
            oee_maq_individual = (row_maq['DISPONIBILIDAD'] * row_maq['PERFORMANCE'] * row_maq['CALIDAD']) / 10000

            std_maq_ind = None
            if is_h_active:
                row_std = df_met_std[df_met_std['Máquina'] == maq]
                if not row_std.empty:
                    row_std = row_std.iloc[0]
                    oee_std = (row_std['DISPONIBILIDAD'] * row_std['PERFORMANCE'] * row_std['CALIDAD']) / 10000
                    std_maq_ind = (oee_std, row_std['DISPONIBILIDAD'], row_std['PERFORMANCE'], row_std['CALIDAD'])

            y_curr = draw_kpi_row(pdf, pdf.get_y(), "INDICADORES DEL MES", oee_maq_individual, row_maq['DISPONIBILIDAD'], row_maq['PERFORMANCE'], row_maq['CALIDAD'], theme_color, std_maq_ind)
            
            if not df_trend.empty:
                df_t_maq = df_trend[df_trend['Máquina'] == maq].copy()
                if not df_t_maq.empty:
                    df_t_maq['DISP'] = (df_t_maq['Disp_Num'] / df_t_maq['OEE_Den']).fillna(0)
                    df_t_maq['PERF'] = (df_t_maq['Perf_Num'] / df_t_maq['T_Operativo']).fillna(0)
                    df_t_maq['CAL'] = (df_t_maq['Cal_Num'] / df_t_maq['Piezas_Totales']).fillna(0)
                    df_t_maq['OEE'] = (df_t_maq['DISP'] * df_t_maq['PERF'] * df_t_maq['CAL']) / 10000
                    
                    df_t_maq_melt = df_t_maq.melt(id_vars=['Month'], value_vars=['OEE', 'DISP', 'PERF', 'CAL'], var_name='Indicador', value_name='Valor')
                    df_t_maq_melt['Mes_Nombre'] = df_t_maq_melt['Month'].map(meses_map)
                    
                    fig_m = px.bar(
                        df_t_maq_melt, x='Mes_Nombre', y='Valor', color='Indicador',
                        barmode='group', text_auto='.0f',
                        color_discrete_map={'OEE': '#2C3E50', 'DISP': '#2980B9', 'PERF': '#F39C12', 'CAL': '#27AE60'}
                    )
                    fig_m.update_layout(
                        height=350, width=700, margin=dict(t=30, b=20, l=20, r=20),
                        yaxis_title='Porcentaje (%)', xaxis_title='', title=f'Evolución Mensual - {maq}',
                        plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_m.update_yaxes(rangemode="tozero")
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_m:
                        fig_m.write_image(tmp_m.name, engine="kaleido")
                        pdf.set_y(y_curr + 15)
                        add_image_safe(pdf, tmp_m.name, w_mm=170, h_mm=85, center=True)
                        os.remove(tmp_m.name)

    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 5.B. MOTOR GENERADOR DEL PDF PRINCIPAL (Detallado)
# ==========================================
def crear_pdf(area, label_reporte, op_target_df, prod_target_df, df_pdf_raw, p_tipo, df_trend, df_metrics_pdf, df_horarios, df_metrics_std_pdf, df_piezas_excluidas):
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

    df_pdf = pd.DataFrame(columns=['Máquina', 'Fábrica', 'Estado_Global', 'Tiempo (Min)', 'Operador'])
    if not df_pdf_raw.empty:
        df_pdf = df_pdf_raw[df_pdf_raw['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
    df_pdf['Grupo_Máquina'] = df_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    df_prod_pdf = pd.DataFrame(columns=['Máquina', 'Buenas', 'Retrabajo', 'Observadas'])
    if not prod_target_df.empty:
        df_prod_pdf = prod_target_df.copy()
    df_prod_pdf['Grupo_Máquina'] = df_prod_pdf['Máquina'].astype(str).str.strip().str.upper().map(mapa_limpio).fillna('Otro')

    pdf = ReportePDF(area, label_reporte, theme_color)
    pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    
    links_resumen_grupo = {g: pdf.add_link() for g in grupos_area}
    links_detalle_grupo = {g: pdf.add_link() for g in grupos_area}
    link_perfo = pdf.add_link(); link_tiempos = pdf.add_link()

    # --- ÍNDICE DEL REPORTE ---
    pdf.ln(10); pdf.set_font("Times", 'B', 18); pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text("ÍNDICE DEL REPORTE"), ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", 'U', 11); pdf.set_text_color(*comp_color)
        
    for g in grupos_area:
        pdf.cell(0, 7, clean_text(f">> Grupo {g} - Resumen General del Área"), ln=True, link=links_resumen_grupo[g])
        pdf.cell(0, 7, clean_text(f"      -> Ir al Cuadro Resumen por Máquinas"), ln=True, link=links_detalle_grupo[g])
        pdf.ln(1)
    pdf.ln(4)
    pdf.cell(0, 8, clean_text(">> Performance General de Operarios"), ln=True, link=link_perfo)
    pdf.cell(0, 8, clean_text(">> Tablas de Tiempos Acumulados de Baño y Refrigerio"), ln=True, link=link_tiempos)

    if df_pdf.empty and df_metrics_pdf.empty:
        pdf.add_page(); pdf.set_font("Arial", 'I', 12); pdf.set_text_color(100)
        pdf.cell(0, 10, f"No hay datos registrados para la fabrica {area} en este periodo.", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    def obtener_metricas_maquina(maq_name, df_m):
        maq_row = df_m[df_m['Máquina'] == maq_name]
        if maq_row.empty: return None
        r = maq_row.iloc[0]
        calc_oee_indiv = (r['DISPONIBILIDAD'] * r['PERFORMANCE'] * r['CALIDAD']) / 10000

        return {
            'OEE': calc_oee_indiv, 'DISPONIBILIDAD': r['DISPONIBILIDAD'], 
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
        df_m_g_check = df_metrics_pdf[df_metrics_pdf['Máquina'].isin(maq_del_grupo)] if not df_metrics_pdf.empty else pd.DataFrame()
        if df_pdf_g.empty and df_m_g_check.empty: continue
            
        pdf.add_page(); pdf.set_link(links_resumen_grupo[g]) 
        pdf.set_font("Times", 'B', 16); pdf.set_text_color(*theme_color)
        pdf.cell(0, 10, clean_text(f"SECCIÓN GRUPO: {g}"), ln=True, align='L', border='B'); pdf.ln(5)

        # 1. RESUMEN OEE DEL GRUPO
        check_space(pdf, 30); print_section_title(pdf, "1. Resumen OEE del Grupo", theme_color)
        
        piezas_excluidas_grupo = df_piezas_excluidas[df_piezas_excluidas['Máquina'].isin(maq_del_grupo)]['Code'].unique() if not df_piezas_excluidas.empty else []
        is_h_active = len(piezas_excluidas_grupo) > 0

        if is_h_active:
            pdf.set_font("Arial", 'I', 8)
            pdf.set_text_color(220, 20, 20)
            piezas_str = ", ".join(sorted(piezas_excluidas_grupo))
            pdf.multi_cell(0, 4, clean_text(f"* Nota: Se calculan indicadores principales excluyendo los tiempos y producción de las siguientes piezas H detectadas en este grupo: {piezas_str}"))
            pdf.ln(2)

        g_plan = 0; g_op = 0; g_buenas = 0; g_totales = 0
        g_disp_w = 0; g_perf_w = 0
        
        g_plan_std = 0; g_op_std = 0; g_buenas_std = 0; g_totales_std = 0
        g_disp_w_std = 0; g_perf_w_std = 0

        maquinas_metricas = {}
        maquinas_metricas_std = {}
        
        for maq in maq_del_grupo:
            # MÉTRICAS PRINCIPALES
            metrics = obtener_metricas_maquina(maq, df_metrics_pdf)
            if metrics:
                maquinas_metricas[maq] = metrics
                t_p = metrics['T_Planificado']; t_o = metrics['T_Operativo']
                g_plan += t_p; g_op += t_o
                g_buenas += metrics['Buenas']; g_totales += metrics['Totales']
                g_disp_w += metrics['DISPONIBILIDAD'] * t_p
                g_perf_w += metrics['PERFORMANCE'] * t_o
            
            # MÉTRICAS ESTÁNDAR (Para comparativa)
            if is_h_active:
                metrics_std = obtener_metricas_maquina(maq, df_metrics_std_pdf)
                if metrics_std:
                    maquinas_metricas_std[maq] = metrics_std
                    t_p_s = metrics_std['T_Planificado']; t_o_s = metrics_std['T_Operativo']
                    g_plan_std += t_p_s; g_op_std += t_o_s
                    g_buenas_std += metrics_std['Buenas']; g_totales_std += metrics_std['Totales']
                    g_disp_w_std += metrics_std['DISPONIBILIDAD'] * t_p_s
                    g_perf_w_std += metrics_std['PERFORMANCE'] * t_o_s

        g_disp = g_disp_w / g_plan if g_plan > 0 else 0
        g_perf = g_perf_w / g_op if g_op > 0 else 0
        g_cal = (g_buenas / g_totales) * 100 if g_totales > 0 else 0 
        g_oee = (g_disp * g_perf * g_cal) / 10000 
        m_g = {'OEE': g_oee, 'DISPONIBILIDAD': g_disp, 'PERFORMANCE': g_perf, 'CALIDAD': g_cal}
        
        m_g_std = None
        if is_h_active:
            g_disp_s = g_disp_w_std / g_plan_std if g_plan_std > 0 else 0
            g_perf_s = g_perf_w_std / g_op_std if g_op_std > 0 else 0
            g_cal_s = (g_buenas_std / g_totales_std) * 100 if g_totales_std > 0 else 0 
            g_oee_s = (g_disp_s * g_perf_s * g_cal_s) / 10000 
            m_g_std = {'OEE': g_oee_s, 'DISPONIBILIDAD': g_disp_s, 'PERFORMANCE': g_perf_s, 'CALIDAD': g_cal_s}

        print_pdf_metric_row(pdf, f"Total {g}", m_g, m_g_std)
        
        for maq, metrics in maquinas_metricas.items():
            print_pdf_metric_row(pdf, f"    > {maq}", metrics, maquinas_metricas_std.get(maq))
        pdf.ln(3)

        # 2. GRÁFICOS DE EVOLUCIÓN (MENSUAL) O KPIS POR MÁQUINA (DIARIO/SEMANAL)
        if p_tipo == "Mensual":
            print_section_title(pdf, "2. Evolución Histórica OEE por Máquina", theme_color)
            if not df_trend.empty:
                df_trend_g = df_trend[df_trend['Máquina'].isin(maq_del_grupo)].copy()
                if not df_trend_g.empty:
                    meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                    df_trend_g['Mes_Nombre'] = df_trend_g['Month'].map(meses_map)
                    
                    df_trend_g['DISP'] = (df_trend_g['Disp_Num'] / df_trend_g['OEE_Den']).fillna(0)
                    df_trend_g['PERF'] = (df_trend_g['Perf_Num'] / df_trend_g['T_Operativo']).fillna(0)
                    df_trend_g['CAL'] = (df_trend_g['Cal_Num'] / df_trend_g['Piezas_Totales']).fillna(0)
                    df_trend_g['OEE'] = (df_trend_g['DISP'] * df_trend_g['PERF'] * df_trend_g['CAL']) / 10000
                    
                    fig_trend_oee = px.bar(
                        df_trend_g, x='Mes_Nombre', y='OEE', color='Máquina', 
                        barmode='group', text_auto='.1f', color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    fig_trend_oee.update_layout(
                        height=180, width=800, margin=dict(t=15, b=15, l=20, r=20),
                        yaxis_title='OEE (%)', xaxis_title='', legend_title='Máquinas', 
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    fig_trend_oee.update_yaxes(rangemode="tozero")
                    
                    y_base = pdf.get_y()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_oee:
                        fig_trend_oee.write_image(tmp_oee.name, engine="kaleido")
                        pdf.image(tmp_oee.name, x=10, y=y_base, w=190)
                        os.remove(tmp_oee.name)
                        
                    pdf.set_y(y_base + 52); pdf.ln(2)
                else:
                    pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay datos históricos para graficar en este grupo."), ln=True)
            else:
                pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay datos de evolución para graficar en este periodo."), ln=True)
        
        else: # Semanal o Diario
            print_section_title(pdf, f"2. Comparativa de KPIs entre Máquinas ({p_tipo})", theme_color)
            df_m_g = df_metrics_pdf[df_metrics_pdf['Máquina'].isin(maq_del_grupo)].copy()
            if not df_m_g.empty:
                df_m_g['OEE'] = (df_m_g['DISPONIBILIDAD'] * df_m_g['PERFORMANCE'] * df_m_g['CALIDAD']) / 10000

                df_m_g_melt = df_m_g.melt(id_vars=['Máquina'], value_vars=['OEE', 'DISPONIBILIDAD', 'PERFORMANCE', 'CALIDAD'], var_name='Indicador', value_name='Valor')
                
                if df_m_g_melt['Valor'].max() <= 10.0:
                    df_m_g_melt['Valor'] = df_m_g_melt['Valor'] * 100
                
                fig_kpis = px.bar(
                    df_m_g_melt, x='Indicador', y='Valor', color='Máquina', 
                    barmode='group', text_auto='.1f',
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_kpis.update_layout(
                    height=180, width=800, margin=dict(t=15, b=15, l=20, r=20),
                    yaxis_title='Porcentaje (%)', xaxis_title='', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title="")
                )
                fig_kpis.update_yaxes(rangemode="tozero")
                
                y_base = pdf.get_y()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_kpi:
                    fig_kpis.write_image(tmp_kpi.name, engine="kaleido")
                    pdf.image(tmp_kpi.name, x=10, y=y_base, w=190)
                    os.remove(tmp_kpi.name)
                    
                pdf.set_y(y_base + 52); pdf.ln(2)
            else:
                pdf.set_font("Arial", 'I', 9); pdf.cell(0, 6, clean_text("No hay datos de KPIs para graficar en este periodo."), ln=True)

        # =========================================================================
        # 3. HORARIOS Y TIEMPO DE APERTURA (CON COLORES SOLO EN DIARIO)
        # =========================================================================
        if p_tipo in ["Diario", "Semanal"]:
            print_section_title(pdf, "3. Horarios y Tiempo de Apertura", theme_color)
            setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)

            if not df_horarios.empty:
                df_horarios_grupo = df_horarios[df_horarios['Máquina'].isin(maq_del_grupo)].copy()

                if not df_horarios_grupo.empty:
                    if p_tipo == "Semanal":
                        w_maq = 35; w_tur = 15; w_day = 27
                        pdf.cell(w_maq, 6, "Maquina", 1, 0, 'C', True)
                        pdf.cell(w_tur, 6, "Turno", 1, 0, 'C', True)
                        dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
                        for d in dias:
                            pdf.cell(w_day, 6, d, 1, 0 if d != "Viernes" else 1, 'C', True)

                        setup_table_row(pdf); pdf.set_font("Arial", '', 8)

                        df_horarios_grupo['Dia'] = pd.to_datetime(df_horarios_grupo['Dia'])
                        df_horarios_grupo['Weekday'] = df_horarios_grupo['Dia'].dt.weekday
                        df_horarios_grupo['Rango'] = df_horarios_grupo.apply(
                            lambda row: f"{row['Hora_Inicio']}-{row['Hora_Cierre']}" if pd.notna(row['Hora_Inicio']) else "", axis=1
                        )

                        grouped = df_horarios_grupo.groupby(['Máquina', 'Turno'])
                        for (maq_name, turno), group in grouped:
                            if pdf.get_y() > 265: 
                                pdf.add_page(); setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                                pdf.cell(w_maq, 6, "Maquina", 1, 0, 'C', True); pdf.cell(w_tur, 6, "Turno", 1, 0, 'C', True)
                                for d in dias: pdf.cell(w_day, 6, d, 1, 0 if d != "Viernes" else 1, 'C', True)
                                setup_table_row(pdf); pdf.set_font("Arial", '', 8)

                            pdf.set_text_color(50, 50, 50)
                            pdf.cell(w_maq, 5, " " + clean_text(maq_name), 1, 0, 'L')
                            pdf.cell(w_tur, 5, clean_text(turno), 1, 0, 'C')

                            for day_idx in range(5):
                                day_data = group[group['Weekday'] == day_idx]
                                if not day_data.empty:
                                    rango = day_data.iloc[0]['Rango']
                                    pdf.cell(w_day, 5, rango, 1, 0 if day_idx < 4 else 1, 'C')
                                else:
                                    pdf.cell(w_day, 5, "", 1, 0 if day_idx < 4 else 1, 'C')
                            pdf.ln()

                    else: # Diario
                        w_maq = 35; w_tur = 20; w_hor = 30; w_tie = 35
                        pdf.cell(w_maq, 6, "Maquina", 1, 0, 'C', True)
                        pdf.cell(w_tur, 6, "Turno", 1, 0, 'C', True)
                        pdf.cell(w_hor, 6, "Hora Inicio", 1, 0, 'C', True)
                        pdf.cell(w_hor, 6, "Hora Cierre", 1, 0, 'C', True)
                        pdf.cell(w_tie, 6, "Apertura Neta", 1, 0, 'C', True)
                        pdf.cell(w_tie, 6, "No Registrado", 1, 1, 'C', True)

                        setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                        for _, r_hor in df_horarios_grupo.sort_values(['Máquina', 'Turno']).iterrows():
                            if pdf.get_y() > 265: 
                                pdf.add_page(); setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                                pdf.cell(w_maq, 6, "Maquina", 1, 0, 'C', True); pdf.cell(w_tur, 6, "Turno", 1, 0, 'C', True)
                                pdf.cell(w_hor, 6, "Hora Inicio", 1, 0, 'C', True); pdf.cell(w_hor, 6, "Hora Cierre", 1, 0, 'C', True)
                                pdf.cell(w_tie, 6, "Apertura Neta", 1, 0, 'C', True); pdf.cell(w_tie, 6, "No Registrado", 1, 1, 'C', True)
                                setup_table_row(pdf); pdf.set_font("Arial", '', 8)

                            pdf.cell(w_maq, 5, " " + clean_text(r_hor['Máquina']), 1, 0, 'L')
                            pdf.cell(w_tur, 5, clean_text(r_hor['Turno']), 1, 0, 'C')
                            
                            hora_ini = str(r_hor['Hora_Inicio'])
                            try:
                                h, m = map(int, hora_ini.split(':'))
                                total_min = h * 60 + m
                                if 360 <= total_min <= 370: # 06:00 - 06:10 -> Verde
                                    pdf.set_text_color(33, 195, 84)
                                elif 370 < total_min <= 420: # 06:11 - 07:00 -> Rojo
                                    pdf.set_text_color(220, 20, 20)
                                else: # Horarios del medio u otros turnos -> Violeta
                                    pdf.set_text_color(128, 0, 128)
                            except:
                                pdf.set_text_color(50, 50, 50)
                            
                            pdf.cell(w_hor, 5, hora_ini, 1, 0, 'C')
                            
                            hora_fin = str(r_hor['Hora_Cierre'])
                            try:
                                h_f, m_f = map(int, hora_fin.split(':'))
                                total_min_fin = h_f * 60 + m_f
                                if 845 <= total_min_fin <= 858: # 14:05 - 14:18 -> Verde (Ideal)
                                    pdf.set_text_color(33, 195, 84)
                                elif 810 <= total_min_fin < 845: # 13:30 - 14:04 -> Rojo (Prematuro)
                                    pdf.set_text_color(220, 20, 20)
                                else: # Horarios del medio u otros turnos -> Violeta
                                    pdf.set_text_color(128, 0, 128)
                            except:
                                pdf.set_text_color(50, 50, 50)

                            pdf.cell(w_hor, 5, clean_text(r_hor['Hora_Cierre']), 1, 0, 'C')
                            pdf.set_text_color(50, 50, 50)
                            
                            apertura_str = mins_to_duration_str(r_hor.get('Apertura_Neta_Min', 0))
                            no_reg_str = mins_to_duration_str(r_hor.get('No_Registrado_Min', 0))
                            
                            pdf.cell(w_tie, 5, apertura_str, 1, 0, 'C')
                            pdf.cell(w_tie, 5, no_reg_str, 1, 1, 'C')
                else:
                    pdf.cell(185, 5, "No hay registros de turnos para este grupo.", 1, 1, 'C')
            else:
                pdf.cell(185, 5, "No hay registros de turnos para este periodo.", 1, 1, 'C')
                
            pdf.ln(5)

        # 4. RESUMEN GENERAL DE TIEMPOS DEL GRUPO
        check_space(pdf, 30)
        num_section_tiempos = "3." if p_tipo == "Mensual" else "4."
        print_section_title(pdf, f"{num_section_tiempos} Resumen General del Grupo (Tiempos Consolidados)", theme_color)
        
        t_prod_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Producción']['Tiempo (Min)'].sum()
        t_falla_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Falla/Gestión']['Tiempo (Min)'].sum()
        t_parada_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Parada Programada']['Tiempo (Min)'].sum()
        t_proy_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Proyecto']['Tiempo (Min)'].sum()
        t_desc_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Descanso']['Tiempo (Min)'].sum()
        
        pdf.set_font("Arial", 'B', 12); pdf.set_text_color(255, 255, 255); pdf.set_fill_color(*comp_color)
        pdf.cell(0, 8, clean_text(f"  RESUMEN TOTAL ACUMULADO GRUPO: {g}"), border=0, ln=True, fill=True)
        pdf.set_font("Arial", 'I', 8); pdf.set_text_color(120, 120, 120); pdf.cell(0, 5, clean_text("  Acumulado total de todas las máquinas de la familia"), border=0, ln=True); pdf.ln(2)
        
        setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
        for col_name in ["Produccion", "Fallas/Gestion", "Paradas Prog.", "Proyecto", "Descansos"]: pdf.cell(38, 6, col_name, border=1, align='C', fill=True)
        pdf.ln(); setup_table_row(pdf); pdf.set_font("Arial", '', 9)
        pdf.cell(38, 5, clean_text(mins_to_duration_str(t_prod_g)), border=1, align='C')
        pdf.cell(38, 5, clean_text(mins_to_duration_str(t_falla_g)), border=1, align='C')
        pdf.cell(38, 5, clean_text(mins_to_duration_str(t_parada_g)), border=1, align='C')
        pdf.cell(38, 5, clean_text(mins_to_duration_str(t_proy_g)), border=1, align='C')
        pdf.cell(38, 5, clean_text(mins_to_duration_str(t_desc_g)), border=1, align='C', ln=True); pdf.ln(4)
        
        # --- Análisis de Fallas + Tendencias Temporales (CORREGIDO CRONOLÓGICAMENTE) ---
        check_space(pdf, 170)
        print_section_title(pdf, "Análisis de Fallas, Tendencias y Estructura Visual", theme_color)

        df_g_fallas = df_pdf_g[df_pdf_g['Estado_Global'] == 'Falla/Gestión'].copy()
        if not df_g_fallas.empty:
            agg_f15 = df_g_fallas.groupby('Detalle_Final')['Tiempo (Min)'].sum().reset_index().sort_values('Tiempo (Min)', ascending=False).head(15)
            agg_f15 = agg_f15.sort_values('Tiempo (Min)', ascending=True) 
            agg_f15['Label'] = agg_f15.apply(lambda r: f" {str(r['Detalle_Final'])[:60]} — {r['Tiempo (Min)']:.0f}m", axis=1)
            max_x_val = agg_f15['Tiempo (Min)'].max() if not agg_f15.empty else 1
            
            # Corrección cronológica con datetime real para que las líneas no vuelvan atrás
            if p_tipo == "Diario":
                df_g_fallas['Eje_Temp'] = pd.to_datetime(df_g_fallas['Inicio']).dt.floor('h')
                fmt_tick = '%H:%M'
            else:
                df_g_fallas['Eje_Temp'] = pd.to_datetime(df_g_fallas['Fecha_Filtro'])
                fmt_tick = '%d/%m'
                
            trend_df = df_g_fallas.groupby(['Eje_Temp', 'Máquina'])['Tiempo (Min)'].sum().reset_index()
            trend_df = trend_df.sort_values('Eje_Temp')
            
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(*comp_color)
            pdf.cell(95, 6, clean_text("> Top 15 Fallas del Grupo (por tiempo):"), 0, 0, 'L')
            pdf.cell(95, 6, clean_text("> Tendencia Temporal de Fallas (Minutos):"), 0, 1, 'L')
            
            y_base_graficos = pdf.get_y()
            
            fig_top15 = px.bar(agg_f15, x='Tiempo (Min)', y='Detalle_Final', orientation='h', text='Label')
            fig_top15.update_traces(marker_color=hex_comp, textposition='outside', textfont=dict(size=11, color='black'), cliponaxis=False)
            fig_top15.update_layout(height=250, width=450, margin=dict(t=5, b=5, l=10, r=220), plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False, range=[0, max_x_val * 1.5]), yaxis=dict(title='', showticklabels=False))
            
            fig_trend = px.line(trend_df, x='Eje_Temp', y='Tiempo (Min)', color='Máquina', markers=True, color_discrete_sequence=px.colors.qualitative.Set1)
            fig_trend.update_xaxes(tickformat=fmt_tick) # Fuerza formato cronológico seguro
            fig_trend.update_layout(height=250, width=400, margin=dict(t=10, b=30, l=40, r=20), plot_bgcolor='rgba(0,0,0,0)', xaxis_title="", yaxis_title="Minutos", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
                fig_top15.write_image(tmp_chart.name, engine="kaleido")
                pdf.image(tmp_chart.name, x=5, y=y_base_graficos, w=105)
                os.remove(tmp_chart.name)
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_trend:
                fig_trend.write_image(tmp_trend.name, engine="kaleido")
                pdf.image(tmp_trend.name, x=110, y=y_base_graficos, w=90)
                os.remove(tmp_trend.name)
                
            pdf.set_y(y_base_graficos + 60); pdf.ln(2)

        # Tortas de Estructura Visual
        resumen_global = df_pdf_g.groupby('Estado_Global')['Tiempo (Min)'].sum().reset_index() if not df_pdf_g.empty else pd.DataFrame()
        total_global = resumen_global['Tiempo (Min)'].sum() if not resumen_global.empty else 0
        
        if total_global > 0:
            num_section_visual = "4." if p_tipo == "Mensual" else "5."
            print_section_title(pdf, f"{num_section_visual} Resumen Visual de Tiempos del Grupo", theme_color); y_base = pdf.get_y()
            
            fig_g = px.pie(resumen_global, values='Tiempo (Min)', names='Estado_Global', hole=0.4, title="Estructura de Tiempos (Hs)", color_discrete_sequence=pie_colors)
            fig_g.update_traces(textinfo='percent+label', textposition='outside', textfont_size=11)
            fig_g.update_layout(width=420, height=300, margin=dict(t=40, b=50, l=80, r=80), showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
                fig_g.write_image(tmp1.name, engine="kaleido")
            
            df_fallas_grupo = df_pdf_g[df_pdf_g['Estado_Global'] == 'Falla/Gestión'].copy()
            if not df_fallas_grupo.empty and df_fallas_grupo['Tiempo (Min)'].sum() > 0:
                resumen_fallas = df_fallas_grupo.groupby('Categoria_Macro')['Tiempo (Min)'].sum().reset_index()
                fig_p = px.pie(resumen_fallas, values='Tiempo (Min)', names='Categoria_Macro', hole=0.4, title="Fallas Distribuidas por Área (Hs)", color_discrete_sequence=pie_colors)
                fig_p.update_traces(textinfo='percent+label', textposition='outside', textfont_size=11)
                fig_p.update_layout(width=420, height=300, margin=dict(t=40, b=50, l=80, r=80), showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
                    fig_p.write_image(tmp2.name, engine="kaleido")
                    
                pdf.image(tmp1.name, x=5, y=y_base, w=100)
                pdf.image(tmp2.name, x=105, y=y_base, w=100)
                os.remove(tmp2.name)
            else:
                pdf.image(tmp1.name, x=55, y=y_base, w=100)
                
            os.remove(tmp1.name)
            pdf.set_y(y_base + 75); pdf.ln(2)
        else:
            num_section_visual = "4." if p_tipo == "Mensual" else "5."
            print_section_title(pdf, f"{num_section_visual} Resumen Visual de Tiempos del Grupo", theme_color)
            pdf.set_font("Arial", 'I', 9); pdf.set_text_color(100, 100, 100); pdf.cell(0, 6, clean_text("No hay datos de tiempo suficientes para generar gráficos de torta."), ln=True); pdf.ln(5)

        # -----------------------------------------------------------------
        # DETALLE DE PARADAS PROGRAMADAS
        # -----------------------------------------------------------------
        check_space(pdf, 50)
        print_section_title(pdf, "Detalle de Paradas Programadas", theme_color)

        df_paradas_g = df_pdf_g[df_pdf_g['Estado_Global'] == 'Parada Programada'].copy()

        if not df_paradas_g.empty:
            if p_tipo in ["Mensual", "Semanal"]:
                resumen_paradas = df_paradas_g.groupby('Detalle_Final').agg(
                    Total_Min=('Tiempo (Min)', 'sum'),
                    Cantidad=('Tiempo (Min)', 'count')
                ).reset_index()
                resumen_paradas['Promedio'] = resumen_paradas['Total_Min'] / resumen_paradas['Cantidad']
                resumen_paradas = resumen_paradas.sort_values('Total_Min', ascending=False)

                pdf.set_font("Arial", 'B', 10); pdf.set_text_color(*theme_color)
                pdf.cell(0, 6, clean_text(">> Resumen por Tipo de Parada Programada (Promedios):"), ln=True)
                
                setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                pdf.cell(80, 6, "Tipo de Evento", 1, 0, 'C', True)
                pdf.cell(30, 6, "Total (Min)", 1, 0, 'C', True)
                pdf.cell(30, 6, "Cantidad Eventos", 1, 0, 'C', True)
                pdf.cell(30, 6, "Promedio (Min)", 1, 1, 'C', True)
                
                setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                for _, r_res in resumen_paradas.iterrows():
                    if pdf.get_y() > 265:
                        pdf.add_page()
                        setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 8)
                        pdf.cell(80, 6, "Tipo de Evento", 1, 0, 'C', True)
                        pdf.cell(30, 6, "Total (Min)", 1, 0, 'C', True)
                        pdf.cell(30, 6, "Cantidad Eventos", 1, 0, 'C', True)
                        pdf.cell(30, 6, "Promedio (Min)", 1, 1, 'C', True)
                        setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                        
                    pdf.cell(80, 5, " " + clean_text(r_res['Detalle_Final'])[:45], 1, 0, 'L')
                    pdf.cell(30, 5, f"{r_res['Total_Min']:.0f}", 1, 0, 'C')
                    pdf.cell(30, 5, str(int(r_res['Cantidad'])), 1, 0, 'C')
                    pdf.cell(30, 5, f"{r_res['Promedio']:.1f}", 1, 1, 'C')
                pdf.ln(5)

            else:
                df_paradas_g = df_paradas_g.sort_values(['Máquina', 'Inicio'])

                def dibujar_cabeza_paradas():
                    setup_table_header(pdf, theme_color)
                    pdf.set_font("Arial", 'B', 8)
                    pdf.cell(35, 6, "Maquina", 1, 0, 'C', True)
                    pdf.cell(20, 6, "Inicio", 1, 0, 'C', True)
                    pdf.cell(20, 6, "Fin", 1, 0, 'C', True)
                    pdf.cell(25, 6, "Duracion", 1, 0, 'C', True)
                    pdf.cell(90, 6, "Descripcion de la Parada", 1, 1, 'C', True)

                dibujar_cabeza_paradas()
                setup_table_row(pdf)
                pdf.set_font("Arial", '', 8)

                fill_toggle_p = False
                for _, r_par in df_paradas_g.iterrows():
                    if pdf.get_y() > 265:
                        pdf.add_page()
                        dibujar_cabeza_paradas()
                        setup_table_row(pdf)
                        pdf.set_font("Arial", '', 8)

                    if fill_toggle_p:
                        if area.upper() == "ESTAMPADO":
                            pdf.set_fill_color(235, 243, 250)
                        else:
                            pdf.set_fill_color(253, 242, 233)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    maq_str = clean_text(str(r_par['Máquina']))[:18]
                    ini_str = clean_text(str(r_par['Inicio_Str']))
                    fin_str = clean_text(str(r_par['Fin_Str']))
                    dur_str = f"{r_par['Tiempo (Min)']:.0f} min"
                    desc_str = clean_text(str(r_par['Detalle_Final']))[:55]

                    pdf.cell(35, 5, " " + maq_str, 1, 0, 'L', True)
                    pdf.cell(20, 5, ini_str, 1, 0, 'C', True)
                    pdf.cell(20, 5, fin_str, 1, 0, 'C', True)
                    pdf.cell(25, 5, dur_str, 1, 0, 'C', True)
                    pdf.cell(90, 5, " " + desc_str, 1, 1, 'L', True)

                    fill_toggle_p = not fill_toggle_p
                pdf.ln(5)
        else:
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, clean_text("No hay paradas programadas registradas para este grupo en este periodo."), ln=True)
            pdf.ln(5)

        pdf.set_text_color(0, 0, 0)
        
        # -----------------------------------------------------------------
        # CUADRO RESUMEN POR MÁQUINAS (Fluye naturalmente)
        # -----------------------------------------------------------------
        maquinas_con_tiempo = []
        if not df_pdf_g.empty:
            for maq in sorted(df_pdf_g['Máquina'].unique()):
                df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
                t_total = df_maq[df_maq['Estado_Global'].isin(['Producción', 'Falla/Gestión', 'Parada Programada', 'Proyecto', 'Descanso'])]['Tiempo (Min)'].sum()
                if t_total > 0: maquinas_con_tiempo.append(maq)

        if maquinas_con_tiempo:
            check_space(pdf, 55)
            pdf.set_link(links_detalle_grupo[g])
            print_section_title(pdf, f"Cuadro Resumen por Máquinas - Grupo {g}", theme_color)

            def dibujar_cabeza_resumen_maq():
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 7)
                pdf.cell(25, 6, "MAQUINA", 1, 0, 'C', True)
                pdf.cell(20, 6, "PRODUCCION", 1, 0, 'C', True)
                pdf.cell(15, 6, "FALLAS", 1, 0, 'C', True)
                pdf.cell(20, 6, "PARADA PROG.", 1, 0, 'C', True)
                pdf.cell(18, 6, "DESCANSO", 1, 0, 'C', True)
                pdf.cell(22, 6, "TIEMPO NO REG.", 1, 0, 'C', True)
                pdf.cell(70, 6, "TOP 3 FALLAS.", 1, 1, 'C', True)

            dibujar_cabeza_resumen_maq()
            setup_table_row(pdf)
            pdf.set_font("Arial", '', 7)

            fill_toggle = False

            for maq in maquinas_con_tiempo:
                df_maq = df_pdf_g[df_pdf_g['Máquina'] == maq]
                t_prod = df_maq[df_maq['Estado_Global'] == 'Producción']['Tiempo (Min)'].sum()
                t_falla = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']['Tiempo (Min)'].sum()
                t_parada = df_maq[df_maq['Estado_Global'] == 'Parada Programada']['Tiempo (Min)'].sum()
                t_desc = df_maq[df_maq['Estado_Global'] == 'Descanso']['Tiempo (Min)'].sum()

                # Cálculo de tiempo no registrado por turno
                total_noreg = 0
                for (fecha, turno), grp_t in df_maq.groupby(['Fecha_Filtro', 'Turno']):
                    intervals = []
                    for _, r in grp_t.iterrows():
                        ini = parse_time_to_mins(r['Inicio_Str'])
                        fin = parse_time_to_mins(r['Fin_Str'])
                        if ini is not None and fin is not None:
                            if fin < ini and (ini - fin) > 720: fin += 1440
                            intervals.append([ini, fin])
                    if intervals:
                        intervals.sort(key=lambda x: x[0])
                        merged = [intervals[0]]
                        for current in intervals[1:]:
                            last = merged[-1]
                            if current[0] <= last[1]: last[1] = max(last[1], current[1])
                            else: merged.append(current)
                        total_active = sum(iv[1] - iv[0] for iv in merged)
                        tiempo_bruto = merged[-1][1] - merged[0][0]
                        total_noreg += max(0, tiempo_bruto - total_active)

                df_maq_fallas = df_maq[df_maq['Estado_Global'] == 'Falla/Gestión']
                top3_fallas = []
                if not df_maq_fallas.empty:
                    agg_f = df_maq_fallas.groupby('Detalle_Final')['Tiempo (Min)'].sum().reset_index().sort_values('Tiempo (Min)', ascending=False).head(3)
                    for _, r in agg_f.iterrows():
                        top3_fallas.append(f"- {str(r['Detalle_Final']).strip()[:42]} ({r['Tiempo (Min)']:.0f}m)")
                
                num_lines = max(1, len(top3_fallas))
                row_h = num_lines * 5 

                if pdf.get_y() + row_h > 265:
                    pdf.add_page()
                    dibujar_cabeza_resumen_maq()
                    setup_table_row(pdf)
                    pdf.set_font("Arial", '', 7)

                if fill_toggle:
                    if area.upper() == "ESTAMPADO":
                        pdf.set_fill_color(235, 243, 250) 
                    else:
                        pdf.set_fill_color(253, 242, 233) 
                else:
                    pdf.set_fill_color(255, 255, 255)

                x_pos = pdf.get_x()
                y_pos = pdf.get_y()

                pdf.cell(25, row_h, clean_text(maq)[:15], 1, 0, 'C', True)
                pdf.cell(20, row_h, clean_text(mins_to_duration_str(t_prod)), 1, 0, 'C', True)
                pdf.cell(15, row_h, clean_text(mins_to_duration_str(t_falla)), 1, 0, 'C', True)
                pdf.cell(20, row_h, clean_text(mins_to_duration_str(t_parada)), 1, 0, 'C', True)
                pdf.cell(18, row_h, clean_text(mins_to_duration_str(t_desc)), 1, 0, 'C', True)
                pdf.cell(22, row_h, clean_text(mins_to_duration_str(total_noreg)), 1, 0, 'C', True)

                x_fail = pdf.get_x()
                y_fail = pdf.get_y()
                pdf.rect(x_fail, y_fail, 70, row_h, 'DF') 

                for idx, f_str in enumerate(top3_fallas):
                    pdf.set_xy(x_fail + 1, y_fail + (idx * 5) + 0.5)
                    pdf.cell(68, 4, clean_text(f_str), 0, 0, 'L')

                pdf.set_xy(x_pos, y_pos + row_h)
                fill_toggle = not fill_toggle
            
            pdf.ln(5)

        # 6. PRODUCCIÓN POR GRUPO 
        df_prod_pdf_g = df_prod_pdf[df_prod_pdf['Grupo_Máquina'] == g] if not df_prod_pdf.empty else pd.DataFrame()
        if not df_prod_pdf_g.empty:
            check_space(pdf, 75)
            print_section_title(pdf, "Desglose de Producción del Grupo", theme_color)
            
            prod_maq = df_prod_pdf_g.groupby('Máquina')[['Buenas', 'Retrabajo', 'Observadas']].sum().reset_index()
            fig_prod = px.bar(prod_maq, x='Máquina', y=['Buenas', 'Retrabajo', 'Observadas'], barmode='stack', color_discrete_sequence=chart_bars, text_auto=True)
            fig_prod.update_layout(width=800, height=220, margin=dict(t=15, b=25, l=20, r=20))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile3:
                fig_prod.write_image(tmpfile3.name, engine="kaleido")
                add_image_safe(pdf, tmpfile3.name, w_mm=155, h_mm=45)
                os.remove(tmpfile3.name)
            
            pdf.ln(2)
            
            def dibujar_cabeza_prod():
                setup_table_header(pdf, theme_color)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(70, 5, "Codigo Producto", 1, 0, 'C', True)
                pdf.cell(30, 5, "Buenas", 1, 0, 'C', True)
                pdf.cell(30, 5, "Retrab.", 1, 0, 'C', True)
                pdf.cell(30, 5, "Observ.", 1, 1, 'C', True)
            
            maquinas_prod = sorted(df_prod_pdf_g['Máquina'].unique())
            
            for maq_p in maquinas_prod:
                df_m_prod = df_prod_pdf_g[df_prod_pdf_g['Máquina'] == maq_p].groupby('Código')[['Buenas', 'Retrabajo', 'Observadas']].sum().reset_index()
                total_piezas = df_m_prod['Buenas'].sum() + df_m_prod['Retrabajo'].sum() + df_m_prod['Observadas'].sum()
                
                check_space(pdf, 45)
                pdf.set_font("Arial", 'B', 9); pdf.set_text_color(*theme_color)
                pdf.cell(0, 5, clean_text(f"Top 5 Códigos Producidos - {maq_p} (Total: {int(total_piezas)} pzs)"), ln=True)
                
                dibujar_cabeza_prod()
                setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                
                top5_prod = df_m_prod.sort_values('Buenas', ascending=False).head(5)
                for _, row in top5_prod.iterrows():
                    if pdf.get_y() > 265:
                        pdf.add_page(); dibujar_cabeza_prod(); setup_table_row(pdf); pdf.set_font("Arial", '', 8)
                    pdf.cell(70, 4.5, " " + clean_text(str(row['Código'])[:45]), 'B') 
                    pdf.cell(30, 4.5, str(int(row['Buenas'])), 'B', 0, 'C')
                    pdf.cell(30, 4.5, str(int(row['Retrabajo'])), 'B', 0, 'C')
                    pdf.cell(30, 4.5, str(int(row['Observadas'])), 'B', 1, 'C')
                pdf.ln(3) 

    # =========================================================================
    # SECCIÓN FINAL OPERARIOS 
    # =========================================================================
    check_space(pdf, 45)
    if pdf.get_y() > 30:
        pdf.ln(10); pdf.set_draw_color(*theme_color); pdf.set_line_width(1); pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.set_draw_color(0, 0, 0); pdf.set_line_width(0.2); pdf.ln(10)

    pdf.set_link(link_perfo); pdf.set_font("Times", 'B', 16); pdf.set_text_color(*theme_color)
    pdf.cell(0, 10, clean_text(f"SECCIÓN FINAL: PERFORMANCE Y TIEMPOS"), ln=True, align='L', border='B'); pdf.ln(5)
    print_section_title(pdf, "Performance de Operarios General", theme_color)
    
    if not op_target_df.empty:
        df_filt = op_target_df[op_target_df['Fábrica'].astype(str).str.contains(area, case=False, na=False)].copy()
        if df_filt.empty and not df_pdf.empty:
            ops_activos = []
            for op_list in df_pdf['Operador'].unique():
                if pd.notna(op_list) and op_list != '-': ops_activos.extend([o.strip() for o in op_list.split('/')])
            df_filt = op_target_df[op_target_df['Operador'].isin(ops_activos)].copy()
            
        if not df_filt.empty:
            df_filt = df_filt.drop_duplicates(subset=['Operador']).copy()
            df_filt['PERFORMANCE'] = pd.to_numeric(df_filt['PERFORMANCE'], errors='coerce').fillna(0)
            df_filt = df_filt.sort_values('PERFORMANCE', ascending=False)
            
            operador_maquinas = {}
            if not df_pdf.empty:
                for _, r in df_pdf.iterrows():
                    maq = str(r['Máquina']).strip()
                    ops = str(r['Operador']).split('/')
                    for o in ops:
                        o = o.strip()
                        if o and o != '-':
                            if o not in operador_maquinas:
                                operador_maquinas[o] = set()
                            operador_maquinas[o].add(maq)

            def dibujar_cabeza_oper():
                setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 9)
                pdf.cell(50, 6, "Operador", 1, 0, 'C', True)
                pdf.cell(35, 6, "Fabrica", 1, 0, 'C', True)
                pdf.cell(85, 6, "Maquinas Operadas", 1, 0, 'C', True)
                pdf.cell(20, 6, "Perf.", 1, 1, 'C', True)

            dibujar_cabeza_oper()
            setup_table_row(pdf); pdf.set_font("Arial", '', 9)
            for _, row in df_filt.iterrows():
                if pdf.get_y() > 270: 
                    pdf.add_page(); dibujar_cabeza_oper(); setup_table_row(pdf); pdf.set_font("Arial", '', 9)
                perf_val = int(round(row['PERFORMANCE'] * 100)) if row['PERFORMANCE'] <= 1.5 else int(round(row['PERFORMANCE']))
                
                op_name = clean_text(str(row['Operador'])).strip()
                if 'usuario' in op_name.lower() or 'admin' in op_name.lower(): continue

                maq_set = operador_maquinas.get(op_name, set())
                maq_str = ", ".join(sorted(list(maq_set))) if maq_set else "-"
                
                pdf.cell(50, 5, " " + op_name[:28], 'B')
                pdf.cell(35, 5, " " + clean_text(str(row['Fábrica'])[:18]), 'B')
                pdf.cell(85, 5, " " + clean_text(maq_str[:50]), 'B')
                    
                if perf_val >= 90: 
                    pdf.set_text_color(33, 195, 84) # Verde estricto
                else: 
                    pdf.set_text_color(220, 20, 20) # Rojo estricto
                    
                pdf.cell(20, 5, f"{perf_val}%", 'B', 1, 'C'); pdf.set_text_color(50, 50, 50)
            pdf.ln(5)
        else:
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 10, clean_text("No hay datos de performance para los operarios de esta área."), ln=True)
    else:
        pdf.set_font("Arial", 'I', 10); pdf.cell(0, 10, clean_text("No hay datos de performance registrados para esta área en este período."), ln=True)

    def agregar_tabla_tiempos(titulo, palabras_clave, limite_minutos):
        check_space(pdf, 25); print_section_title(pdf, titulo, theme_color)
        resumen_eventos = {}
        if not df_pdf.empty:
            mask = df_pdf[['Nivel Evento 1', 'Nivel Evento 2', 'Nivel Evento 3', 'Nivel Evento 4']].apply(
                lambda row: any(isinstance(val, str) and any(kw in val.upper() for kw in palabras_clave) for val in row), axis=1)
            df_ev = df_pdf[mask]
            for _, r in df_ev.iterrows():
                t = float(r['Tiempo (Min)'])
                for op in str(r['Operador']).split('/'):
                    op = op.strip()
                    if op and op != '-':
                        if op not in resumen_eventos: resumen_eventos[op] = {'tiempo': 0.0, 'cantidad': 0}
                        resumen_eventos[op]['tiempo'] += t; resumen_eventos[op]['cantidad'] += 1

        if resumen_eventos:
            df_res = pd.DataFrame([{'Operador': k, 'Minutos': v['tiempo'], 'Cantidad': v['cantidad']} for k, v in resumen_eventos.items()]).sort_values('Minutos', ascending=False)
            df_res['Promedio'] = df_res['Minutos'] / df_res['Cantidad']
            
            def dibujar_cabeza_t():
                setup_table_header(pdf, theme_color); pdf.set_font("Arial", 'B', 9)
                pdf.cell(70, 6, "Operador", 1, 0, 'C', True)
                pdf.cell(40, 6, "Total Min", 1, 0, 'C', True)
                pdf.cell(40, 6, "Cant. Veces", 1, 0, 'C', True)
                pdf.cell(40, 6, "Promedio Min", 1, 1, 'C', True)

            dibujar_cabeza_t()
            setup_table_row(pdf); pdf.set_font("Arial", '', 9)
            for _, r in df_res.iterrows():
                if pdf.get_y() > 270: 
                    pdf.add_page(); dibujar_cabeza_t(); setup_table_row(pdf); pdf.set_font("Arial", '', 9)
                
                is_over = False
                if p_tipo == "Diario":
                    if r['Minutos'] > limite_minutos: is_over = True
                else:
                    if r['Promedio'] > limite_minutos: is_over = True

                pdf.set_text_color(50, 50, 50)
                pdf.cell(70, 5, " " + clean_text(r['Operador'])[:35], 'B')
                
                if is_over: pdf.set_text_color(220, 20, 20)
                else: pdf.set_text_color(50, 50, 50)
                
                pdf.cell(40, 5, f"{r['Minutos']:.1f}", 'B', 0, 'C')
                
                pdf.set_text_color(50, 50, 50)
                pdf.cell(40, 5, str(int(r['Cantidad'])), 'B', 0, 'C')
                
                if is_over: pdf.set_text_color(220, 20, 20)
                else: pdf.set_text_color(50, 50, 50)
                
                pdf.cell(40, 5, f"{r['Promedio']:.1f}", 'B', 1, 'C')
                pdf.set_text_color(50, 50, 50) # Reset final
            pdf.ln(5)
        else:
            pdf.set_font("Arial", 'I', 10); pdf.cell(0, 10, clean_text("No hay registros de tiempo acumulado para este ítem en el período."), ln=True)

    pdf.set_link(link_tiempos)
    agregar_tabla_tiempos("Tiempo de Baño Acumulado", ["BAÑO", "BANO"], limite_minutos=8)
    agregar_tabla_tiempos("Tiempo de Refrigerio Acumulado", ["REFRIGERIO"], limite_minutos=17)

    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 5.5. EDITOR MANUAL DEL REPORTE (NUEVO)
# ==========================================
st.divider()
with st.expander("🛠️ Editor Manual de Datos (Ajustes antes de exportar el PDF)", expanded=False):
    st.markdown("Utiliza estas tablas para alterar los datos. **Los cambios que realices aquí se reflejarán directamente en los totales, gráficos e indicadores del PDF (tanto Diario como Semanal o Mensual).**")

    # --- 1. OCULTAR MÁQUINAS ---
    st.markdown("#### 1. Ocultar Máquinas")
    maquinas_lista = sorted(df_metrics['Máquina'].unique().tolist()) if not df_metrics.empty else []
    maq_ocultas = st.multiselect("Selecciona las máquinas que NO quieres que aparezcan en este reporte:", maquinas_lista)

    # --- 2. EDITAR KPIs Y HORAS TOTALES ---
    st.markdown("#### 2. Modificar KPIs y Horas Totales por Máquina")
    st.info("💡 **Tip:** Si eliminas una falla en el paso 4, recuerda ajustar aquí el **T_Parada** (restando esos minutos) y el **T_Operativo** (sumándolos) para que los cuadros resumen de arriba coincidan. También puedes sobreescribir el % de OEE y demás indicadores.")
    if not df_metrics.empty:
        df_metrics = st.data_editor(
            df_metrics,
            disabled=["Máquina"], 
            hide_index=True,
            key="editor_kpi",
            use_container_width=True
        )
    else:
        st.caption("No hay métricas cargadas.")

    # --- 3. EDITAR PRODUCCIÓN ---
    st.markdown("#### 3. Modificar Desglose de Producción")
    st.caption("Ajusta manualmente la cantidad de piezas Buenas, Retrabajo u Observadas por código de producto.")
    if not pdf_df_prod_target.empty:
        pdf_df_prod_target = st.data_editor(
            pdf_df_prod_target,
            disabled=["Máquina", "Código"],
            hide_index=True,
            key="editor_prod",
            use_container_width=True
        )
    else:
        st.caption("No hay datos de producción.")

    # --- 4. EDITAR EVENTOS, HORARIOS Y FALLAS ---
    st.markdown("#### 4. Modificar Horarios o Eliminar Eventos (Fallas/Paradas)")
    st.caption("Para **eliminar un evento**, selecciona la casilla izquierda de la fila y presiona la tecla `Suprimir` (o el ícono de la papelera). Puedes modificar `Inicio_Str`, `Fin_Str` y `Tiempo (Min)` directamente en las celdas.")
    if not df_raw.empty:
        df_raw = st.data_editor(
            df_raw,
            num_rows="dynamic", 
            column_config={
                "Evento_Id": None,
                "Categoria_Macro": None,
                "Estado_Global": st.column_config.TextColumn(disabled=True),
            },
            key="editor_eventos",
            use_container_width=True
        )
    else:
        st.caption("No hay eventos en este período para editar.")

    # --- 5. EDITAR PERFORMANCE OPERARIOS ---
    st.markdown("#### 5. Modificar Performance de Operarios")
    st.caption("Si necesitas corregir el porcentaje de rendimiento de algún operador, hazlo aquí.")
    if not pdf_df_op_target.empty:
        pdf_df_op_target = st.data_editor(
            pdf_df_op_target,
            disabled=["Operador", "Fábrica"],
            hide_index=True,
            key="editor_op",
            use_container_width=True
        )
    else:
        st.caption("No hay datos de operarios.")

# --- APLICAR FILTRO DE MÁQUINAS OCULTAS AL RESTO DEL CÓDIGO ---
if maq_ocultas:
    df_metrics = df_metrics[~df_metrics['Máquina'].isin(maq_ocultas)]
    if not df_metrics_std.empty:
        df_metrics_std = df_metrics_std[~df_metrics_std['Máquina'].isin(maq_ocultas)]
    if not df_piezas_excluidas.empty:
        df_piezas_excluidas = df_piezas_excluidas[~df_piezas_excluidas['Máquina'].isin(maq_ocultas)]
    df_raw = df_raw[~df_raw['Máquina'].isin(maq_ocultas)]
    pdf_df_prod_target = pdf_df_prod_target[~pdf_df_prod_target['Máquina'].isin(maq_ocultas)]
    df_trend = df_trend[~df_trend['Máquina'].isin(maq_ocultas)]
    if not df_horarios.empty:
        df_horarios = df_horarios[~df_horarios['Máquina'].isin(maq_ocultas)]


# ==========================================
# 6. INTERFAZ STREAMLIT FINAL (BOTONES)
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
                    pdf_data = crear_pdf("Estampado", pdf_label, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo, df_trend, df_metrics, df_horarios, df_metrics_std, df_piezas_excluidas)
                    st.download_button("Descargar Estampado", data=pdf_data, file_name=f"Estampado_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    with col_btn2:
        if st.button("Reporte SOLDADURA", use_container_width=True):
            with st.spinner("Generando PDF Soldadura..."):
                try:
                    pdf_data = crear_pdf("Soldadura", pdf_label, pdf_df_op_target, pdf_df_prod_target, df_raw, pdf_tipo, df_trend, df_metrics, df_horarios, df_metrics_std, df_piezas_excluidas)
                    st.download_button("Descargar Soldadura", data=pdf_data, file_name=f"Soldadura_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")
                    
    if pdf_tipo == "Mensual":
        with col_btn3:
            if st.button("Resumen Ejecutivo", use_container_width=True):
                with st.spinner("Generando Resumen Ejecutivo Global..."):
                    try:
                        pdf_resumen = crear_pdf_resumen_ejecutivo(pdf_label, df_trend, df_metrics, df_metrics_std, df_piezas_excluidas)
                        st.download_button("Descargar Resumen", data=pdf_resumen, file_name=f"Resumen_Global_Planta_{file_label}.pdf", mime="application/pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")
