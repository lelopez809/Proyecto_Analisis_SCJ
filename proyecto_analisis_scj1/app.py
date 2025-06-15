import os
from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
import warnings

# Ignoramos advertencias para mantener la consola limpia
warnings.filterwarnings("ignore", category=FutureWarning)

app = Flask(__name__)

# --- CONFIGURACIÓN Y CARGA DE DATOS DESDE LA BASE DE DATOS ---
db_engine = None
df_global = pd.DataFrame()

try:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        db_engine = create_engine(DATABASE_URL)
        df_global = pd.read_sql("SELECT * FROM sentencias", db_engine)
        
        df_global['Año'] = pd.to_numeric(df_global['Año'], errors='coerce').astype('Int64')
        def categorizar_resultado(resultado):
            if 'Favorable' in str(resultado): return 'Favorable'
            elif 'Desfavorable' in str(resultado): return 'Desfavorable'
            else: return 'Mixto / Otro'
        df_global['Categoria_Resultado'] = df_global['Resultado_Causa'].apply(categorizar_resultado)
        print(">>> Conexión a la BD y carga de datos inicial exitosa.")
    else:
        print(">>> ERROR CRÍTICO: La variable de entorno DATABASE_URL no está definida.")
except Exception as e:
    print(f">>> ERROR AL CONECTAR O CARGAR DATOS DESDE LA BASE DE DATOS: {e}")

coordenadas_rd = {
    "Distrito Nacional": {"lat": 18.4861, "lon": -69.9312}, "Santiago": {"lat": 19.4517, "lon": -70.6970},
    "Santo Domingo": {"lat": 18.5001, "lon": -69.8887}, "La Vega": {"lat": 19.2240, "lon": -70.5287},
    "San Pedro De Macorís": {"lat": 18.4542, "lon": -69.3086}, "San Cristóbal": {"lat": 18.4184, "lon": -70.1034},
    "Duarte": {"lat": 19.2995, "lon": -70.1299}, "La Romana": {"lat": 18.4273, "lon": -68.9728},
    "Puerto Plata": {"lat": 19.7808, "lon": -70.6871}, "La Altagracia": {"lat": 18.6148, "lon": -68.7077},
    "Espaillat": {"lat": 19.5000, "lon": -70.4167}, "San Juan": {"lat": 18.8052, "lon": -71.2334},
    "Barahona": {"lat": 18.2085, "lon": -71.0995}, "Azua": {"lat": 18.4533, "lon": -70.7347},
    "Monseñor Nouel": {"lat": 18.9221, "lon": -70.3846}, "San Francisco De Macorís": {"lat": 19.3079, "lon": -70.2547}
}

