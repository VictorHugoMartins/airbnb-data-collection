import requests


response = requests.get('https://www.airbnb.com.br/users/show/1033769')
print(response.status_code)
print(response)
page = response.text
print(page)             