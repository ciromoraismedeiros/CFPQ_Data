import lzma
import tarfile
import os
import subprocess
import shutil
import urllib.request
import requests

from contextlib import closing

GT_GRAPH_URL = 'http://www.cse.psu.edu/~kxm85/software/GTgraph/GTgraph.tar.gz'
GT_GRAPH_ARCH = 'GTgraph.tar.gz'

MEMORY_ALIASES_DOWNLOAD_ID = '1fVMY1rE7vX-bFWdP3CDTdjILDsELOXK0'
RDF_DOWNLOAD_ID = '1ahY5P4UkJ9Fpg9EN6iT2_GQNsztTI2K3'

SAPRSE_GRAPH_TO_GEN = [[5000, 0.001], [10000, 0.001], [10000, 0.01], [10000, 0.1], [20000, 0.001], [40000, 0.001], [80000, 0.001]]
FULL_GRAPH_TO_GEN = [10, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 25000, 50000, 80000]
NUMBER_OF_WORST_CASES = 12


RDF = 'RDF'
MEMORY_ALIASES = 'MemoryAliases'
DATA_ROOT_DIR = './data/graphs/'
MATRICES_DIR = 'Matrices'
DATA_TO_UNPACK = [[MEMORY_ALIASES,MEMORY_ALIASES_DOWNLOAD_ID], [RDF,RDF_DOWNLOAD_ID]]
GT_GRAPH = './GTgraph/random/GTgraph-random'
TMP_FILE = 'tmp.txt'

def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)    

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

def download_data():
    print('Downloading from GDrive is tarted.')
    for f in DATA_TO_UNPACK:         
        dst = os.path.join(os.path.join(DATA_ROOT_DIR,f[0]),os.path.join(MATRICES_DIR + '.tar.xz'))
        print('Download archive to ' + dst)
        download_file_from_google_drive(f[1], dst)  
    print('Downloading from GDrive is finised.')
    

def unpack(file_from, path_to):
    with lzma.open(file_from) as f:
        with tarfile.open(fileobj=f) as tar:
            content = tar.extractall(path_to)

def install_gtgraph():
    print('Installation of GTgraph is started.')
    with urllib.request.urlopen(GT_GRAPH_URL) as response, open(GT_GRAPH_ARCH, 'wb') as out_file:
       shutil.copyfileobj(response, out_file)
    print('GTgraph is downloaded.')
    tar = tarfile.open(GT_GRAPH_ARCH)
    tar.extractall()
    tar.close()

    subprocess.run(['sed', '-i', 's/CC = icc/#CC = icc/g', './GTgraph/Makefile.var'])
    subprocess.run(['sed', '-i', 's/#CC = gcc/CC = gcc/g', './GTgraph/Makefile.var'])
    subprocess.run(['make', '-C', './GTgraph']) 
    print('Installation of GTgraph is finished.') 

def unpack_graphs():
    for d in DATA_TO_UNPACK:
        to = os.path.join(DATA_ROOT_DIR, d[0])
        arch = os.path.join(to, '%s.tar.xz'%(MATRICES_DIR))
        print ('Unpack ', arch, ' to ', to)
        unpack(arch, to)

def to_file(filepath, graph):
    with open(filepath, 'w') as out_file:
        for t in graph:
            s = t[0]
            p = t[1]
            o = t[2]
            out_file.write('%s %s %s\n'%(s,p,o))

def gen_sparse_graph(target_dir, vertices, prob, add_back_edge):
 
    subprocess.run([GT_GRAPH, '-t', '0', '-n', '%s'%(vertices), '-p', '%s'%(prob), '-o', TMP_FILE])
    
    with open(os.path.join(target_dir, 'G%sk-%s.txt'%(int(vertices/1000), prob)), 'a') as out_file:
        with open(TMP_FILE) as in_file:
            for l in in_file.readlines():
                if l.startswith('a '):
                   a = l.split(' ')
                   if (add_back_edge):
                      out_file.write('%s A %s\n'%(a[1], a[2]))
                      out_file.write('%s AR %s\n'%(a[2], a[1]))
                   else: 
                      lbl = 'A' if int(a[3]) % 2 == 0 else 'AR'
                      out_file.write('%s %s %s\n'%(a[1], lbl, a[2]))
    os.remove(TMP_FILE)

