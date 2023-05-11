from bokeh.models import ColumnDataSource, CustomJS
from bokeh.layouts import column, row
from bokeh.models.widgets import TextInput, PasswordInput, Button
from bokeh.io import curdoc, show
from graphsPage import GraphsPage

source = ColumnDataSource(data=dict(username=[], password=[]))
username_input = TextInput(value="", title="Login:")
password_input = PasswordInput(value="", title="Senha:")

curd = curdoc()
layout = None

def login():
		username = username_input.value
		password = password_input.value

		print(username_input.value, password_input.value)
		if (( username_input.value == "adm" ) and (password_input.value == "123")):
			print(True)
		else:
			print(False)
			lay = column(row(button))
			curd.add_root(lay)
			show(lay)
		# Aqui você pode adicionar a lógica de autenticação
		# Se a autenticação for bem-sucedida, redirecione o usuário para a próxima página
		# Caso contrário, exiba um erro na interface gráfica



button = Button(label="Login", button_type="success")
button.on_click(login)


curd.add_root(column(
										row(username_input),
										row(password_input),
										row(button)
									) if (layout is None) else layout)
show(curd.roots[0])