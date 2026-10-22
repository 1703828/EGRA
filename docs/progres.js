// Web de seguiment: calcula el progrés a partir dels criteris escrits a l'HTML.
// Cada criteri és un <li data-estat="validat|fet|pendent|no-compleix"> dins d'un subobjectiu.
// Progrés = criteris VALIDATS / total. La part "fet" (comprovat per Claude, pendent de l'equip)
// es mostra a part, en un color més suau, i no compta com a progrés.

const NOMS = { validat: 'VALIDAT', fet: 'FET', pendent: 'PENDENT', 'no-compleix': 'NO COMPLEIX' };

function comptar(element) {
  const criteris = element.querySelectorAll('ul.criteris li[data-estat]');
  const c = { total: criteris.length, validat: 0, fet: 0 };
  criteris.forEach((li) => {
    if (li.dataset.estat === 'validat') c.validat++;
    if (li.dataset.estat === 'fet') c.fet++;
  });
  return c;
}

function barra(c) {
  const pct = (n) => (c.total ? (100 * n) / c.total : 0);
  return `<span class="progres" title="${c.validat} validats i ${c.fet} fets de ${c.total} criteris">
      <span class="barra"><span class="b-validat" style="width:${pct(c.validat)}%"></span>
      <span class="b-fet" style="width:${pct(c.fet)}%"></span></span>
      ${Math.round(pct(c.validat))} % validat · ${c.validat}/${c.total}</span>`;
}

document.addEventListener('DOMContentLoaded', () => {
  // etiqueta visible a cada criteri (el text va dins d'un <span> perquè es mantingui en una columna)
  document.querySelectorAll('ul.criteris li[data-estat]').forEach((li) => {
    const e = li.dataset.estat;
    li.innerHTML = `<span class="etiqueta ${e}">${NOMS[e]}</span><span>${li.innerHTML}</span>`;
  });
  // barra de progrés a cada subobjectiu i objectiu
  document.querySelectorAll('details.sub, details.objectiu').forEach((d) => {
    d.querySelector(':scope > summary').insertAdjacentHTML('beforeend', barra(comptar(d)));
  });
  // botons per obrir o tancar tots els desplegables
  document.getElementById('obrir-tot').addEventListener('click', () =>
    document.querySelectorAll('details').forEach((d) => (d.open = true)));
  document.getElementById('tancar-tot').addEventListener('click', () =>
    document.querySelectorAll('details').forEach((d) => (d.open = false)));
});
