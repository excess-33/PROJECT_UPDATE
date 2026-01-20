import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')
import os

# Импортируем функции подготовки из main.py
from main import load_and_prepare, add_price_ppm2

# ЗАГРУЖАЕМ ДАННЫЕ
print("Загрузка и подготовка данных через main.py...")
df = load_and_prepare('melb_data.csv')
df = add_price_ppm2(df)

# Дополнительные поля для визуализаций
df['YearMonth'] = df['Date'].dt.to_period('M').astype(str)
type_map = {'h': 'Дом', 'u': 'Квартира', 't': 'Таунхаус'}
df['TypeName'] = df['Type'].map(type_map)

print(f"Подготовлено {len(df)} записей")
print(f"Период данных: {df['Date'].min()} - {df['Date'].max()}")

os.makedirs('output', exist_ok=True)

# ============== 1. КАРТА С МЕДИАННОЙ ЦЕНОЙ ПО ПРИГОРОДАМ ==============
print("\n1. Карта с медианной ценой по пригородам...")

df_map = df.dropna(subset=['Lattitude', 'Longtitude', 'Price', 'Suburb']).copy()
suburb_agg = df_map.groupby('Suburb').agg({
    'Price': 'median',
    'Lattitude': 'mean',
    'Longtitude': 'mean',
    'Rooms': 'mean',
    'BuildingArea': 'median'
}).reset_index()

fig1 = px.scatter_mapbox(
    suburb_agg,
    lat='Lattitude',
    lon='Longtitude',
    size='Price',
    color='Price',
    hover_name='Suburb',
    hover_data={'Price': ':,.0f', 'Rooms': ':.1f', 'BuildingArea': ':.0f'},
    zoom=9,
    mapbox_style="open-street-map",
    title="Медианная цена по пригородам (размер = цена)",
    color_continuous_scale="Viridis",
    size_max=30
)
fig1.update_layout(height=700, coloraxis_colorbar=dict(title="Цена, $"))
fig1.write_html("output/1_map_median_price.html")
print("   ✓ Сохранено: output/1_map_median_price.html")

# ============== 2. ТОП-20 ПРИГОРОДОВ ПО МЕДИАННОЙ ЦЕНЕ ==============
print("\n2. Топ-20 самых дорогих пригородов...")

top_suburbs = df.groupby('Suburb').agg({
    'Price': ['median', 'count']
}).reset_index()
top_suburbs.columns = ['Suburb', 'MedianPrice', 'Count']
top_suburbs = top_suburbs[top_suburbs['Count'] >= 10]
top_suburbs = top_suburbs.nlargest(20, 'MedianPrice')

fig2 = px.bar(
    top_suburbs,
    x='MedianPrice',
    y='Suburb',
    orientation='h',
    title="Топ-20 самых дорогих пригородов (≥10 продаж)",
    labels={'MedianPrice': 'Медианная цена, $', 'Suburb': 'Пригород'},
    color='MedianPrice',
    color_continuous_scale='Reds',
    text='MedianPrice'
)
fig2.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig2.update_layout(height=600, showlegend=False, yaxis={'categoryorder': 'total ascending'})
fig2.write_html("output/2_top20_suburbs.html")
print("   ✓ Сохранено: output/2_top20_suburbs.html")

# ============== 3. РАСПРЕДЕЛЕНИЕ ЦЕН ПО ТИПАМ НЕДВИЖИМОСТИ ==============
print("\n3. Распределение цен по типам...")

df_types = df.dropna(subset=['TypeName', 'Price']).copy()

fig3 = go.Figure()
for type_name in ['Дом', 'Квартира', 'Таунхаус']:
    type_data = df_types[df_types['TypeName'] == type_name]['Price']
    fig3.add_trace(go.Box(
        y=type_data,
        name=type_name,
        boxmean='sd'
    ))

fig3.update_layout(
    title="Распределение цен по типам недвижимости",
    yaxis_title="Цена, $",
    height=600,
    showlegend=True
)
fig3.write_html("output/3_price_by_type.html")
print("   ✓ Сохранено: output/3_price_by_type.html")

# ============== 4. ДИНАМИКА МЕДИАННЫХ ЦЕН ПО МЕСЯЦАМ ==============
print("\n4. Динамика цен по месяцам...")

