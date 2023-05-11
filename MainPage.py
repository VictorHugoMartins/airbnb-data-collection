from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Button
from bokeh.layouts import column
from bokeh.io import curdoc

class MainPage():
    def __init__(self):
        self.source = ColumnDataSource(data=dict(message=['Welcome to the main page!']))
        self.button = Button(label='Go to Graphs')
        self.button.on_click(self.go_to_graphs)
        self.layout = column(self.button)

    def go_to_graphs(self):
        curdoc().clear()
        graphs = GraphsPage()
        curdoc().add_root(graphs.layout)

main = MainPage()
curdoc().add_root(main.layout)