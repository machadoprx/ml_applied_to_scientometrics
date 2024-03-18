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

import re

# Get number of pages
#print("https://bv.fapesp.br" + u"{}".format(str(args.query)) + f"&page={str(page_num)}" + "&count=50")
context = ssl._create_unverified_context()
query = "/pt/pesquisa/buscador/?q2=(assuntos%3ABases+de+dados+cient%C3%ADficos)+OR+(*%3A*)&selected_facets=area_pt%3ACi%C3%AAncias+Exatas+e+da+Terra|Ci%C3%AAncia+da+Computa%C3%A7%C3%A3o&selected_facets=area_pt%3ACi%C3%AAncias+Exatas+e+da+Terra|Ci%C3%AAncia+da+Computa%C3%A7%C3%A3o&selected_facets=publicacoes_cientificas_exact%3ASim"

try:
    context = ssl._create_unverified_context()
    wp = urllib.request.urlopen("https://bv.fapesp.br" + str(query) + f"&page={str(page_num)}" + "&count=50", context=context, timeout=10)
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
    
    context = ssl._create_unverified_context()

    try:
        wp = urllib.request.urlopen("https://bv.fapesp.br" + str(query) + f"&page={str(page_num)}" + f"&count=50", context=context, timeout=10)
        page = wp.read()
    except TimeoutError as e:
        print(f"Timeout when reading page {page_num}")
        continue
    except urllib.error.URLError as e:
        print("URL Error, trying again")
        continue

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

    k = 0
    while k < len(all_projects):
        proj = all_projects[k]
        proj_soup = BeautifulSoup(proj, "html.parser")
        proj_page = proj_soup.find_all('a', {'itemprop':"name"})[0]
        proj_page = re.findall('"([^"]*)"', str(proj_page))[0]

        try:
            proj_page = urllib.request.urlopen("https://bv.fapesp.br" + str(proj_page), context=context, timeout=5)
            proj_page = proj_page.read()
        except TimeoutError as e:
            print(f"Timeout when reading project {k} from page {page_num}")
            continue
        except urllib.error.URLError as e:
            print("URL Error, trying again")
            k += 1
            continue


        proj_page = BeautifulSoup(proj_page, features="html.parser")
        publication_pages = proj_page.find_all('a', {'itemprop':"name"})

        proj_dois = []
        pub_names = []
        dois_names_dic = {}
        i = 0
        while i < len(publication_pages):
            pub = publication_pages[i]
            pub = re.findall('"([^"]*)"', str(pub))[0]
        
            try:
                pub_page = urllib.request.urlopen("https://bv.fapesp.br" + str(pub), context=context, timeout=5)
                pub_page = pub_page.read()
            except TimeoutError as e:
                print(f"Timeout when reading pub {i} from project {k} from page {page_num}")
                continue
            except urllib.error.URLError as e:
                print("URL Error, trying again")
                i += 1
                continue

            pub_page = BeautifulSoup(pub_page, features="html.parser")

            pub_name = [l for l in pub_page.find_all('h1', {'class':"mini-title bv_h1"})][0]
            p = re.compile(r'<.*?>')
            pub_name = p.sub('', str(pub_name)).rstrip().lstrip()
            pub_names.append(pub_name)
            
            doi = [l for l in pub_page.find_all('a', {'class':"link-color"}) if "www.doi" in str(l)]
            
            if len(doi) > 0:
                doi = doi[0]
                doi = str(re.findall('"([^"]*)"', str(doi))[1])
                proj_dois.append(doi)
            dois_names_dic[pub_name] = doi
            i += 1

        proj_id = proj.split("<!-- PROCESSO -->")[1].split("<!-- LINHA DE FOMENTO -->")[0]
        proj_id = re.sub(CLEANR, '', str(proj_id)).rstrip().lstrip().replace("Processo:", "")
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
                "project_id": proj_id,
                "orcids": proj_orcids,
                "title": proj_title,
                "summary": proj_summary,
                "keywords": proj_keywords,
                "related_dois": proj_dois,
                "pubs_names": pub_names,
                "name_doi_relationship": dois_names_dic
            }
        )
        k += 1

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
    #reset = False

pkl.dump(results, open(f"{args.output_name}.pkl", "wb"))




