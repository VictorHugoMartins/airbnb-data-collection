from django.shortcuts import render
from django.http import HttpResponse

from .models import Greeting

import requests

# Create your views here.
def index(request):
    r = requests.get('http://httpbin.org/status/418')
    print(r.text)
    return HttpResponse('<pre>' + r.text + '</pre>')


def db(request):

    greeting = Greeting()
    greeting.save()

    greetings = Greeting.objects.all()

    return render(request, "db.html", {"greetings": greetings})

def teste(request):
	return '''
		<html>
			<body>
				
				<p>Preencha os campos:</p>
				<form method="post" action=".">
					<p>Área de pesquisa: <input name="area" /></p>
					<p>Site para pesquisa: <input name="site" /></p>
					<p>Pesquisa por ruas: <input name="buscaIsolada" /> (disponível apenas para Airbnb)</p>
					<p>Data de entrada: <input name="inicioEstadia" /> (disponível apenas para Booking)</p>
					<p>Data de saída: <input name="fimEstadia" /> (disponível apenas para Booking)</p>
					<p>Pesquisar comentários? <input name="comentarios" /></p>
					<p><input type="submit" value="Iniciar pesquisa!" /></p>
				</form>
				 <iframe width="100%" height="100%" src="https://enigmatic-tundra-07687.herokuapp.com/" title="W3Schools Free Online Web Tutorials"></iframe> 
			</body>
		</html>
	'''