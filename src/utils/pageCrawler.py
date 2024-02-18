from bs4 import BeautifulSoup
import urllib.request
import ssl
import re
import pickle as pkl

query = '/pt/pesquisa/buscador/?q2=%28assuntos%3A%22Bases+de+dados+cient%C3%ADficos%22%29+OR+%28*%3A*%29&selected_facets=area_pt%3ACi%C3%AAncias+Exatas+e+da+Terra%7CCi%C3%AAncia+da+Computa%C3%A7%C3%A3o'
page_num = 1
results = []
filter_tag = "plataforma_orcid"
num_of_results = float("inf")
reset = False

def extract_from_str(item):
    item = str(item)
    item = re.findall(r'\(([^)]*)\)', item)[0]
    item = item.split(' ')[0]
    item = item.replace(",", "").replace("'", "")
    return item

while len(results) < num_of_results:
    try:
        context = ssl._create_unverified_context()
        wp = urllib.request.urlopen("https://bv.fapesp.br" + query + f"&page={str(page_num)}", context=context, timeout=10)
        page = wp.read()
        soup = BeautifulSoup(page, features="html.parser")
        if page_num == 1:
            filter = soup.find_all('div', {'class':'w25 content'})[0]
            p = re.compile(r'<.*?>')
            num_of_results = int(p.sub('', str(filter)).replace(".", "").replace(" resultado(s)", ""))

        filter = soup.find_all('a', {'class':filter_tag})
        results_page = [extract_from_str(item) for item in filter]
        if len(results_page) == 0:
            break

        results.extend(results_page)
        summary = f"""
        Page Number: {page_num}
        Results gathered: {len(results_page)}
        Results total %: {int(100 * len(results) / num_of_results)}
        """
        print(f"{summary}\r", end='')
        page_num += 1
        reset = False
    except TimeoutError as e:
        continue
    except urllib.error.URLError as e:
        print("URL Error trying again")
        continue
    except KeyboardInterrupt:
        if reset:
            break
        else:
            reset = True
            print("Interrupt again to stop")
            continue


pkl.dump(results, open(f"output_{filter_tag}.pkl", "wb"))




