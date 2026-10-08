const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const S = { me: null, movies: [], classes: [], movie: null, time: null, seats: new Set(), taken: new Set(), price: {}, bookings: [], editId: null, mode: "login" };
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 10);

const bad = m => new Error(m);
async function api(path, method = 'GET', body = {}) {
  const token = document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
  const response = await fetch('/api/' + path, {
    method, credentials: 'same-origin',
    headers: {'Content-Type':'application/json', 'X-CSRFToken':decodeURIComponent(token)},
    ...(method === 'GET' ? {} : {body:JSON.stringify(body)})
  });
  const data = await response.json().catch(() => ({error:'Server error. Check the Django terminal and try again.'}));
  if (!response.ok) throw bad(data.error || 'Request failed');
  return data;
}
const shrink = url => new Promise((ok, no) => {
  const img = new Image();
  img.onload = () => { const k = Math.min(1, 400 / img.width), c = document.createElement("canvas"); c.width = img.width * k; c.height = img.height * k; c.getContext("2d").drawImage(img, 0, 0, c.width, c.height); ok(c.toDataURL("image/jpeg", 0.85)); };
  img.onerror = () => no(bad("Could not read that image")); img.src = url;
});
let tt; function toast(msg, err) { const t = $("toast"); t.textContent = msg; t.className = err ? "err" : ""; t.hidden = false; clearTimeout(tt); tt = setTimeout(() => t.hidden = true, 3500); }
const guard = fn => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

function priceMap() { S.price = {}; S.classes.forEach(c => c.rows.forEach(r => { for (let n = 1; n <= c.cols; n++) S.price[r + "-" + n] = c.price; })); }
async function refresh() { const c = await api("config"); S.me = c.me; S.movies = c.movies; S.classes = c.classes; priceMap(); }
const poster = m => m.poster ? `<img class="poster" src="${esc(m.poster)}" alt="${esc(m.title)} poster">` : `<div class="poster fallback">${esc(m.title)}</div>`;

// ---------- auth ----------
function setMode(mode) {
  S.mode = mode; const reg = mode === "register";
  $("authTitle").textContent = $("authBtn").textContent = reg ? "Create account" : "Log in";
  $("nameRow").hidden = !reg; $("authAsk").textContent = reg ? "Already registered?" : "New here?";
  $("authToggle").textContent = reg ? "Log in" : "Create an account"; $("authErr").textContent = "";
  $("password").autocomplete = reg ? "new-password" : "current-password";
}
$("authToggle").onclick = e => { e.preventDefault(); setMode(S.mode === "login" ? "register" : "login"); };
$("authForm").onsubmit = async e => {
  e.preventDefault(); $("authErr").textContent = "";
  try {
    const d = { phone: $("phone").value.trim(), password: $("password").value };
    if (S.mode === "register") d.name = $("name").value;
    await api(S.mode, "POST", d); $("password").value = ""; await refresh(); render();
  } catch (err) { $("authErr").textContent = err.message; }
};
$("logout").onclick = guard(async () => { await api("logout", "POST"); S.me = null; S.movie = null; S.time = null; S.seats.clear(); S.bookings = [];
  ['p-show','p-seats','p-confirm','done'].forEach(id => $(id).hidden = true);
  ['done','mine','rows'].forEach(id => $(id).innerHTML = ''); resetMovieForm(); render(); });