def gen_worst_case_graph(target_dir, vertices):
    first_cycle = int(vertices / 2) + 1
    second_cycle = int(vertices / 2) - 1
    
    with open(os.path.join(target_dir, 'worstcase_%s.txt'%(vertices)), 'a') as out_file:
        for i in range(0, first_cycle - 1):
            out_file.write('%s A %s \n'%(i, i + 1))
        out_file.write('%s A %s \n'%(first_cycle - 1, 0))
        
        out_file.write('%s B %s \n'%(first_cycle - 1, first_cycle))      

        for i in range(first_cycle, vertices - 1):
            out_file.write('%s B %s \n'%(i, i + 1))
        out_file.write('%s B %s \n'%(vertices - 1, first_cycle - 1))

def gen_cycle_graph(target_dir, vertices):
    with open(os.path.join(target_dir, 'fullgraph_%s.txt'%(vertices)), 'a') as out_file:
        for i in range(0, vertices - 1):
            out_file.write('%s A %s \n'%(i, i + 1))
        out_file.write('%s A %s \n'%(vertices - 1, 0))   

def clean_dir(path):
   if os.path.isdir(path): 
      shutil.rmtree(path)
   os.mkdir(path)

def generate_all_sparse_graphs():
   print('Sparse graphs generation is started.') 
   matrices_dir = os.path.join(os.path.join(DATA_ROOT_DIR, 'SG_1'), MATRICES_DIR)
   clean_dir(matrices_dir)

   for g in SAPRSE_GRAPH_TO_GEN: gen_sparse_graph(matrices_dir, g[0], g[1], True)

   matrices_dir = os.path.join(os.path.join(DATA_ROOT_DIR, 'SG_2'), MATRICES_DIR)
   clean_dir(matrices_dir)

   for g in SAPRSE_GRAPH_TO_GEN: gen_sparse_graph(matrices_dir, g[0], g[1], False)
   print('Sparse graphs generation is finished.')


def generate_full_graphs():
   print('Full graphs generation is started.')
   matrices_dir = os.path.join(os.path.join(DATA_ROOT_DIR, 'FullGraph'), MATRICES_DIR)
   clean_dir(matrices_dir)
   
   for g in FULL_GRAPH_TO_GEN: gen_cycle_graph(matrices_dir, g)
   print('Full graphs generation is finished.')

def generate_worst_case_graphs():
   print('Worst case graphs generation is started.')
   matrices_dir = os.path.join(os.path.join(DATA_ROOT_DIR, 'WorstCase'), MATRICES_DIR)
   clean_dir(matrices_dir)
   
   for n in range(2, NUMBER_OF_WORST_CASES): gen_worst_case_graph(matrices_dir, 2 ** n)
   print('Worst case graphs generation is finished.')

def gen_sierpinski_graph(target_dir, degree, predicates=['A']):
    """ Generates a Sierpinski Triangle graph. """
    
    def sierpinski(t, l, r, deg, preds, g):
        ''' Core function for generating the Sierpinski Triangle. '''
        if deg > 0:
            lt = next(ids)
            tr = next(ids)
            rl = next(ids)
            sierpinski(l,  lt, rl, deg-1, preds, g)
            sierpinski(lt, t,  tr, deg-1, preds, g)
            sierpinski(rl, tr, r,  deg-1, preds, g)
        else:
            add_edges(l,t,preds,g)
            add_edges(t,r,preds,g)
            add_edges(r,l,preds,g)
            
    def add_edges(u,v,preds,g):
        ''' Adds edges between vertices u and v for all predicates. '''
        for p in preds:
            g += [[u,p,v]]
            g += [[v,p,u]]
            
    def _idgen():
        ''' Generates integer identifiers for vertices. '''
        c = 4
        while True:
            yield c
            c += 1
            
    ids = _idgen()
    graph = []
    sierpinski(1,2,3,degree,predicates, graph)   
    with open(os.path.join(target_dir, 'sierpinskigraph_%s.txt'%(degree)), 'w') as out_file:
        for triple in graph:
            out_file.write('%s %s %s \n'%(triple[0], triple[1], triple[2]))

if __name__ == '__main__':
   install_gtgraph()
   download_data()
   unpack_graphs()
   generate_all_sparse_graphs()
   generate_full_graphs()
   generate_worst_case_graphs()
