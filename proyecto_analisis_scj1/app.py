from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

app = Flask(__name__)

# --- Carga de datos y preparación ---
try:
    # Leemos el archivo de Excel definitivo y correcto
    df_global = pd.read_excel("analisis_final_definitivo.xlsx")
    
    # Aseguramos que la columna 'Año' sea tratada correctamente
    df_global['Año'] = pd.to_numeric(df_global['Año'], errors='coerce')
    df_global.dropna(subset=['Año'], inplace=True)
    df_global['Año'] = df_global['Año'].astype(int)
    
    # Creamos la categoría de resultado para los filtros y gráficos
    def categorizar_resultado(resultado):
        if 'Favorable' in resultado: return 'Favorable'
        elif 'Desfavorable' in resultado: return 'Desfavorable'
        else: return 'Mixto / Otro'
    df_global['Categoria_Resultado'] = df_global['Resultado_Causa'].apply(categorizar_resultado)
except FileNotFoundError:
    df_global = None

# Diccionario de coordenadas (no cambia)
coordenadas_rd = {
    "Distrito Nacional": {"lat": 18.4861, "lon": -69.9312}, "Santiago": {"lat": 19.4517, "lon": -70.6970},
    "Santo Domingo": {"lat": 18.5001, "lon": -69.8887}, "La Vega": {"lat": 19.2240, "lon": -70.5287},
    "San Pedro De Macorís": {"lat": 18.4542, "lon": -69.3086}, "San Cristóbal": {"lat": 18.4184, "lon": -70.1034},
    "Duarte": {"lat": 19.2995, "lon": -70.1299}, "La Romana": {"lat": 18.4273, "lon": -68.9728},
    "Puerto Plata": {"lat": 19.7808, "lon": -70.6871}, "La Altagracia": {"lat": 18.6148, "lon": -68.7077},
    "Espaillat": {"lat": 19.5000, "lon": -70.4167}, "San Juan": {"lat": 18.8052, "lon": -71.2334},
    "Barahona": {"lat": 18.2085, "lon": -71.0995}, "Azua": {"lat": 18.4533, "lon": -70.7347},
    "Monseñor Nouel": {"lat": 18.9221, "lon": -70.3846}
}

