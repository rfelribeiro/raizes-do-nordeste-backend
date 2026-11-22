/* Navegação, escala 16:9, notas do apresentador e renderização dos dados de mercado. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var palco = document.getElementById("palco");
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var atual = -1;

  /* ---------- ornamentos gerados (raios do sol) ---------- */
  var raios = document.getElementById("sol-raios");
  if (raios) {
    var h = "";
    for (var i = 0; i < 24; i++) {
      var comp = i % 2 ? 80 : 96;
      h += '<polygon points="-7,-60 7,-60 0,-' + comp + '" transform="rotate(' + i * 15 + ')"/>';
    }
    raios.innerHTML = h;
  }

  /* ---------- utilidades ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function fmt(n) {
    return Number(n).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  }
  function el(id) { return document.getElementById(id); }

  /* ---------- escala ---------- */
  function escalar() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    palco.style.transform = "translate(" + (-960 * s) + "px," + (-540 * s) + "px) scale(" + s + ")";
  }
  window.addEventListener("resize", escalar);
  escalar();

  /* ---------- navegação ---------- */
  function ir(n, silencioso) {
    n = Math.max(0, Math.min(slides.length - 1, n));
    if (n === atual) return;
    var anterior = slides[atual];
    if (anterior) {
      anterior.classList.remove("ativo");
      anterior.classList.add("saindo");
      setTimeout(function () { anterior.classList.remove("saindo"); }, 400);
    }
    atual = n;
    slides[n].classList.add("ativo");
    el("num").textContent = (n + 1) + " / " + slides.length;
    el("progresso").style.width = (100 * (n + 1) / slides.length) + "%";
    var nota = slides[n].querySelector(".notes");
    el("notas-texto").innerHTML = nota ? nota.innerHTML : "";
    if (!silencioso) history.replaceState(null, "", "#" + (n + 1));
  }
  function doHash() {
    var m = /^#(\d+)$/.exec(location.hash);
    ir(m ? parseInt(m[1], 10) - 1 : 0, true);
  }
  window.addEventListener("hashchange", doHash);

  function dica(t) {
    var d = el("dica"); d.textContent = t; d.classList.add("on");
    clearTimeout(dica.t); dica.t = setTimeout(function () { d.classList.remove("on"); }, 1400);
  }

  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var k = e.key;
    if (k === "ArrowRight" || k === "ArrowDown" || k === " " || k === "PageDown" || k === "Enter") { e.preventDefault(); ir(atual + 1); }
    else if (k === "ArrowLeft" || k === "ArrowUp" || k === "PageUp" || k === "Backspace") { e.preventDefault(); ir(atual - 1); }
    else if (k === "Home") { e.preventDefault(); ir(0); }
    else if (k === "End") { e.preventDefault(); ir(slides.length - 1); }
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
    } else if (k === "n" || k === "N") {
      document.body.classList.toggle("notas");
      dica(document.body.classList.contains("notas") ? "Notas visíveis (N para esconder)" : "Notas escondidas");
    }
  });
  var tx = null;
  document.addEventListener("touchstart", function (e) { tx = e.touches[0].clientX; });
  document.addEventListener("touchend", function (e) {
    if (tx == null) return;
    var dx = e.changedTouches[0].clientX - tx; tx = null;
    if (Math.abs(dx) > 60) ir(atual + (dx < 0 ? 1 : -1));
  });

  /* ---------- decisões por origem (gráfico) ---------- */
  function desenharDecisoes() {
    var D = window.DECISOES, alvo = el("grafico-decisoes");
    if (!alvo) return;
    if (!D) { alvo.innerHTML = '<p class="sm urucum">Execute <code>python3 docs/apresentacao/montar.py</code> para gerar as contagens.</p>'; return; }
    var itens = [
      { r: "Humana", s: "🧑", v: D.humana, c: "var(--urucum)", d: "visão, modelagem, textos" },
      { r: "Conjunta", s: "🤝", v: D.conjunta, c: "var(--anil)", d: "a IA propôs, o autor escolheu" },
      { r: "IA", s: "🤖", v: D.ia, c: "var(--verde)", d: "boas práticas, validadas depois" }
    ];
    var max = Math.max.apply(null, itens.map(function (i) { return i.v; }));
    var html = itens.map(function (i) {
      return '<div style="margin:14px 0"><div style="display:flex;justify-content:space-between;font-weight:800;font-size:26px">' +
        '<span>' + i.s + " " + i.r + '</span><span>' + i.v + '</span></div>' +
        '<div style="height:34px;border:3px solid var(--ink);background:var(--paper-2)"><div style="height:100%;width:' + (100 * i.v / max) + '%;background:' + i.c + '"></div></div>' +
        '<div class="xs">' + i.d + '</div></div>';
    }).join("");
    alvo.innerHTML = html + '<div class="sm" style="margin-top:8px"><strong>' + D.total + '</strong> decisões registradas' + (D.mista ? ' (' + D.mista + ' mista)' : '') + '</div>';
    document.querySelectorAll("[data-total-decisoes]").forEach(function (n) { n.textContent = D.total; });
  }

  /* ---------- mercado ---------- */
  var COR = { comprar: "u", integrar: "a", construir: "v" };
  function tagDecisao(d) {
    var k = String(d || "").toLowerCase();
    return '<span class="tag ' + (COR[k] || "o") + '">' + esc(k ? k.charAt(0).toUpperCase() + k.slice(1) : "?") + "</span>";
  }
  function faixaPendente(M) {
    return M && M.pendente ? '<div class="pendente-faixa" data-pendente="mercado">PENDENTE: pesquisa de mercado</div>' : "";
  }

  function mercado() {
    var M = window.MERCADO;
    if (!M) {
      document.querySelectorAll("[data-mercado]").forEach(function (n) {
        n.innerHTML = '<p class="urucum">Execute <code>python3 docs/apresentacao/montar.py</code> para gerar os dados de mercado.</p>';
      });
      return;
    }
    document.querySelectorAll("[data-mercado-faixa]").forEach(function (n) { n.innerHTML = faixaPendente(M); });
    if (window.renderMercado) window.renderMercado(M, { esc: esc, fmt: fmt, tagDecisao: tagDecisao });
  }

  /* o renderizador específico fica em mercado-render.js */
  window.addEventListener("load", function () { mercado(); });

  desenharDecisoes();
  doHash();
  if (location.hash === "") ir(0, true);
})();

