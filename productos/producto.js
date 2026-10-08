const tabs = Array.from(document.querySelectorAll('.thumbnail'));
const panels = Array.from(document.querySelectorAll('.gallery-panel'));
function selectImage(index, focus = false) {
  tabs.forEach((tab, i) => {
    tab.setAttribute('aria-selected', String(i === index));
    tab.tabIndex = i === index ? 0 : -1;
    panels[i].hidden = i !== index;
  });
  document.querySelector('.image-count').textContent = `${String(index + 1).padStart(2, '0')} / ${String(tabs.length).padStart(2, '0')}`;
  if (focus) tabs[index].focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectImage(index));
  tab.addEventListener('keydown', event => {
    let next;
    if (['ArrowRight', 'ArrowDown'].includes(event.key)) next = (index + 1) % tabs.length;
    if (['ArrowLeft', 'ArrowUp'].includes(event.key)) next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectImage(next, true); }
  });
});