@app.route('/')
def index():
    if df_global is None:
        return "<h1>Error</h1><p>No se encontró el archivo 'analisis_final_definitivo.xlsx'.</p>"

    # --- 1. LEER FILTROS (INCLUYENDO EL AÑO) ---
    selected_depto = request.args.get('departamento', 'Todos')
    selected_resultado = request.args.get('resultado', 'Todos')
    selected_derecho = request.args.get('derecho', 'Todos')
    selected_año = request.args.get('año', 'Todos')

    # --- 2. FILTRAR DATAFRAME BASE (para tendencias) ---
    df_filtrado_base = df_global.copy()
    if selected_depto != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Departamento_Judicial'] == selected_depto]
    if selected_resultado != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Categoria_Resultado'] == selected_resultado]
    if selected_derecho != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Tipo_Derecho'] == selected_derecho]
    
    # --- 3. GENERAR GRÁFICO DE TENDENCIAS ---
    df_tendencia = df_filtrado_base.groupby('Año').agg(Total_Casos=('Archivo', 'count'), Casos_Favorables=('Categoria_Resultado', lambda x: (x == 'Favorable').sum())).reset_index()
    trend_chart_div = "<h6>No hay datos de tendencia para esta selección.</h6>"
    if not df_tendencia.empty:
        df_tendencia['Tasa_Ganancia'] = round((df_tendencia['Casos_Favorables'] / df_tendencia['Total_Casos']) * 100, 1)
        trend_chart_fig = make_subplots(specs=[[{"secondary_y": True}]])
        trend_chart_fig.add_trace(go.Bar(x=df_tendencia['Año'], y=df_tendencia['Total_Casos'], name='Total de Casos', marker_color='#0d6efd', opacity=0.7), secondary_y=False)
        trend_chart_fig.add_trace(go.Scatter(x=df_tendencia['Año'], y=df_tendencia['Tasa_Ganancia'], name='Tasa de Ganancia (%)', marker_color='#d62728'), secondary_y=True)
        trend_chart_fig.update_layout(title_text='Evolución Anual de Casos y Tasa de Ganancia', title_x=0.5, template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        trend_chart_fig.update_yaxes(title_text="Total de Casos", secondary_y=False)
        trend_chart_fig.update_yaxes(title_text="Tasa de Ganancia (%)", secondary_y=True)
        trend_chart_fig.update_xaxes(type='category') # Tratamos el año como categoría para evitar comas
        trend_chart_div = trend_chart_fig.to_html(full_html=False)

    # --- 4. APLICAR FILTRO DE AÑO PARA EL RESTO DE ELEMENTOS ---
    df_filtrado = df_filtrado_base.copy()
    if selected_año != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Año'] == int(selected_año)]
    
    # --- 5. GENERAR OTROS GRÁFICOS Y KPIS ---
    kpis, pie_chart_div, keyword_chart_div, map_div = generar_graficos_filtrados(df_filtrado)
        
    # --- 6. PREPARAR OPCIONES PARA LOS FILTROS ---
    opciones_depto = ['Todos'] + sorted(df_global['Departamento_Judicial'].unique().tolist())
    opciones_resultado = ['Todos', 'Favorable', 'Desfavorable', 'Mixto / Otro']
    opciones_derecho = ['Todos'] + sorted(df_global['Tipo_Derecho'].unique().tolist())
    opciones_año = ['Todos'] + sorted(df_global['Año'].unique().tolist(), reverse=True)

    return render_template('index.html', 
        kpis=kpis, pie_chart_div=pie_chart_div, keyword_chart_div=keyword_chart_div, 
        trend_chart_div=trend_chart_div, map_div=map_div,
        opciones_depto=opciones_depto, selected_depto=selected_depto,
        opciones_resultado=opciones_resultado, selected_resultado=selected_resultado,
        opciones_derecho=opciones_derecho, selected_derecho=selected_derecho,
        opciones_año=opciones_año, selected_año=selected_año)

def generar_graficos_filtrados(df_filtrado):
    # KPIs
    conteo_categorias = df_filtrado['Categoria_Resultado'].value_counts()
    total_sentencias = len(df_filtrado)
    casos_favorables = conteo_categorias.get('Favorable', 0)
    ganancia_porcentaje = round((casos_favorables / total_sentencias) * 100, 1) if total_sentencias > 0 else 0
    kpis = {"total": total_sentencias, "favorables": casos_favorables, "porcentaje": ganancia_porcentaje}

    # Gráfico de Pastel
    pie_chart_div = "<h6>No hay datos para esta selección.</h6>"
    if not conteo_categorias.empty:
        pie_fig = px.pie(conteo_categorias, values=conteo_categorias.values, names=conteo_categorias.index, title='Proporción de Resultados', color_discrete_map={'Favorable':'#28a745', 'Desfavorable':'#dc3545', 'Mixto / Otro':'#ffc107'})
        pie_fig.update_layout(title_x=0.5, template="plotly_white", legend_title_text='Categoría', legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        pie_chart_div = pie_fig.to_html(full_html=False)

    # Gráfico de Barras de Conceptos
    columnas_lemas = [col for col in df_filtrado.columns if col.startswith('lema_')]
    frecuencia_total = df_filtrado[columnas_lemas].sum().sort_values(ascending=False)
    top_15_lemas = frecuencia_total[frecuencia_total > 0].head(15).sort_values(ascending=True)
    keyword_chart_div = "<h6>No hay datos para esta selección.</h6>"
    if not top_15_lemas.empty:
        top_15_lemas.index = top_15_lemas.index.str.replace('lema_', '').str.capitalize()
        keyword_fig = px.bar(top_15_lemas, x=top_15_lemas.values, y=top_15_lemas.index, orientation='h', title='Top Conceptos Más Frecuentes', text_auto=True)
        keyword_fig.update_layout(xaxis_title=None, yaxis_title=None, title_x=0.5, template="plotly_white")
        keyword_fig.update_traces(marker_color='#17a2b8')
        keyword_chart_div = keyword_fig.to_html(full_html=False)

    # Mapa de Burbujas
    conteo_demarcaciones = df_filtrado[df_filtrado['Departamento_Judicial'] != 'No Especificado']['Departamento_Judicial'].value_counts().reset_index()
    conteo_demarcaciones.columns = ['Departamento', 'Cantidad']
    conteo_demarcaciones['lat'] = conteo_demarcaciones['Departamento'].map(lambda d: coordenadas_rd.get(d, {}).get('lat'))
    conteo_demarcaciones['lon'] = conteo_demarcaciones['Departamento'].map(lambda d: coordenadas_rd.get(d, {}).get('lon'))
    conteo_demarcaciones.dropna(subset=['lat', 'lon'], inplace=True)
    map_div = "<h6>No hay datos geográficos para esta selección.</h6>"
    if not conteo_demarcaciones.empty:
        map_fig = px.scatter_map(conteo_demarcaciones, lat="lat", lon="lon", size="Cantidad", color="Cantidad", hover_name="Departamento", hover_data={"lat": False, "lon": False, "Cantidad": True}, color_continuous_scale=px.colors.sequential.Plasma, size_max=50, title="Distribución Geográfica de Casos")
        map_fig.update_layout(mapbox_style="carto-positron", mapbox_center_lat=18.7357, mapbox_center_lon=-70.1627, mapbox_zoom=7.5, margin={"r":0,"t":40,"l":0,"b":0}, title_x=0.5)
        map_div = map_fig.to_html(full_html=False)
        
    return kpis, pie_chart_div, keyword_chart_div, map_div

if __name__ == '__main__':
    app.run(debug=True)