df_time = df.dropna(subset=['YearMonth', 'Price', 'TypeName']).copy()
time_agg = df_time.groupby(['YearMonth', 'TypeName'])['Price'].median().reset_index()

fig4 = px.line(
    time_agg,
    x='YearMonth',
    y='Price',
    color='TypeName',
    title="Динамика медианных цен по типам недвижимости",
    labels={'YearMonth': 'Месяц', 'Price': 'Медианная цена, $', 'TypeName': 'Тип'},
    markers=True
)
fig4.update_xaxes(tickangle=45)
fig4.update_layout(height=500)
fig4.write_html("output/4_price_dynamics.html")
print("   ✓ Сохранено: output/4_price_dynamics.html")

# ============== 5. ЦЕНА ЗА М² ПО РЕГИОНАМ ==============
print("\n5. Цена за м² по регионам...")

df_region = df.dropna(subset=['Regionname', 'PricePerM2', 'TypeName']).copy()
df_region = df_region[df_region['PricePerM2'] < df_region['PricePerM2'].quantile(0.95)]

region_agg = df_region.groupby(['Regionname', 'TypeName']).agg({
    'PricePerM2': 'median',
    'Price': 'count'
}).reset_index()
region_agg.columns = ['Regionname', 'TypeName', 'MedianPricePerM2', 'Count']

fig5 = px.bar(
    region_agg,
    x='Regionname',
    y='MedianPricePerM2',
    color='TypeName',
    barmode='group',
    title="Медианная цена за м² по регионам и типам",
    labels={'MedianPricePerM2': 'Цена за м², $', 'Regionname': 'Регион', 'TypeName': 'Тип'},
    text='MedianPricePerM2'
)
fig5.update_traces(texttemplate='$%{text:.0f}', textposition='outside')
fig5.update_xaxes(tickangle=45)
fig5.update_layout(height=600)
fig5.write_html("output/5_price_per_m2_regions.html")
print("   ✓ Сохранено: output/5_price_per_m2_regions.html")

# ============== 6. КОРРЕЛЯЦИОННАЯ МАТРИЦА ==============
print("\n6. Корреляционная матрица...")

corr_cols = ['Price', 'Rooms', 'Bathroom', 'Car', 'Landsize', 'BuildingArea', 
             'Distance', 'Propertycount', 'HouseAge', 'PricePerM2']
df_corr = df[corr_cols].dropna()

corr_matrix = df_corr.corr()

fig6 = go.Figure(data=go.Heatmap(
    z=corr_matrix.values,
    x=corr_matrix.columns,
    y=corr_matrix.columns,
    colorscale='RdBu',
    zmid=0,
    text=np.round(corr_matrix.values, 2),
    texttemplate='%{text}',
    textfont={"size": 10},
    colorbar=dict(title="Корреляция")
))

fig6.update_layout(
    title="Корреляционная матрица ключевых показателей",
    height=700,
    xaxis={'side': 'bottom'},
    yaxis={'side': 'left'}
)
fig6.write_html("output/6_correlation_matrix.html")
print("   ✓ Сохранено: output/6_correlation_matrix.html")

# ============== 7. ЦЕНА VS РАССТОЯНИЕ ОТ ЦЕНТРА ==============
print("\n7. Цена vs расстояние от центра...")

df_dist = df.dropna(subset=['Distance', 'Price', 'TypeName']).copy()
df_dist = df_dist[df_dist['Price'] < df_dist['Price'].quantile(0.95)]

# Агрегируем по расстоянию для уменьшения шума
distance_agg = df_dist.groupby(['Distance', 'TypeName'])['Price'].median().reset_index()

fig7 = px.scatter(
    distance_agg,
    x='Distance',
    y='Price',
    color='TypeName',
    title="Зависимость цены от расстояния до центра",
    labels={'Distance': 'Расстояние от CBD, км', 'Price': 'Медианная цена, $', 'TypeName': 'Тип'},
    opacity=0.7
)
fig7.update_layout(height=600)
fig7.write_html("output/7_price_vs_distance.html")
print("   ✓ Сохранено: output/7_price_vs_distance.html")

# ============== 8. СРЕДНЯЯ ЦЕНА ПО КОЛИЧЕСТВУ КОМНАТ ==============
print("\n8. Цена по количеству комнат...")

df_rooms = df.dropna(subset=['Rooms', 'Price', 'TypeName']).copy()
df_rooms = df_rooms[df_rooms['Rooms'] <= 6]

