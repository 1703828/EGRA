"""
Equivalencies, per als scripts de prova escrits abans de la F48, entre l'API antiga de la camera (dues vistes: des
dels ulls de l'observador i d'exploracio, tecla V) i la vista unica actual (main.py). No es una capa del programa:
cada funcio fa exactament el que fa ara el programa quan l'usuari ho demana.
  - abans canviar_vista(1) (vista des dels ulls)  -> als_ulls(app): app.posar_als_ulls() (doble clic, sense girar)
  - abans camera_observador.mirar(rumb, incl)     -> app.camera.orientar(rumb, incl)
  - abans canviar_vista(0) (exploracio)            -> lliure(app): la mateixa camera deixa de seguir els ulls
  - abans app.vista == 1                           -> app.camera_als_ulls()
  - abans veure_ombra_des_de_lespai()             -> veure_ombra_des_de_lespai(app): tecla G (anada)
"""


def als_ulls(app, rumb=None, inclinacio=None):
    """La camera als ulls. Com feia la vista des dels ulls, si despres el script canvia el punt (triar_punt), la camera
    hi torna (l'usuari ho fa amb el doble clic, app.anar_al_punt, que tria el punt i posa la camera als ulls)."""
    _seguir_el_punt(app)
    app._script_als_ulls = True
    app.camera.aturar_moviment()
    app.posar_als_ulls()
    if rumb is not None:
        app.camera.orientar(rumb, inclinacio)


def lliure(app):
    """La camera ja no segueix els ulls (com quan l'usuari la mou): el script la pot posar on vulgui."""
    app._script_als_ulls = False
    app.camera.aturar_moviment()
    app.ulls_fixats = None


def _seguir_el_punt(app):
    if getattr(app, '_triar_original', None) is not None:
        return
    app._triar_original = original = app.triar_punt

    def triar_punt(*args, **kw):
        r = original(*args, **kw)
        if r and getattr(app, '_script_als_ulls', False):
            app.posar_als_ulls()
        return r
    app.triar_punt = triar_punt


def veure_ombra_des_de_lespai(app):
    """Abans, el boto 'Ombra de la Lluna des de l'espai'; ara la tecla G (app.commutar_espai), sempre l'anada."""
    app.abans_espai = None
    app.commutar_espai()


def sobre_el_punt(app):
    """Abans posar_exploracio_sobre_el_punt: la camera a 6 km del punt d'observacio, d'esquena al Sol, 3 km amunt i
    mirant cap al punt (una posicio de partida dels scripts; ara l'usuari hi arriba movent la camera)."""
    from basecode.camera_exploracio import direccio_mirada
    from dades import geodesia
    lliure(app)
    o = app.observador
    az, _ = app.model.sol(app.hora)
    darrere = direccio_mirada(o.lat, o.lon, az + 180.0, 0.0)
    _, _, amunt = geodesia.base_local(o.lat, o.lon)
    app.camera.posicio = app.ulls() + 6.0 * darrere + 3.0 * amunt
    app.camera.orientar(az, -25.0)