@app.route('/')
def index():
    if df_global.empty:
        return "<h1>Error Crítico</h1><p>No se pudieron cargar los datos desde la base de datos. Revisa los logs del servidor.</p>"

    # Lógica de Filtros
    selected_depto = request.args.get('departamento', 'Todos')
    selected_resultado = request.args.get('resultado', 'Todos')
    selected_derecho = request.args.get('derecho', 'Todos')
    selected_año = request.args.get('año', 'Todos')

    df_filtrado_base = df_global.copy()
    if selected_depto != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Departamento_Judicial'] == selected_depto]
    if selected_resultado != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Categoria_Resultado'] == selected_resultado]
    if selected_derecho != 'Todos':
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Tipo_Derecho'] == selected_derecho]
    
    # Generación de Gráfico de Tendencias
    df_tendencia = df_filtrado_base.groupby('Año').agg(Total_Casos=('Archivo', 'count'), Casos_Favorables=('Categoria_Resultado', lambda x: (x == 'Favorable').sum())).reset_index()
    trend_chart_div = "<h6>No hay datos de tendencia para esta selección.</h6>"
    if not df_tendencia.empty and len(df_tendencia) > 1:
        df_tendencia['Tasa_Ganancia'] = round((df_tendencia['Casos_Favorables'] / df_tendencia['Total_Casos']) * 100, 1)
        trend_chart_fig = make_subplots(specs=[[{"secondary_y": True}]])
        trend_chart_fig.add_trace(go.Bar(x=df_tendencia['Año'], y=df_tendencia['Total_Casos'], name='Total de Casos', marker_color='#0d6efd', opacity=0.7), secondary_y=False)
        trend_chart_fig.add_trace(go.Scatter(x=df_tendencia['Año'], y=df_tendencia['Tasa_Ganancia'], name='Tasa de Ganancia (%)', marker_color='#d62728'), secondary_y=True)
        trend_chart_fig.update_layout(title_text='Evolución Anual de Casos y Tasa de Ganancia', title_x=0.5, template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        trend_chart_fig.update_yaxes(title_text="Total de Casos", secondary_y=False)
        trend_chart_fig.update_yaxes(title_text="Tasa de Ganancia (%)", secondary_y=True)
        trend_chart_fig.update_xaxes(type='category')
        trend_chart_div = trend_chart_fig.to_html(full_html=False)
    
    # Aplicar filtro de Año para el resto de elementos
    df_filtrado = df_filtrado_base.copy()
    if selected_año != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Año'] == int(selected_año)]
    
    kpis, pie_chart_div, keyword_chart_div, map_div = generar_graficos_filtrados(df_filtrado)
        
    # --- TEXTO ANALÍTICO PROFESIONAL PARA TESIS ---
    texto_analitico = f"""
        <h5 class="card-title mb-3">Análisis de Hallazgos Jurisprudenciales</h5>
        
        <h6>I. Introducción y Metodología</h6>
        <p class="card-text small">El presente estudio analiza un corpus de <strong>{len(df_global)} sentencias</strong> emitidas por la SCJ (2011-2023) en materia laboral con mujeres como demandantes. La metodología empleó la extracción automatizada de texto y técnicas de Procesamiento de Lenguaje Natural (NLP) para la clasificación de decisiones y el análisis temático.</p>
        
        <h6>II. Análisis Cuantitativo de Resultados</h6>
        <p class="card-text small">De las <strong>{kpis['total']} sentencias</strong> que cumplen los criterios de filtrado, se observa una notoria tasa de <strong>"ganancia de causa" del {kpis['porcentaje']}%</strong>. Es fundamental matizar que una porción considerable de estas victorias se materializa por la desestimación de recursos por razones procesales (inadmisibilidad, caducidad), consolidando así decisiones de instancias inferiores.</p>
        
        <h6>III. Análisis Cualitativo del Discurso Judicial</h6>
        <p class="card-text small">El análisis de frecuencia de conceptos revela una clara <strong>predominancia del paradigma jurídico-laboral tradicional</strong>. La argumentación se basa fuertemente en el <strong>Código de Trabajo y la Ley 87-01</strong>, con una incidencia consistentemente baja de terminología de género explícita a lo largo de los años.</p>

        <h6>IV. Conclusión e Hipótesis</h6>
        <p class="card-text small">Los datos presentan una dualidad: una alta eficacia judicial a favor de las mujeres, que coexiste con una baja visibilidad de un discurso de género explícito. La protección se otorga en base al rol de "trabajadora", abriendo la interrogante para futuras investigaciones sobre la aplicación implícita de un enfoque de género.</p>
    """
    
    # Opciones para los filtros
    opciones_depto = ['Todos'] + sorted(df_global['Departamento_Judicial'].dropna().unique().tolist())
    opciones_resultado = ['Todos', 'Favorable', 'Desfavorable', 'Mixto / Otro']
    opciones_derecho = ['Todos'] + sorted(df_global['Tipo_Derecho'].dropna().unique().tolist())
    opciones_año = ['Todos'] + sorted(df_global['Año'].dropna().unique().tolist(), reverse=True)

    return render_template(
        'index.html', 
        kpis=kpis, pie_chart_div=pie_chart_div, keyword_chart_div=keyword_chart_div, 
        trend_chart_div=trend_chart_div, map_div=map_div,
        analysis_text=texto_analitico,
        opciones_depto=opciones_depto, selected_depto=selected_depto,
        opciones_resultado=opciones_resultado, selected_resultado=selected_resultado,
        opciones_derecho=opciones_derecho, selected_derecho=selected_derecho,
        opciones_año=opciones_año, selected_año=selected_año
    )

def generar_graficos_filtrados(df_filtrado):
    kpis = {
        "total": len(df_filtrado),
        "favorables": (df_filtrado['Categoria_Resultado'] == 'Favorable').sum(),
        "porcentaje": round(((df_filtrado['Categoria_Resultado'] == 'Favorable').sum() / len(df_filtrado)) * 100, 1) if len(df_filtrado) > 0 else 0
    }

    conteo_categorias = df_filtrado['Categoria_Resultado'].value_counts()
    pie_chart_div = "<h6>No hay datos para esta selección.</h6>"
    if not conteo_categorias.empty:
        pie_fig = px.pie(conteo_categorias, values=conteo_categorias.values, names=conteo_categorias.index, title='Proporción de Resultados', color_discrete_map={'Favorable':'#28a745', 'Desfavorable':'#dc3545', 'Mixto / Otro':'#ffc107'})
        pie_fig.update_layout(title_x=0.5, template="plotly_white", legend_title_text='Categoría', legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        pie_chart_div = pie_fig.to_html(full_html=False)

    columnas_lemas = [col for col in df_filtrado.columns if 'lema_' in col]
    frecuencia_total = df_filtrado[columnas_lemas].sum().sort_values(ascending=False).head(15).sort_values(ascending=True)
    keyword_chart_div = "<h6>No hay datos para esta selección.</h6>"
    if not frecuencia_total[frecuencia_total > 0].empty:
        frecuencia_total = frecuencia_total[frecuencia_total > 0]
        frecuencia_total.index = frecuencia_total.index.str.replace('lema_', '', regex=False).str.capitalize()
        keyword_fig = px.bar(frecuencia_total, x=frecuencia_total.values, y=frecuencia_total.index, orientation='h', title='Top Conceptos Más Frecuentes', text_auto=True)
        keyword_fig.update_layout(xaxis_title=None, yaxis_title=None, title_x=0.5, template="plotly_white")
        keyword_fig.update_traces(marker_color='#17a2b8')
        keyword_chart_div = keyword_fig.to_html(full_html=False)
    
    conteo_demarcaciones = df_filtrado[df_filtrado['Departamento_Judicial'] != 'No Especificado']['Departamento_Judicial'].value_counts().reset_index()
    conteo_demarcaciones.columns = ['Departamento', 'Cantidad']
    conteo_demarcaciones['lat'] = conteo_demarcaciones['Departamento'].map(lambda d: coordenadas_rd.get(d, {}).get('lat'))
    conteo_demarcaciones['lon'] = conteo_demarcaciones['Departamento'].map(lambda d: coordenadas_rd.get(d, {}).get('lon'))
    conteo_demarcaciones.dropna(subset=['lat', 'lon'], inplace=True)
    map_div = "<h6>No hay datos geográficos para esta selección.</h6>"
    if not conteo_demarcaciones.empty:
        # ===== ¡LA CORRECCIÓN ESTÁ AQUÍ! Volvemos a scatter_mapbox =====
        map_fig = px.scatter_mapbox(conteo_demarcaciones, lat="lat", lon="lon", size="Cantidad", color="Cantidad", hover_name="Departamento", hover_data={"lat": False, "lon": False, "Cantidad": True}, color_continuous_scale=px.colors.sequential.Plasma, size_max=50, title="Distribución Geográfica de Casos")
        map_fig.update_layout(mapbox_style="carto-positron", mapbox_center_lat=18.7357, mapbox_center_lon=-70.1627, mapbox_zoom=7.5, margin={"r":0,"t":40,"l":0,"b":0}, title_x=0.5)
        map_div = map_fig.to_html(full_html=False)
        
    return kpis, pie_chart_div, keyword_chart_div, map_div, texto_analitico

if __name__ == '__main__':
    app.run(debug=True)
