# airbnb-data-collection

A presente pesquisa foi realizada a partir de uma ferramenta de web-scrapping previamente desenvolvida por Tom Slee. A partir da mesma, foram inseridas novas funcionalidades com o objetivo de adaptar o trabalho original para o contexto da cidade de Ouro Preto, MG, Brasil, onde também foi realizado o scrapping de anúncios disponíveis no Booking (site de hospedagem tradicional) e a preparação e clusterização dos dados por meio do algoritmo KModes. Além disso, também foi disponibilizada uma plataforma online onde podem ser visualizados os resultados encontrados.

## Alguns conceitos importantes
### Web scrapping

É uma técnica de raspagem web utilizada para coletar dados presentes sobre a superfície de uma aplicação. Neste caso, foram usadas predominantemente as bibliotecas requests e selenium ara obter os dados referentes aos anúncios do Airbnb e do Booking. Para saber mais sobre estas bibliotecas, clique sobre o respectivo nome.
Clusterização

### Clusterização

É uma técnica usada para agrupar dados em grupos distintos, sendo que os elementos de cada grupo possuem características em comum entre si e possuem alto nível de similaridade. No escopo deste projeto, foi aplicado o método K-Modes (clique no nome para saber mais) de clusterização para dados mistos, ou seja, tanto categóricos quanto numéricos

## Plataforma online para visualização de dados

### Como usar a plataforma

O site foi desenvolvido com o intuito de expor os dados que foram coletados pela pesquisa. A seguir, é melhor o funcionamento dos seus componentes (os filtros, o mapa, os gráficos e a tabela).


#### Os gráficos: o que exibem?

**O mapa:** No mapa estão exibidos os anúncios de forma geográfica. Aqui, é possível passar o mouse por determinados anúncios para observar algumas de suas características específicas, tais como o nome, preço per capita e classificação média.

**O gráfico de barras:** São exibidos alguns dados de interesse de acordo com os filtros de coluna categórica e coluna numérica de interesse, sendo agrupados os dados tanto por essas categorias quanto, também, pelo site (Airbnb, Booking, ou a soma de ambos).

**O gráfico de correlação:** Nesse gráfico, está exposta a relação da variável preço com as demais características que foram coletados. Um valor próximo de 1 indica uma relação proporcional, onde ambos crescem juntos, um valor próximo de -1 indica um decréscimo no preço a medida que a outra coluna cresce e um valor próximo de 0 indica uma relação fraca. Passe o mouse pelos campos para observar os números absolutos por si só.

**A tabela:** Na tabela estão presentes todos os anúncios que são visualizados no mapa.

**Importante!** A todo momento, a visualização no mapa, nos gráficos e no mapa estão sujeitos aos filtros. Logo, os anúncios que foram excluídos pelos filtros de site, região, tipo de quarto e categoria também estão fora dos cálculos de quantidade e correlação. Para fins de exemplificação, se apenas os anúncios de quartos compartilhados estiverem sendo exibidos, apenas a correlação deles será calculada e apenas eles serão agrupados no gráfico de barras... Ainda, se, nesse caso, for escolhida como coluna categórica para visualização o tipo de quarto, as categorias diferentes de quarto compartilhados estarão todas com valor igual a 0. Se o filtro de região não for selecionado, serão exibidos todos os anúncios, sem excluir os diferentes.

#### Os filtros: o que significam?

**Cidade visualizada:** Indica a cidade cujos dados estão sendo visualizados no momento no mapa e cujos dados estão sendo levados em consideração para a construção dos demais gráficos.

**Quantidade k de clusters para clusterização:** Um cluster é um aglomerado cujos dados presentes ali possuem características semelhantes entre si. No contexto dessa pesquisa, os clusters são grupos de anúncios que possuem certa similaridade em relação ao preço, classificação média, categoria, tipo de quarto, região e etc. A quantidade k de clusters para clusterização se refere, então, a quantidade de grupos distintos que serão gerados para análise, sendo possível visualizar todos ao mesmo tempo, ou então visualizar apenas um deles por vez com o cluster de filtro visualizado.

**Site para clusterização:** É o site (Airbnb ou Booking) que está sendo considerado para geração dos aglomerados. Por padrão, são usados os anúncios tanto do Airbnb quanto do Booking, mas é possível ignorar uma dessas plataformas da equação.

**Cluster visualizado:** (EM REVISÃO) Indica o aglomerado específico que está sendo visualizado no momento, de forma a excluir momentaneamente da visualização os demais clusters gerados. Caso o valor de cluster escolhido aqui seja maior que o total de clusters escolhido, nada será exibido.

**Site visualizado:**  É o site (Airbnb ou Booking) que está sendo visualizado no momento. Por padrão, são usados os anúncios tanto do Airbnb quanto do Booking, mas é possível ignorar uma dessas plataformas da equação. Caso o site escolhido aqui não esteja incluso no site para clusterização, nada será exibido.

