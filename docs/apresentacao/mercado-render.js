/* Renderiza os slides 14 a 17 a partir de window.MERCADO (gerado por montar.py). */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function dataBR(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? m[3] + "/" + m[2] + "/" + m[1] : (iso || "sem data");
  }
  function moeda(v) {
    if (v >= 1e6) return "R$ " + (v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + " mi";
    return "R$ " + Math.round(v / 1e3).toLocaleString("pt-BR") + " mil";
  }
  var GRATIS = { "gratuita": 1, "open source": 1, "open source gerenciado": 1 };
  var PRAT = { "prateleira": 1, "marketplace": 1 };

  window.renderMercado = function (M, U) {
    var esc = U.esc, tag = U.tagDecisao;
    var rodape = '<p class="xs" style="margin-top:14px">Preços consultados em ' + esc(dataBR(M.data_consulta)) +
      '. Valores mudam; cada opção tem a fonte em <code>dados/mercado.json</code>.</p>';

    /* 14. matriz por capacidade */
    var a = $("m-matriz");
    if (a) {
      var linhas = (M.capacidades || []).map(function (c) {
        var g = [], p = [], s = [];
        (c.opcoes || []).forEach(function (o) {
          var t = String(o.tipo || "").toLowerCase();
          if (t === "sob medida") s.push(o); else if (GRATIS[t]) g.push(o.nome); else p.push(o.nome);
        });
        var sob = s.length ? esc(String(s[0].preco).replace(/^estimativa\s*/i, "")) : "—";
        return "<tr><td><strong>" + esc(c.nome) + "</strong></td><td>" + (g.map(esc).join(" · ") || "—") +
          "</td><td>" + (p.map(esc).join(" · ") || "—") + "</td><td>" + sob + '</td><td class="c">' + tag(c.decisao) + "</td></tr>";
      }).join("");
      a.innerHTML = '<table style="font-size:23px;line-height:1.25"><thead><tr><th style="width:360px">Capacidade</th><th>Gratuita ou open source</th><th>De prateleira</th><th style="width:300px">Sob medida (estimativa)</th><th class="c" style="width:170px">Decisão</th></tr></thead><tbody>' +
        linhas + "</tbody></table>" + rodape;
      a.querySelectorAll("td").forEach(function (td) { td.style.padding = "9px 12px"; });
    }

    /* 15. TCO */
    var b = $("m-tco");
    if (b && M.tco) {
      var cen = M.tco.cenarios || [], max = 0;
      cen.forEach(function (c) { max = Math.max(max, c.total); });
      function par(un) {
        var pr = cen.filter(function (c) { return /^Prateleira/.test(c.nome) && c.nome.indexOf(un + " unid") > -1; })[0];
        var co = cen.filter(function (c) { return /^Constru/.test(c.nome) && c.nome.indexOf(un + " unid") > -1; })[0];
        function barra(c, cor, rot) {
          if (!c) return "";
          return '<div style="display:flex;align-items:center;gap:14px;margin:8px 0"><div style="width:130px;font-weight:700;font-size:22px">' + rot +
            '</div><div style="flex:1;height:40px;border:3px solid var(--ink);background:var(--paper-2)"><div style="height:100%;width:' + (100 * c.total / max) +
            '%;background:' + cor + '"></div></div><div style="width:230px;white-space:nowrap;font:400 30px var(--titulo)">' + moeda(c.total) + "</div></div>";
        }
        return '<div style="margin-bottom:22px"><div style="font:400 30px var(--titulo)">' + un + ' unidades</div>' +
          barra(pr, "var(--verde)", "Prateleira") + barra(co, "var(--urucum)", "Própria") + "</div>";
      }
      var pm = M.tco.premissas || [];
      var mq = /(\d+ a \d+ unidades)/.exec(pm.join(" "));
      var eq = mq ? '<div class="card ink-bg" style="padding:20px 28px"><div class="sm" style="color:var(--ocre);font-weight:800">Ponto de equilíbrio grosseiro</div><div style="font:400 46px/1.15 var(--titulo)">' + esc(mq[1]) + '</div><div class="xs" style="color:var(--paper-3);font-size:22px">se o custo de prateleira crescesse de forma linear</div></div>' : "";
      var escolhidas = [0, 1, 6, 7].filter(function (i) { return pm[i]; }).map(function (i) { return "<li>" + esc(pm[i]) + "</li>"; }).join("");
      b.innerHTML = '<div class="row" style="gap:40px"><div style="flex:1.1"><p class="sm" style="margin-bottom:12px">Total em 3 anos, em reais constantes</p>' +
        par(5) + par(20) + par(50) + "</div>" +
        '<div class="col" style="flex:1"><div class="card" style="padding:22px 28px"><h3 style="font-size:32px">Premissas</h3><ul style="padding-left:24px;line-height:1.32;font-size:25px">' + escolhidas +
        '</ul></div>' + eq + '</div></div>';
      b.querySelectorAll("ul li").forEach(function (li) { li.style.margin = "12px 0"; });
    }

    /* 16. IA: só os dados de "Automação e IA" vêm do JSON */
    var c = $("m-ia-opcoes");
    if (c) {
      var cap = (M.capacidades || []).filter(function (x) { return /IA/.test(x.nome); })[0];
      if (cap) c.innerHTML = cap.opcoes.map(function (o) { return "<li>" + esc(o.nome) + "</li>"; }).join("");
    }

    /* 17. roadmap */
    var d = $("m-roadmap");
    if (d) {
      var cores = ["var(--verde)", "var(--anil)", "var(--urucum)"];
      d.innerHTML = '<div class="grid g3" style="gap:26px">' + (M.roadmap || []).map(function (f, i) {
        return '<div class="card" style="padding:0;display:flex;flex-direction:column"><div style="background:' + cores[i % 3] +
          ';color:#fff;font:400 36px var(--titulo);padding:14px 24px;border-bottom:3px solid var(--ink)">' + esc(f.fase) +
          '</div><div style="padding:18px 26px"><div class="xs" style="font-weight:800;letter-spacing:.08em;text-transform:uppercase;font-size:22px">Adotar</div><ul class="lista" style="font-size:26px;line-height:1.28">' +
          (f.adotar || []).map(function (x) { return "<li style='margin:11px 0;padding-left:38px'>" + esc(x) + "</li>"; }).join("") +
          '</ul></div><div style="margin-top:auto;padding:14px 24px;background:var(--paper-3);border-top:3px solid var(--ink)"><div class="xs" style="font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--urucum)">Sinais para construir</div><ul style="font-size:24px;line-height:1.28;padding-left:22px;margin-top:4px">' +
          (f.sinais_para_construir || []).map(function (x) { return "<li style='margin:7px 0'>" + esc(x) + "</li>"; }).join("") + "</ul></div></div>";
      }).join("") + "</div>";
    }
  };
})();