rooms_agg = df_rooms.groupby(['Rooms', 'TypeName']).agg({
    'Price': ['median', 'count']
}).reset_index()
rooms_agg.columns = ['Rooms', 'TypeName', 'MedianPrice', 'Count']
rooms_agg = rooms_agg[rooms_agg['Count'] >= 10]

fig8 = px.bar(
    rooms_agg,
    x='Rooms',
    y='MedianPrice',
    color='TypeName',
    barmode='group',
    title="Медианная цена по количеству комнат (≥10 продаж)",
    labels={'Rooms': 'Количество комнат', 'MedianPrice': 'Медианная цена, $', 'TypeName': 'Тип'},
    text='MedianPrice'
)
fig8.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig8.update_layout(height=600)
fig8.write_html("output/8_price_by_rooms.html")
print("   ✓ Сохранено: output/8_price_by_rooms.html")

# ============== 9. КОЛИЧЕСТВО ПРОДАЖ ПО МЕТОДАМ ==============
print("\n9. Методы продажи и их цены...")

df_method = df.dropna(subset=['Method', 'Price']).copy()
method_names = {
    'S': 'Продажа',
    'SP': 'Продажа по цене',
    'PI': 'Продажа до аукциона',
    'VB': 'Цена продавца',
    'SA': 'Продано после аукциона'
}
df_method['MethodName'] = df_method['Method'].map(method_names)

method_agg = df_method.groupby('MethodName').agg({
    'Price': ['median', 'count']
}).reset_index()
method_agg.columns = ['Method', 'MedianPrice', 'Count']

fig9 = make_subplots(
    rows=1, cols=2,
    subplot_titles=('Количество продаж по методам', 'Медианная цена по методам'),
    specs=[[{'type': 'bar'}, {'type': 'bar'}]]
)

fig9.add_trace(
    go.Bar(x=method_agg['Method'], y=method_agg['Count'], name='Количество', marker_color='steelblue'),
    row=1, col=1
)

fig9.add_trace(
    go.Bar(x=method_agg['Method'], y=method_agg['MedianPrice'], name='Медианная цена', marker_color='coral'),
    row=1, col=2
)

fig9.update_xaxes(tickangle=45)
fig9.update_layout(height=500, showlegend=False, title_text="Анализ методов продажи")
fig9.write_html("output/9_sales_methods.html")
print("   ✓ Сохранено: output/9_sales_methods.html")

# ============== 10. ИНТЕРАКТИВНАЯ ТАБЛИЦА СВОДКИ ==============
print("\n10. Интерактивная сводная таблица по регионам...")

summary = df.groupby(['Regionname', 'TypeName']).agg({
    'Price': ['median', 'mean', 'count'],
    'PricePerM2': 'median',
    'BuildingArea': 'median',
    'Rooms': 'mean'
}).reset_index()

summary.columns = ['Регион', 'Тип', 'Медиана цены', 'Средняя цена', 'Количество', 
                   'Цена за м²', 'Площадь', 'Комнат']

summary = summary.round({'Медиана цены': 0, 'Средняя цена': 0, 'Цена за м²': 0, 
                         'Площадь': 0, 'Комнат': 1})

fig10 = go.Figure(data=[go.Table(
    header=dict(
        values=list(summary.columns),
        fill_color='steelblue',
        align='left',
        font=dict(color='white', size=12)
    ),
    cells=dict(
        values=[summary[col] for col in summary.columns],
        fill_color='lavender',
        align='left',
        font=dict(size=11)
    )
)])

fig10.update_layout(
    title="Сводная таблица по регионам и типам",
    height=800
)
fig10.write_html("output/10_summary_table.html")
print("   ✓ Сохранено: output/10_summary_table.html")

print("\n" + "="*60)
print("\nФайлы в папке 'output/':")
print("1.  Карта медианных цен по пригородам")
print("2.  Топ-20 самых дорогих пригородов")
print("3.  Распределение цен по типам (box plot)")
print("4.  Динамика цен по месяцам")
print("5.  Цена за м² по регионам и типам")
print("6.  Корреляционная матрица")
print("7.  Зависимость цены от расстояния")
print("8.  Цена по количеству комнат")
print("9.  Анализ методов продажи")
print("10. Сводная таблица по регионам")
