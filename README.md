# airbnb-data-collection

  A presente pesquisa foi realizada a partir de uma ferramenta de web-scrapping previamente desenvolvida por Tom Slee. A partir da mesma, foram inseridas novas funcionalidades com o objetivo de adaptar o trabalho original para o contexto da cidade de Ouro Preto, MG, Brasil, onde também foi realizado o scrapping de anúncios disponíveis no Booking (site de hospedagem tradicional) e a preparação e clusterização dos dados por meio do algoritmo KModes.
  
  Breve descrição dos arquivos: (EM DESENVOLVIMENTO)

airbnb.py:

  Funções referentes ao scrapping dos anúncios disponíveis no Airbnb usando requests. Para mais informações, visite: https://github.com/tomslee/airbnb-data-collection

booking.py:

  Equivalente ao airbnb.py, referente ao scrapping dos anúncios disponíveis no Booking usando selenium.

data_analysis.py:

  Preparação dos dados usando o método kmodes de clusterização e plotação de gráficos para análise.

clustering_quality.py:

  A partir dos dados passados, determina a quantidade ideal de clusters distintos para os dados. Para mais informação sobre o KModes, acesse: https://github.com/nicodv/kmodes

airbnb_geocoding.py:

  Uso da API do Google para determinar a localização espacial de um determinado anúncio dada as suas coordenadas.

export_spreadsheet.py:

  Exporta os dados presentes no banco de dados do PostgreSQL para planilhas em formato xlsx.

create_map.py:

  Cria uma mapa a partir das coordenadas dos anúncios coletados e os divide usando como parâmetro o site de origem (Airbnb ou Booking)