/* ---------- matriz de barramento (slide 11) ---------- */
(function () {
  var M = [
    ["1. Itens de pedido", "X X X X X X . X . . . .", "modelado"],
    ["2. Pedidos", "X X X . X X . X X X . .", "implementado"],
    ["3. Ciclo de vida", "R . X . X . . . . X . .", "modelado"],
    ["4. Pagamentos", "X X X . X X X . . . X .", "implementado"],
    ["5. Mov. de estoque", "X X X X . . . . X . X .", "modelado"],
    ["6. Saldo de estoque", "X . X X . . . . . . . .", "modelado"],
    ["7. Fidelidade", "X . X . X X . X . . X .", "modelado"],
    ["8. Operações sensíveis", "X X X X X . . X X . X .", "modelado"],
    ["9. Consentimentos LGPD", "X . . . X X . . . . . X", "modelado"]
  ];
  var corpo = document.getElementById("matriz-corpo");
  if (!corpo) return;
  corpo.innerHTML = M.map(function (l) {
    var ok = l[2] === "implementado";
    var cels = l[1].split(" ").map(function (c) {
      return '<td class="c" style="padding:9px 4px;font-size:26px;line-height:1">' + (c === "X" ? "●" : c === "R" ? "<span style='font:800 17px var(--corpo)'>RP</span>" : "") + "</td>";
    }).join("");
    return '<tr style="' + (ok ? "background:#f6dfa0" : "") + '"><td style="padding:9px 12px"><strong>' + l[0] + "</strong></td>" + cels +
      '<td class="c" style="padding:9px 8px;font-weight:800;color:' + (ok ? "var(--verde)" : "var(--muted)") + '">' + (ok ? "✓ no ar" : "modelado") + "</td></tr>";
  }).join("");
})();

/* ---------- painel (slide 12): usa as capturas se existirem ---------- */
(function () {
  var imgs = window.DASHBOARD || [];
  var alvo = document.getElementById("painel-corpo");
  if (!alvo || !imgs.length) return;
  imgs = imgs.slice(0, 4);
  var col = imgs.length === 1 ? "1fr" : "1fr 1fr";
  alvo.innerHTML = '<div style="display:grid;grid-template-columns:' + col + ';gap:24px;height:100%;align-content:center;justify-items:center">' +
    imgs.map(function (p) {
      return '<div class="moldura" style="max-height:' + (imgs.length > 2 ? "385px" : "780px") + ';overflow:hidden;display:flex"><img src="' + p +
        '" alt="Painel Streamlit sobre dados simulados" style="max-height:100%;width:auto;max-width:100%;object-fit:contain"></div>';
    }).join("") + "</div>";
})();
