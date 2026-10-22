// Web de seguiment: estat i progrés calculats a partir dels criteris escrits a l'HTML.
// Cada criteri és un <li data-estat="validat|fet|pendent|no-compleix"> dins d'un subobjectiu.
// Progrés = criteris VALIDATS / total. Els FETS (comprovats per Claude, pendents de l'equip) es
// mostren a part a la barra, més suaus, i no compten com a progrés.

const NOMS = { validat: 'VALIDAT', fet: 'FET', pendent: 'PENDENT', 'no-compleix': 'NO COMPLEIX' };

function comptar(element) {
  const c = { total: 0, validat: 0, fet: 0, pendent: 0, 'no-compleix': 0 };
  element.querySelectorAll('ul.criteris li[data-estat]').forEach((li) => {
    c.total++;
    c[li.dataset.estat]++;
  });
  return c;
}

// estat d'un subobjectiu: VALIDAT si tots els criteris ho estan, PENDENT si cap no s'ha fet, si no EN CURS
function estat(c) {
  if (c.total && c.validat === c.total) return ['validat', 'VALIDAT'];
  if (c.validat + c.fet + c['no-compleix'] === 0) return ['pendent', 'PENDENT'];
  return ['en-curs', 'EN CURS'];
}

function barra(c) {
  const pct = (n) => (c.total ? (100 * n) / c.total : 0);
  return `<span class="progres" title="${c.validat} validats i ${c.fet} fets de ${c.total} criteris">
      <span class="barra"><span class="b-validat" style="width:${pct(c.validat)}%"></span>
      <span class="b-fet" style="width:${pct(c.fet)}%"></span></span>${c.validat}/${c.total} validats</span>`;
}

function obrirDesDeLaUrl() {
  const d = document.getElementById(location.hash.slice(1));
  if (d && d.tagName === 'DETAILS') d.open = true;
}

document.addEventListener('DOMContentLoaded', () => {
  // etiqueta a cada criteri (el text va dins d'un <span> perquè es mantingui en una columna)
  document.querySelectorAll('ul.criteris li[data-estat]').forEach((li) => {
    const e = li.dataset.estat;
    li.innerHTML = `<span class="etiqueta ${e}">${NOMS[e]}</span><span>${li.innerHTML}</span>`;
  });
  // capçalera de cada subobjectiu i la seva entrada a l'índex
  document.querySelectorAll('details.sub').forEach((d) => {
    const c = comptar(d);
    const [classe, nom] = estat(c);
    const html = `<span class="etiqueta ${classe}">${nom}</span>${barra(c)}`;
    d.querySelector('.cap').insertAdjacentHTML('beforeend', html);
    const entrada = document.querySelector(`nav.index a[href="#${d.id}"]`);
    if (entrada) entrada.insertAdjacentHTML('afterend', ` <span class="etiqueta ${classe}">${nom}</span>`);
  });
  // progrés de cada objectiu
  document.querySelectorAll('section.objectiu').forEach((s) => {
    const lloc = s.querySelector('.progres-objectiu');
    if (lloc) lloc.innerHTML = barra(comptar(s));
  });
  document.getElementById('obrir-tot').addEventListener('click', () =>
    document.querySelectorAll('details.sub').forEach((d) => (d.open = true)));
  document.getElementById('tancar-tot').addEventListener('click', () =>
    document.querySelectorAll('details.sub').forEach((d) => (d.open = false)));
  // en clicar l'índex (o obrir un enllaç amb #o1-3), s'obre el subobjectiu
  window.addEventListener('hashchange', obrirDesDeLaUrl);
  obrirDesDeLaUrl();
});
