from bokeh.embed import server_document
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def page1():
    script = server_document('http://localhost:5006/dashboard')
    return render_template('page.html', script=script)

@app.route('/login')
def page2():
    script = server_document('http://localhost:5006/login')
    print(script)
    return render_template('page.html', script=script)

if __name__ == '__main__':
    app.run(port=5000)