import pandas as pd
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from unidecode import unidecode
from flask import Flask, render_template, request, json
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods = ['POST'])
def procesar_datos():
    #--------- input del usuario

    buscar = request.form['termino_busqueda']
    a = '-'.join(buscar.replace('%', '%25').split())
    b = '%20'.join(buscar.split())

    #--------- Búsqueda en MeLi

    url = unidecode(f'https://listado.mercadolibre.com.co/{a}#D[A:{b}]')
    lista_articulos = defaultdict(list)
    ingreso_pag = requests.get(url)
    html_soup = BeautifulSoup(ingreso_pag.text, 'html.parser')

    #--------- Extracción de la información

    if len(html_soup.find_all('li', class_= "ui-search-layout__item shops__layout-item")) > 0:
        articulos_mdolibre = html_soup.find_all('li', class_= "ui-search-layout__item shops__layout-item")
    else:
        articulos_mdolibre = html_soup.find_all('li', class_= "ui-search-layout__item")

    try:
        cant_pctos = int(html_soup.find('li', class_="andes-pagination__page-count").text.split()[-1])
    except AttributeError:
        cant_pctos = 0
    if cant_pctos < 5:
        saturacion = "No Saturado"
    elif cant_pctos >= 5 and cant_pctos < 12:
        saturacion = "Poco Saturado"
    elif cant_pctos >= 12 and cant_pctos < 20:
        saturacion = "Saturado"
    elif cant_pctos >= 20 and cant_pctos < 25:
        saturacion = "Muy Saturado"
    else:
        saturacion = "Demasiado Saturado"

    for articulo in articulos_mdolibre:
        # tienda = html_soup.find('p', class_= "ui-search-official-store-label ui-search-item__group__element shops__items-group-details ui-search-color--GRAY").text.split()[1]
        nombre = unidecode(articulo.find('h2', class_="ui-search-item__title").text.lower())
        precio_actual = articulo.find('span', class_="andes-money-amount__fraction").text.split()[0].replace('.','')
        try:
            rating = articulo.find('span', class_="ui-search-reviews__rating-number").text
            cantidad_opiniones = articulo.find('span', class_="ui-search-reviews__amount").text.replace(")", "").replace("(", "")
            # opiniones = articulo.find('div', class_="ui-search-reviews ui-search-item__group__element shops__items-group-details").text.split()
            # if len(opiniones[:4]) > 1:
            #     rating = opiniones[1]
            #     cantidad_opiniones = opiniones[-1].split('.')[2][2:].replace(")", "")
            # else:
            #     rating = 0
            #     cantidad_opiniones = opiniones[0]
        except AttributeError:
            rating = 0
            cantidad_opiniones = 0
        try:
            precio_antes = articulo.find('span', class_='andes-money-amount__fraction').text.replace('.','')
            descuento = articulo.find('span', class_="ui-search-price__discount").text.split()[0]
        except AttributeError:
            precio_antes = 0
            descuento = 0

    #--------- Ingreso al producto   
    
        url_producto = articulo.a.get('href')
        ingreso = requests.get(url_producto)
        html_bs4 = BeautifulSoup(ingreso.text, 'html.parser')
        try:
            categoria = unidecode(html_bs4.find_all('a', class_='andes-breadcrumb__link')[-1].get_text().lower())
        except IndexError:
            categoria = "no categoria"
        try:
            ventas = html_bs4.find('span', class_= 'ui-pdp-subtitle').get_text().split()[2].replace('+', '').replace('mil', '000')
        except (IndexError, AttributeError):
            ventas = 0

    #--------- Guarda cada variable en el diccionario

        lista_articulos['nombre_producto'].append(nombre)
        lista_articulos['precio_actual'].append(precio_actual)
        lista_articulos['precio_antes'].append(precio_antes)
        lista_articulos['descuento'].append(descuento)
        lista_articulos['ventas_producto'].append(ventas)
        lista_articulos['rating'].append(rating)
        lista_articulos['cantidad_opiniones'].append(cantidad_opiniones)
        lista_articulos['categoria'].append(categoria)
        lista_articulos['url_producto'].append(url_producto)
        lista_articulos['busqueda'].append(unidecode(buscar.lower()))

    #--------- Se transforman los datos númericos

    tabla_final = pd.DataFrame(lista_articulos)
    tabla_final['precio_actual'] = tabla_final['precio_actual'].astype('int32')
    tabla_final['precio_antes'] = tabla_final['precio_antes'].astype('int32')
    tabla_final['cantidad_opiniones'] = tabla_final['cantidad_opiniones'].astype('int32')
    tabla_final['rating'] = tabla_final['rating'].astype('float32')
    tabla_final['ventas_producto'] = tabla_final['ventas_producto'].astype('int32')

    #--------- Estadística básica

    datos_estadisticos = {
        "1.Ventas" : {"Promedio": round(tabla_final['ventas_producto'].mean(), 2),"Maximo": tabla_final['ventas_producto'].max(),"Minimo": tabla_final['ventas_producto'].min()}
        ,"2.Opiniones": {"Promedio": round(tabla_final['cantidad_opiniones'].mean(), 2),"Maximo": tabla_final['cantidad_opiniones'].max(),"Minimo": tabla_final['cantidad_opiniones'].min()}
        ,"3.Precio": {"Promedio": round(tabla_final['precio_actual'].mean(), 2),"Maximo": tabla_final['precio_actual'].max(),"Minimo": tabla_final['precio_actual'].min()}
        ,"4.Saturacion" : saturacion
        ,"5.Paginas": cant_pctos
        ,"6.Productos": cant_pctos* 50}

    tabla_html = tabla_final.to_html(classes = "table table-bordered", index=False)

    return render_template("resultado.html", resultado = tabla_html, estadistica = json.dumps(datos_estadisticos, indent = 4))
