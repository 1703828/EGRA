"""
Feines en segon pla (sense OpenGL): una funcio que s'executa en un fil mentre el bucle de dibuix continua.

El fil principal consulta estat (text per al panell), fet, resultat i error. La funcio rep avis(text) per anar
explicant que fa. Els objectes OpenGL no es creen mai aqui: quan la feina acaba, el fil principal en fa servir el
resultat (p. ex. puja les textures). Es el mateix esquema que dades/llocs.Preparacio i dades/visibilitat.Calcul.

FeinaProces fa el mateix en un altre proces: per a les feines que passen molta estona dins de biblioteques que no
deixen anar el bloqueig global de Python (GIL) mentre treballen (llegir el GML del Catastro amb GDAL, rasteritzar, fer
la malla dels edificis). En un fil, aturaven el dibuix: llegir el Catastro de Valencia (36 MB comprimits) el va
deixar sense fotogrames 5 minuts. En un proces, el dibuix no s'atura mai. La funcio ha de ser d'un modul (no una
lambda) i el resultat, petit: el proces deixa les dades al disc i el fil principal (o una Feina) les llegeix.

clau identifica que s'ha demanat (p. ex. el lloc i l'etapa): quan acaba, qui la va demanar comprova si encara es
el que cal abans de fer-la servir (una descarrega antiga no ha de canviar el que es veu despres de moure's).
"""
import multiprocessing
import threading
import time


class Feina:
    def __init__(self, clau, funcio, *args, descripcio=''):
        self.clau, self.descripcio = clau, descripcio
        self.estat, self.fet, self.resultat, self.error = 'Comencant...', False, None, None
        self.t0 = time.time()
        self.fil = threading.Thread(target=self._executar, args=(funcio, args), daemon=True)
        self.fil.start()

    def _executar(self, funcio, args):
        try:
            self.resultat = funcio(*args, self.avis)
        except Exception as e:   # noqa: BLE001 (xarxa, servei o dades: es mostra al panell)
            self.error = f'{e.__class__.__name__}: {e}'
            print(f'AVIS: {self.descripcio or self.clau}: {self.error}')
        self.fet = True

    def avis(self, text):
        self.estat = text

    def segons(self):
        return time.time() - self.t0


def _proces(cua, funcio, args):
    """Cos del proces fill: els avisos i el resultat (o l'error) tornen per la cua."""
    try:
        r = funcio(*args, lambda text: cua.put(('estat', text)))
        cua.put(('fet', r))
    except Exception as e:   # noqa: BLE001
        cua.put(('error', f'{e.__class__.__name__}: {e}'))


class FeinaProces(Feina):
    """Com Feina, pero la funcio s'executa en un proces nou (spawn: no comparteix res amb el programa). Un fil del
    programa n'escolta els avisos i el resultat."""

    def _executar(self, funcio, args):
        ctx = multiprocessing.get_context('spawn')
        cua = ctx.Queue()
        p = ctx.Process(target=_proces, args=(cua, funcio, args), daemon=True)
        try:
            p.start()
        except Exception as e:   # noqa: BLE001 (sense proces no hi ha feina: es diu al panell)
            self.error = f'no s\'ha pogut engegar el proces: {e.__class__.__name__}: {e}'
            print(f'AVIS: {self.descripcio or self.clau}: {self.error}')
            self.fet = True
            return
        while True:
            try:
                tipus, valor = cua.get(timeout=1.0)
            except Exception:   # noqa: BLE001 (cua buida: el proces potser ha mort)
                if not p.is_alive():
                    self.error = self.error or f'el proces ha acabat sense resultat (codi {p.exitcode})'
                    break
                continue
            if tipus == 'estat':
                self.estat = valor
            elif tipus == 'fet':
                self.resultat = valor
                break
            else:
                self.error = valor
                print(f'AVIS: {self.descripcio or self.clau}: {self.error}')
                break
        p.join(timeout=5)
        self.fet = True
