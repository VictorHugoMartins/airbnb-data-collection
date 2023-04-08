from Proxy_List_Scrapper import Scrapper

def getProxies(verbose=False):
  scrapper = Scrapper(category='NEW', print_err_trace=False)

  # Get ALL Proxies According to your Choice
  data = scrapper.getProxies()

  formattedProxies = []
  for item in data.proxies:
      formattedProxies.append('{}:{}'.format(item.ip, item.port))
  return formattedProxies