function render() {
  const on = !!S.me;
  $("auth").hidden = on; $("app").hidden = !on; $("nav").hidden = !on;
  if (!on) { setMode("login"); return; }
  $("who").textContent = S.me.name; $("navAdmin").hidden = S.me.role !== "admin";
  tab("book");
}
function tab(name) {
  ["book", "mine", "admin"].forEach(t => { $("t-" + t).hidden = t !== name; });
  document.querySelectorAll("nav [data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === name));
  if (name === "book") { renderMovies(); $("date").value = $("date").value || today(); $("date").min = today(); }
  if (name === "mine") loadMine();
  if (name === "admin") { loadAdmin(); sub(S.sub || "bookings"); }
}
document.querySelectorAll("nav [data-tab]").forEach(b => b.onclick = () => tab(b.dataset.tab));

// ---------- booking ----------
function renderMovies() {
  $("movies").innerHTML = S.movies.map(m => `<button class="movie ${S.movie && S.movie.id === m.id ? "on" : ""}" data-id="${m.id}">${poster(m)}<strong>${esc(m.title)}</strong><span>${esc(m.lang)}${m.genre ? " · " + esc(m.genre) : ""}</span></button>`).join("") || '<p class="muted">No movies are showing right now.</p>';
}
$("movies").onclick = e => {
  const b = e.target.closest(".movie"); if (!b) return;
  S.movie = S.movies.find(m => m.id === +b.dataset.id); S.time = null; S.seats.clear();
  renderMovies(); renderTimes(); $("p-show").hidden = false; $("p-seats").hidden = $("p-confirm").hidden = $("done").hidden = true;
};
$("date").onchange = () => { if (S.movie) { S.time = null; S.seats.clear(); renderTimes(); $("p-seats").hidden = $("p-confirm").hidden = true; } };
function renderTimes() { $("times").innerHTML = S.movie.times.map(t => `<button class="chip ${S.time === t ? "on" : ""}" data-t="${esc(t)}">${esc(t)}</button>`).join(""); }
$("times").onclick = guard(async e => {
  const b = e.target.closest(".chip"); if (!b) return;
  S.time = b.dataset.t; S.seats.clear(); renderTimes(); await loadTaken(); $("p-seats").hidden = false; $("done").hidden = true;
});
async function loadTaken() {
  const r = await api(`taken?movieId=${S.movie.id}&date=${$("date").value}&time=${encodeURIComponent(S.time)}`);
  S.taken = new Set(r.seats); S.seats = new Set([...S.seats].filter(s => !S.taken.has(s))); renderSeats();
}
const sortSeats = set => [...set].sort((x, y) => { const [a, b] = x.split("-").map(Number), [c, d] = y.split("-").map(Number); return a - c || b - d; });
function renderSeats() {
  $("seats").innerHTML = S.classes.map(cl => `<div class="class-title">${esc(cl.name)} · ₹${cl.price}</div>` + cl.rows.map(r =>
    `<div class="seat-row"><b>${esc(r)}</b>` + Array.from({ length: cl.cols }, (_, i) => {
      const n = i + 1, id = r + "-" + n, t = S.taken.has(id);
      return `<button class="s ${t ? "taken" : S.seats.has(id) ? "sel" : "free"}" data-seat="${id}" ${t ? "disabled" : ""} aria-label="${esc(cl.name)} seat ${id}" ${n === Math.floor(cl.cols / 2) ? 'style="margin-right:18px"' : ""}>${n}</button>`;
    }).join("") + "</div>").join("")).join("");
  const list = sortSeats(S.seats); $("p-confirm").hidden = !list.length;
  $("summary").textContent = `${S.movie.title}, ${$("date").value} at ${S.time}. Seats: ${list.join(", ")}. Total: ₹${list.reduce((n, s) => n + S.price[s], 0)}`;
}
$("seats").onclick = e => { const b = e.target.closest(".s"); if (!b || b.disabled) return; const id = b.dataset.seat; S.seats.has(id) ? S.seats.delete(id) : S.seats.add(id); renderSeats(); };
$("book").onclick = guard(async () => {
  try {
    const { booking: b } = await api("book", "POST", { movieId: S.movie.id, date: $("date").value, time: S.time, seats: sortSeats(S.seats) });
    $("done").innerHTML = `<h2>Booking confirmed</h2><div class="ticket"><p><b>Ref:</b> ${esc(b.ref)}</p><p><b>Name:</b> ${esc(b.name)}</p><p><b>Movie:</b> ${esc(b.movie)}</p><p><b>Show:</b> ${esc(b.date)} at ${esc(b.time)}</p><p><b>Seats:</b> ${b.seats.map(esc).join(", ")}</p><p><b>Amount to pay at counter:</b> ₹${b.amount}</p></div><button class="primary" onclick="window.print()">Print ticket</button>`;
    $("done").hidden = false; S.seats.clear(); $("p-seats").hidden = $("p-confirm").hidden = true; $("done").scrollIntoView({ behavior: "smooth" });
  } catch (e) { if (S.movie && S.time) { S.seats.clear(); await loadTaken(); } throw e; }
});

async function loadMine() {
  try {
    const { bookings } = await api("my-bookings");
    $("mine").innerHTML = bookings.length ? `<div class="tablewrap"><table><thead><tr><th>Ref</th><th>Movie</th><th>Show</th><th>Seats</th><th>Amount</th></tr></thead><tbody>${bookings.map(b => `<tr><td>${esc(b.ref)}</td><td>${esc(b.movie)}</td><td>${esc(b.date)} ${esc(b.time)}</td><td>${b.seats.map(esc).join(", ")}</td><td>₹${b.amount}</td></tr>`).join("")}</tbody></table></div>` : '<p class="muted">You have no bookings yet.</p>';
  } catch (e) { toast(e.message, true); }
}

// ---------- admin ----------
function sub(name) {
  S.sub = name;
  ["bookings", "movies", "prices", "account"].forEach(s => $("a-" + s).hidden = s !== name);
  document.querySelectorAll("[data-sub]").forEach(b => b.classList.toggle("on", b.dataset.sub === name));
}
document.querySelectorAll("[data-sub]").forEach(b => b.onclick = () => sub(b.dataset.sub));
async function loadAdmin() {
  try { S.bookings = (await api("admin/bookings")).bookings; } catch (e) { return toast(e.message, true); }
  $("mf").innerHTML = '<option value="">All movies</option>' + [...new Set(S.bookings.map(b => b.movie).concat(S.movies.map(m => m.title)))].map(t => `<option>${esc(t)}</option>`).join("");
  renderBookings(); renderAdminMovies(); renderPrices();
}
const filtered = () => { const q = $("q").value.trim().toLowerCase(), mf = $("mf").value; return S.bookings.filter(b => (!mf || b.movie === mf) && (!q || [b.ref, b.name, b.phone, b.movie].some(v => String(v).toLowerCase().includes(q)))); };
function renderBookings() {
  const l = filtered();
  $("rows").innerHTML = l.map(b => `<tr><td>${esc(b.ref)}</td><td>${esc(b.name)}</td><td>${esc(b.phone)}</td><td>${esc(b.movie)}</td><td>${esc(b.date)} ${esc(b.time)}</td><td>${b.seats.map(esc).join(", ")}</td><td>₹${b.amount}</td><td>${new Date(b.createdAt).toLocaleString()}</td><td><button class="del" data-ref="${esc(b.ref)}">Cancel</button></td></tr>`).join("");
  $("noB").hidden = l.length > 0; $("sB").textContent = l.length;
  $("sS").textContent = l.reduce((n, b) => n + b.seats.length, 0); $("sR").textContent = "₹" + l.reduce((n, b) => n + b.amount, 0);
}
$("q").oninput = $("mf").onchange = renderBookings;
$("rows").onclick = guard(async e => {
  const b = e.target.closest(".del"); if (!b || !confirm(`Cancel booking ${b.dataset.ref}? Its seats become available again.`)) return;
  await api("admin/bookings/" + b.dataset.ref, "DELETE"); await loadAdmin(); toast("Booking cancelled");
});
$("csv").onclick = () => {
  const safeCell = v => /^[=+@\-\t\r\n]/.test(String(v)) ? "'" + v : v;
  const c = v => '"' + String(safeCell(v)).replace(/"/g, '""') + '"';
  const rows = filtered().map(b => [b.ref, b.name, b.phone, b.movie, b.date, b.time, b.seats.join(" "), b.amount, b.createdAt].map(c).join(","));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([["Ref", "Name", "Phone", "Movie", "Date", "Time", "Seats", "Amount", "Booked at"].map(c).join(",") + "\n" + rows.join("\n")], { type: "text/csv" }));
  a.download = "bookings.csv"; a.click();
};

function renderAdminMovies() {
  $("mRows").innerHTML = S.movies.map(m => `<tr><td>${m.poster ? `<img class="thumb" src="${esc(m.poster)}" alt="">` : ""}</td><td>${esc(m.title)}</td><td>${esc(m.lang)}</td><td>${m.times.map(esc).join(", ")}</td><td><button class="edit" data-id="${m.id}">Edit</button> <button class="del" data-id="${m.id}">Delete</button></td></tr>`).join("");
}
function resetMovieForm() {
  S.editId = null; ["mTitle", "mGenre", "mTimes", "mPoster"].forEach(i => $(i).value = ""); $("mLang").value = "Telugu"; $("mFile").value = "";
  $("mPrev").hidden = true; $("mErr").textContent = ""; $("mfTitle").textContent = "Add a movie"; $("mSave").textContent = "Add movie"; $("mCancel").hidden = true;
}
$("mCancel").onclick = resetMovieForm;
$("mFile").onchange = () => {
  const f = $("mFile").files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = guard(async () => { const { path } = await api("admin/upload", "POST", { data: await shrink(r.result) }); $("mPoster").value = path; $("mPrev").src = path; $("mPrev").hidden = false; });
  r.readAsDataURL(f);
};
$("mSave").onclick = async () => {
  $("mErr").textContent = "";
  try {
    const d = { title: $("mTitle").value, lang: $("mLang").value, genre: $("mGenre").value, times: $("mTimes").value, poster: $("mPoster").value };
    S.editId ? await api("admin/movies/" + S.editId, "PUT", d) : await api("admin/movies", "POST", d);
    const wasEdit = !!S.editId; resetMovieForm(); await refresh(); await loadAdmin(); toast(wasEdit ? "Movie updated" : "Movie added");
  } catch (e) { $("mErr").textContent = e.message; }
};
$("mRows").onclick = guard(async e => {
  const b = e.target.closest("button"); if (!b) return; const m = S.movies.find(x => x.id === +b.dataset.id);
  if (b.classList.contains("edit")) {
    S.editId = m.id; $("mTitle").value = m.title; $("mLang").value = m.lang; $("mGenre").value = m.genre; $("mTimes").value = m.times.join(", "); $("mPoster").value = m.poster;
    $("mPrev").hidden = !m.poster; if (m.poster) $("mPrev").src = m.poster;
    $("mfTitle").textContent = "Edit movie"; $("mSave").textContent = "Save changes"; $("mCancel").hidden = false; window.scrollTo({ top: 0, behavior: "smooth" });
  } else if (confirm(`Delete "${m.title}"? Existing bookings are kept.`)) {
    await api("admin/movies/" + m.id, "DELETE"); if (S.movie && S.movie.id === m.id) S.movie = null; resetMovieForm(); await refresh(); await loadAdmin(); toast("Movie deleted");
  }
});

function renderPrices() { $("priceBox").innerHTML = S.classes.map(c => `<label>${esc(c.name)} (₹ per seat)<input type="number" min="0" max="5000" step="1" data-class="${esc(c.name)}" value="${c.price}"></label>`).join(""); }
$("pSave").onclick = async () => {
  $("pErr").textContent = "";
  try {
    const prices = {}; document.querySelectorAll("[data-class]").forEach(i => prices[i.dataset.class] = i.value);
    await api("admin/classes", "PUT", { prices }); await refresh(); renderPrices(); toast("Prices saved");
  } catch (e) { $("pErr").textContent = e.message; }
};

(async () => { try { await refresh(); render(); } catch (e) { document.body.insertAdjacentHTML("beforeend", `<p class="error" style="padding:20px">Could not start: ${esc(e.message)}</p>`); } })();

$("aSave").onclick = async () => {
  $("aErr").textContent = "";
  try { await api("admin/password", "PUT", { current: $("aCur").value, password: $("aNew").value }); $("aCur").value = $("aNew").value = ""; toast("Admin password changed"); }
  catch (e) { $("aErr").textContent = e.message; }
};
