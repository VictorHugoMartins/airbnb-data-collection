class SettingsPage():
    def __init__(self):
        self.source = ColumnDataSource(data=dict(message=['Welcome to the settings page!']))
        self.button = Button(label='Go to Main')
        self.button.on_click(self.go_to_main)
        self.layout = column(self.button)

    def go_to_main(self):
        curdoc().clear()
        main = MainPage()
        curdoc().add_root(main.layout)