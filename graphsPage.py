from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJS
from bokeh.layouts import column, row
from bokeh.models.widgets import TextInput, PasswordInput, Button
from bokeh.io import curdoc

class GraphsPage():
    def __init__(self):
        self.plot = figure(width=400, height=400)
        self.plot.line([1,2,3,4,5], [2,5,4,6,7])
        self.button = Button(label='Go to Settings')
        self.button.on_click(self.go_to_settings)
        self.layout = column(self.plot, self.button)

    def go_to_settings(self):
        curdoc().clear()
        settings = SettingsPage()
        curdoc().add_root(settings.layout)