**Coluna categórica e coluna numérica para visualização no gráfico:** Responsáveis pela visualização no gráfico de barras logo abaixo do mapa, a coluna categórica indica a coluna usada para agrupamento no eixo x. A coluna numérica indica os valores do eixo y.

**Região (no momento, disponível apenas para Ouro Preto):** Filtra os anúncios que estão sendo visualizados de acordo com a sua região, exibindo os anúncios cujo campo possui o valor indicado. Por padrão, todos os anúncios estão sendo exibidos.

**Tipo de quarto:** Filtra os anúncios que estão sendo visualizados de acordo com o tipo de quarto, exibindo os anúncios cujo campo possui o valor indicado. Por padrão, todos os anúncios estão sendo exibidos.

**Categoria:** Filtra os anúncios que estão sendo visualizados de acordo com a sua categoria, exibindo os anúncios cujo campo possui o valor indicado. Por padrão, todos os anúncios estão sendo exibidos.

**Price per capita mínimo:** Filtra os anúncios que estão sendo visualizados de acordo com um preço per capita mínimo (calculado dividindo o preço total pela quantidade máxima de visitantes que o quarto acomoda), ou seja, são exibidos os anúncios cujo preço per capita é maior do que o indicado. Por padrão, todos os anúncios estão sendo exibidos.

**Consulta**: Esse campo é usado para a aplicação de filtros mais específicos além dos que foram descritos anteriormente. Com esse campo, é possível, por exemplo, selecionar os anúncios cujo determinado campo possui determinado valor. Por exemplo, selecionar os quartos do Airbnb que possuem determinado anfitrião (identificado por um número encontrado no site de origem). A seguir, é mais detalhado como preencher este campo de consulta:

#### Como escrever?

Para consultar os valores por comodidade, digite: 'valor == 1'. Por exemplo, 'academia == 1'

Para consultar os anúncios que ocorrem em Repúblicas, digite 'republica == 1'

Para consultar os valores por região, tipo de quarto ou tipo de propriedade,
digite "region == 'valor'", 'room_type == valor' ou 'property_type == "valor"'. Por exemplo, 'region == "Centro"'.
A mesma lógica se aplica aos nomes do quarto, o site de onde os anúncios foram coletados e sua categoria.

Para valores numéricos (room, host ou hotel id, cluster, price_pc, overall_satisfaction, contagem de anúncios por host ou por hotel),
use 'coluna == valor'. Por exemplo, 'overall_satisfaction == 5'. Operadores >, <, >=, <= também são aplicáveis.

Para aplicar mais de um filtro, use 'filtro1 & filtro2'.
Nesse caso, serão retornados anúncios que atendam à todos os filtros simultaneamente.
Por exemplo, 'site == 'Airbnb' & region == "Centro"' ou 'site == 'Airbnb' & region == "Centro"' & price_pc < 20'.

Para encontrar anúncios que atendam à um filtro ou outro, use o operador '|'.
Por exemplo, 'room_type == "Hotel room" | property_type == 'Hotel'".

Quais valores usar ao escrever uma consulta?

Para região, os possíveis valores são: 'Centro', 'Distrito' e 'Entorno'. Até o momento, essa divisão está disponível apenas para a cidade de Ouro Preto.

## Algumas bibliotecas de interesse

### Pandas: usada para tratar os dados coletados como se eles estivessem em uma tabela

### Bokeh: usada para o desenvolvimento da interface da plataforma

Acesse também a página do Tom Slee, grande contribuidor, ainda que indireto, desse projeto, no GitHub

## Breve descrição dos arquivos no GitHub: (EM DESENVOLVIMENTO)

### airbnb.py:

  Funções referentes ao scrapping dos anúncios disponíveis no Airbnb usando requests. Para mais informações, visite: https://github.com/tomslee/airbnb-data-collection

### booking.py:

  Equivalente ao airbnb.py, referente ao scrapping dos anúncios disponíveis no Booking usando selenium.

### data_analysis.py:

  Preparação dos dados usando o método kmodes de clusterização e plotação de gráficos para análise.

### clustering_quality.py:

  A partir dos dados passados, determina a quantidade ideal de clusters distintos para os dados. Para mais informação sobre o KModes, acesse: https://github.com/nicodv/kmodes

### airbnb_geocoding.py:

  Uso da API do Google para determinar a localização espacial de um determinado anúncio dada as suas coordenadas.

### export_spreadsheet.py:

  Exporta os dados presentes no banco de dados do PostgreSQL para planilhas em formato xlsx.

### create_map.py:

  Cria uma mapa a partir das coordenadas dos anúncios coletados e os divide usando como parâmetro o site de origem (Airbnb ou Booking)


## Informações legais

Todos os dados contidos aqui estiveram, em algum momento, disponíveis publicamente no Airbnb ou no Booking e não é intuito desse trabalho prejudicar a imagem destas as plataformas ou dos usuários das mesmas.