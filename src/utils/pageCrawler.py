from bs4 import BeautifulSoup
import urllib.request
import ssl
import re
import pickle as pkl
import argparse

parser = argparse.ArgumentParser(description='Query and format in structured object FAPESP projects, given a query obtained in https://bv.fapesp.br/pt/pesquisa/buscador/')

parser.add_argument('--query', dest='query', required=True,
                    help='query obtained from refining at fapesp website https://bv.fapesp.br/pt/pesquisa/buscador/')
parser.add_argument('--output_name', dest='output_name', required=True,
                    help='output file path for results')

args = parser.parse_args()

page_num = 1
results = list()
reset = False

def extract_orcid_from_str(item):
    item = str(item)
    item = re.findall(r'\(([^)]*)\)', item)[0]
    item = item.split(' ')[0]
    item = item.replace(",", "").replace("'", "")
    return item

CLEANR = re.compile('<.*?>')

# Get number of pages
try:
    context = ssl._create_unverified_context()
    wp = urllib.request.urlopen("https://bv.fapesp.br" + args.query + f"&page={str(page_num)}" + f"&count=50", context=context, timeout=10)
    page = wp.read()
    soup = BeautifulSoup(page, features="html.parser")
    filter = soup.find_all('div', {'class':'w25 content'})[1]
    p = re.compile(r'<.*?>')
    filter = p.sub('', str(filter)).rstrip().lstrip()
    if "Página 1 de " not in filter:
        raise Exception("Could not get the number of pages in the required format") 
    else:
        filter = filter.replace("Página 1 de ", "").replace(".", "")
    num_of_pages = int(filter)
except:
    print("Error processing the query")
    quit(0)

# Iterate through query
while page_num <= num_of_pages:
    try:
        context = ssl._create_unverified_context()
        wp = urllib.request.urlopen("https://bv.fapesp.br" + args.query + f"&page={str(page_num)}" + f"&count=50", context=context, timeout=10)
        page = wp.read()
        soup = BeautifulSoup(page, features="html.parser")
        filter = soup.find_all('div', {'class':'content resumo'})
        if page_num == 1:
            filter = soup.find_all('div', {'class':'w25 content'})[1]
            p = re.compile(r'<.*?>')
            filter = p.sub('', str(filter)).rstrip().lstrip().replace("Página 1 de ", "").replace(".", "")
            num_of_pages = int(filter)
        
        all_projects = str(soup).split("<div class=\"table_details\"><h2 class=\"no_float\">")[1:]
        all_projects[-1] = all_projects[-1].split("</p></span></div></div></section></div><script type=\"text/javascript\">")[0]

        results_page = []
        for proj in all_projects:
            proj_soup = BeautifulSoup(proj, "html.parser")
            proj_orcids = proj_soup.find_all('a', {'class':"plataforma_orcid"})

            proj_orcids = [extract_orcid_from_str(item) for item in proj_orcids]
            res_summary = proj_soup.find_all('span', {'itemprop': "text"})
            if len(res_summary) == 0:
                proj_summary = ""
            else:
                proj_summary = str(proj_soup.find_all('span', {'itemprop': "text"})[0])
                proj_summary = re.sub(CLEANR, '', str(proj_summary)).rstrip().lstrip()

            proj_title = proj_soup.find_all('a', {'itemprop':"name"})[0]
            proj_title = re.sub(CLEANR, '', str(proj_title)).rstrip().lstrip()

            proj_keywords = proj_soup.find_all('a', {'itemprop':"keywords"})
            proj_keywords = [re.sub(CLEANR, '', str(p)).rstrip().lstrip() for p in proj_keywords]
            results_page.append(
                {
                    "orcids": proj_orcids,
                    "title": proj_title,
                    "summary": proj_summary,
                    "keywords": proj_keywords,
                }
            )

        if len(results_page) == 0:
            break
        print(results_page)
        results.extend(results_page)
        summary = f"""
        Page Number (total: {num_of_pages}): {page_num}
        Pages total %: {int(100 * page_num / num_of_pages)}
        Results gathered: {len(results_page)}
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

pkl.dump(results, open(f"{args.output_name}.pkl", "wb"))




