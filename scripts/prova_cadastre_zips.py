"""
Prova de la memoria cau dels ZIP del Catastro (dades/catastro.py, F51) en una carpeta de proves (EGRA_CACHE_PROVES):
els ZIP de l'usuari no es toquen.

  1. Descarrega tallada: es deixa a <zip>.part una part del fitxer (com si s'hagues tallat la xarxa); descarregar() la
     repren on era (HTTP Range) i el ZIP resultant es valid i igual (mateixa mida i contingut) que un de baixat sencer.
  2. <zip>.part malmes (bytes que no son del fitxer): el ZIP no es valid i es torna a baixar des de zero.
  3. Limit d'espai: netejar_zips esborra primer els que fa mes que no es fan servir i mai el protegit.
  4. Dues cel·les veines (Igualada) que comparteixen municipis: la segona no baixa cap ZIP que ja tingui la primera.
Necessita xarxa (un ZIP petit, el de Carme, ~0,2 MB, i els d'Igualada, ~6 MB).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_cadastre_zips.py <carpeta de proves>
"""
import hashlib
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    carpeta = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'proves_cadastre')
    os.environ['EGRA_CACHE_PROVES'] = carpeta
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    import requests
    from dades import catastro, llocs
    assert catastro.DIR_ZIPS.startswith(carpeta)
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text, flush=True)
        if not condicio:
            errors.append(text)

    def md5(cami):
        return hashlib.md5(open(cami, 'rb').read()).hexdigest()

    # municipi petit: Carme (al sud d'Igualada)
    mun = [m for m in catastro.municipis_a_prop(41.52, 41.54, 1.61, 1.63) if m[2] == 'CARME']
    prov, codi, nom, url = mun[0]
    cami = catastro.cami_zip(codi)
    for f in (cami, cami + '.part'):
        if os.path.exists(f):
            os.remove(f)

    # 1. tallada i represa
    sencer = catastro.descarregar(prov, codi, nom, url)
    mida, suma = os.path.getsize(sencer), md5(sencer)
    os.remove(sencer)
    with requests.get(url, stream=True, timeout=60) as r, open(cami + '.part', 'wb') as f:
        for tros in r.iter_content(65536):
            f.write(tros)
            if f.tell() >= mida // 3:
                break                               # la "xarxa" es talla a un terc
    tallat = os.path.getsize(cami + '.part')
    represa = catastro.descarregar(prov, codi, nom, url)
    ok(os.path.getsize(represa) == mida and md5(represa) == suma and not os.path.exists(cami + '.part'),
       f'descarrega tallada a {tallat / 1e3:.0f} de {mida / 1e3:.0f} kB: es repren i el ZIP es igual al sencer')
    ok(len(catastro.llegir_parts(represa, codi)) > 0, 'el ZIP repres es llegeix (parts d\'edifici)')

    # 2. .part malmes
    os.remove(represa)
    with open(cami + '.part', 'wb') as f:
        f.write(os.urandom(50_000))
    refet = catastro.descarregar(prov, codi, nom, url)
    ok(os.path.getsize(refet) == mida and md5(refet) == suma, '.part malmes: es torna a baixar sencer i es valid')

    # 3. limit d'espai (ZIP falsos, nomes per a la neteja)
    falsos = []
    for k in range(4):
        f = os.path.join(catastro.DIR_ZIPS, f'A.ES.SDGC.BU.9999{k}.zip')
        with open(f, 'wb') as g:
            g.write(b'0' * 400_000)
        os.utime(f, (time.time() - 1000 + k * 100, time.time() - 1000 + k * 100))
        falsos.append(f)
    os.utime(falsos[0], (time.time() - 5000, time.time() - 5000))     # el mes antic, pero protegit
    esborrats = catastro.netejar_zips(maxim_mb=1.2, protegits={falsos[0]})
    resten = sum(os.path.getsize(os.path.join(catastro.DIR_ZIPS, f)) for f in os.listdir(catastro.DIR_ZIPS)
                 if f.endswith('.zip'))
    ok(falsos[0] not in esborrats and esborrats and resten <= 1.2e6 and
       all(os.path.getmtime(e) if os.path.exists(e) else True for e in esborrats),
       f'limit d\'1,2 MB: esborrats {[os.path.basename(e)[-9:] for e in esborrats]}, en queden {resten / 1e6:.2f} MB, '
       'el protegit es conserva')
    for f in falsos:
        if os.path.exists(f):
            os.remove(f)

    # 4. cel·les veines d'Igualada
    c1, c2 = llocs.clau_latlon(41.5786, 1.6172), llocs.clau_latlon(41.5786, 1.6532)
    t = time.time()
    llocs.preparar_cadastre(c1, avis=lambda s: None)
    t1 = time.time() - t
    abans = {f: os.path.getmtime(os.path.join(catastro.DIR_ZIPS, f)) for f in os.listdir(catastro.DIR_ZIPS)
             if f.endswith('.zip')}
    mides = {f: os.path.getsize(os.path.join(catastro.DIR_ZIPS, f)) for f in abans}
    t = time.time()
    llocs.preparar_cadastre(c2, avis=lambda s: None)
    t2 = time.time() - t
    m1 = set(llocs.meta(c1)['cadastre']['municipis'])
    m2 = set(llocs.meta(c2)['cadastre']['municipis'])
    nous = [f for f in os.listdir(catastro.DIR_ZIPS) if f.endswith('.zip') and f not in abans]
    ok(m1 & m2 and len(nous) == len(m2 - m1) and all(os.path.getsize(os.path.join(catastro.DIR_ZIPS, f)) == mides[f]
                                                      for f in abans),
       f'cel·les veines: comparteixen {sorted(m1 & m2)}; la segona nomes baixa {len(nous)} ZIP '
       f'({sorted(m2 - m1)}); {t1:.1f} s la primera, {t2:.1f} s la segona')
    print(f'\n{"Tot correcte" if not errors else f"{len(errors)} errors"}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
