const $ = id => document.getElementById(id);
const jobStorageKey = 'tryfit-job-skirt-v2';
let catalog, currentJob, polling, clock;
const labels = { tshirt: 'Siyah tişört', 'patterned-blouse': 'Çiçekli askılı bluz', 'wide-trousers': 'Geniş paça pantolon', skirt: 'Pileli mini etek' };
function status(text, error = false) { $('status').textContent = text; $('status').parentElement.classList.toggle('error', error); }
function profileId() { return document.querySelector('input[name="profile"]:checked')?.value; }
function setBusy(busy) {
  document.querySelectorAll('input, select, #generate').forEach(e => { e.disabled = busy; });
  $('busy').hidden = !busy;
  $('generate').querySelector('span').textContent = busy ? 'Kombinin üretiliyor…' : 'Kombini dene';
}
function resetResult() {
  if (currentJob && ['queued', 'running'].includes(currentJob.status)) return;
  $('result-image').hidden = true; $('empty').hidden = false; $('comparison').hidden = true; $('download').hidden = true;
  $('elapsed').textContent = ''; $('result-title').textContent = 'Kombinin burada.';
  status('Seçimlerin hazır. Yeni bir kombin üretebilirsin.');
}
function updateProducts() {
  for (const kind of ['top', 'bottom']) {
    const product = catalog.products.find(p => p.id === $(kind).value);
    if (!product) continue;
    $(kind + '-photo').src = product.imageUrl;
    $(kind + '-source').href = product.productUrl;
  }
  $('skirt-style').hidden = $('bottom').value !== 'skirt';
  $('source-note').textContent = $('bottom').value === 'wide-trousers' ? 'Pantolonun ürün görseli, kaynak sayfada AI üretimi olarak etiketli.' : 'Deneysel etek üretimi. Kemer görünürlüğü üstü nasıl giydiğine bağlıdır; ayrıntılar değişebilir.';
}
async function request(url, options) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  let payload; try { payload = await response.json(); } catch { payload = {}; }
  if (!response.ok) throw new Error(payload.error || 'Yerel sunucuya ulaşılamadı. Lütfen tekrar dene.');
  return payload;
}
function renderJob(job) {
  currentJob = job;
  const running = ['queued', 'running'].includes(job.status);
  setBusy(running); status(job.error || job.stage, job.status === 'failed');
  $('busy-stage').textContent = job.stage;
  if (running) { $('empty').hidden = true; $('result-image').hidden = true; $('download').hidden = true; $('comparison').hidden = true; }
  clearInterval(clock);
  const tick = () => { const end = job.completedAt ? Date.parse(job.completedAt) : Date.now(); $('elapsed').textContent = Math.max(0, Math.round((end - Date.parse(job.createdAt)) / 1000)) + ' sn'; };
  tick(); if (running) clock = setInterval(tick, 1000);
  if (job.status === 'completed') {
    $('empty').hidden = true; $('result-image').src = job.resultUrl; $('result-image').hidden = false;
    $('download').href = job.resultUrl; $('download').hidden = false;
    $('result-title').textContent = 'Kombinin hazır.';
    const profile = catalog.profiles.find(p => p.id === job.profileId);
    $('before-image').src = profile.imageUrl; $('comparison').hidden = false;
  } else if (job.status === 'failed') { $('empty').hidden = false; }
  clearTimeout(polling);
  if (running) polling = setTimeout(() => poll(job.id), 1800);
}
async function poll(id) {
  try { renderJob(await request('/api/jobs/' + encodeURIComponent(id))); }
  catch (error) { status(error.message, true); clearInterval(clock); setBusy(false); localStorage.removeItem(jobStorageKey); }
}
async function init() {
  try {
    catalog = await request('/api/catalog');
    for (const p of catalog.profiles) {
      const label = document.createElement('label'); label.className = 'profile';
      const input = document.createElement('input'); input.type = 'radio'; input.name = 'profile'; input.value = p.id; input.checked = p.id === 'medium'; input.setAttribute('aria-label', p.label);
      const image = document.createElement('img'); image.src = p.imageUrl; image.alt = p.label + ' — sentetik başlangıç profili';
      const text = document.createElement('span'); text.textContent = p.label;
      label.append(input, image, text); $('profiles').append(label);
      input.addEventListener('change', resetResult);
    }
    for (const kind of ['top', 'bottom']) {
      const category = kind === 'top' ? 'tops' : 'bottoms';
      for (const p of catalog.products.filter(p => p.category === category)) {
        const option = document.createElement('option'); option.value = p.id; option.textContent = labels[p.id] || p.label; $(kind).append(option);
      }
      $(kind).addEventListener('change', () => { updateProducts(); resetResult(); });
    }
    $('top').value = 'tshirt'; $('bottom').value = 'wide-trousers'; updateProducts(); setBusy(false); resetResult();
    const previous = new URLSearchParams(window.location.search).get('job') || localStorage.getItem(jobStorageKey);
    if (previous) {
      try {
        const job = await request('/api/jobs/' + encodeURIComponent(previous));
        localStorage.setItem(jobStorageKey, job.id);
        const profile = document.querySelector('input[name="profile"][value="' + job.profileId + '"]');
        if (profile) profile.checked = true;
        $('top').value = job.topId; $('bottom').value = job.bottomId; $('tuck-top').checked = job.tuckTop === true; updateProducts(); renderJob(job);
      } catch { localStorage.removeItem(jobStorageKey); }
    }
  } catch (error) { status(error.message, true); }
}
$('tryon-form').addEventListener('submit', async event => {
  event.preventDefault(); if (!catalog) return;
  setBusy(true); $('empty').hidden = true; $('result-image').hidden = true; $('download').hidden = true; $('comparison').hidden = true;
  $('busy-stage').textContent = 'Sıraya alınıyor'; status('Seçimin hazırlanıyor…');
  try {
    const job = await request('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ profileId: profileId(), topId: $('top').value, bottomId: $('bottom').value, tuckTop: $('bottom').value === 'skirt' && $('tuck-top').checked }) });
    localStorage.setItem(jobStorageKey, job.id); renderJob(job);
    const jobUrl = new URL(window.location.href); jobUrl.searchParams.set('job', job.id); window.history.replaceState({}, '', jobUrl);
    if (window.innerWidth < 850) $('result-stage').scrollIntoView({ behavior: 'smooth', block: 'center' });
  } catch (error) { setBusy(false); $('empty').hidden = false; status(error.message, true); }
});
$('tuck-top').addEventListener('change', resetResult);
init();
