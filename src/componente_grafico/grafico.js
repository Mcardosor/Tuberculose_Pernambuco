/* Componente de gráfico — o ECharts vivo entre um rerun e outro.
 *
 * Mesma ideia do mapa (`../componente_mapa/mapa.js`): a instância nasce uma
 * vez, no primeiro `streamlit:render`, e os renders seguintes só chamam
 * `setOption` com a opção nova. O ECharts interpola sozinho o que mudou —
 * barra que cresce até o valor novo, barra que troca de posição no ranking,
 * linha que se redesenha — porque os itens são casados pelo `name` de cada
 * dado (por isso o Python manda `name` em todo item).
 *
 * O Python manda a opção pronta (`option`), a altura e o nome do evento de
 * clique. O clique volta como ``{nonce, name, seriesName, dataIndex}``.
 */
(function () {
  "use strict";

  const raiz = document.getElementById("grafico");
  let instancia = null;
  let contador = 0;
  const prefixo = Date.now().toString(36);

  function enviar(tipo, dados) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: tipo }, dados), "*");
  }

  function aoClicar(params) {
    contador += 1;
    enviar("streamlit:setComponentValue", {
      value: {
        nonce: prefixo + "-" + contador,
        name: params.name,
        seriesName: params.seriesName,
        dataIndex: params.dataIndex,
        // A chave de navegação viaja dentro do dado, quando existe.
        chave: params.data && typeof params.data === "object" ? params.data.chave : undefined,
      },
      dataType: "json",
    });
  }

  function devolverFoco() {
    setTimeout(() => {
      if (document.activeElement && document.activeElement !== document.body) {
        document.activeElement.blur();
      }
      try { window.parent.focus(); } catch (e) { /* ignora */ }
    }, 0);
  }

  function render(args, tema) {
    const option = typeof args.option === "string" ? JSON.parse(args.option) : args.option;
    const altura = Number(args.altura) || 300;
    raiz.style.height = altura + "px";
    enviar("streamlit:setFrameHeight", { height: altura });

    // Cor do texto e fonte vêm do tema do Streamlit — o iframe não herda
    // `currentColor` da página, como o Altair herdava.
    const corTexto = (tema && tema.textColor) || "#31333F";
    const fonte = (tema && tema.font) || "system-ui, sans-serif";
    option.textStyle = Object.assign({ color: corTexto, fontFamily: fonte }, option.textStyle || {});
    // Tooltip em pt-BR: o Python manda o rótulo e as casas; o formatador é
    // função, e função não viaja em JSON.
    if (option.tooltip && option.tooltip.rotuloValor) {
      const rotulo = option.tooltip.rotuloValor;
      const casas = Number(option.tooltip.casas) || 0;
      option.tooltip.formatter = (p) => {
        const v = Array.isArray(p) ? p[0] : p;
        const num = v.value === null || v.value === undefined ? "—"
          : Number(v.value).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
        return "<b>" + v.name + "</b><br/>" + rotulo + ": <b>" + num + "</b>";
      };
    }
    if (option.yAxis && option.yAxis.axisLabel) {
      option.yAxis.axisLabel.color = corTexto;
    }
    if (option.xAxis && option.xAxis.axisLabel) {
      option.xAxis.axisLabel.color = corTexto;
      if (option.xAxis.nameTextStyle) option.xAxis.nameTextStyle.color = corTexto;
    }

    if (!instancia) {
      instancia = echarts.init(raiz, null, { renderer: "canvas" });
      instancia.on("click", aoClicar);
      raiz.addEventListener("pointerup", devolverFoco);
      window.addEventListener("resize", () => instancia && instancia.resize());
      window.__grafico = instancia;
    } else if (instancia.getHeight() !== altura) {
      instancia.resize({ height: altura });
    }
    // `notMerge: false` (o padrão) é o que preserva a animação: o ECharts
    // casa a opção nova com a antiga série a série e interpola. Com
    // `notMerge: true` ele descartaria tudo e desenharia do zero.
    instancia.setOption(option, { replaceMerge: ["series"] });
  }

  window.addEventListener("message", (ev) => {
    const msg = ev.data || {};
    if (msg.type !== "streamlit:render") return;
    try {
      render(msg.args || {}, msg.theme);
    } catch (e) {
      console.error("grafico: falha ao renderizar", e);
    }
  });

  enviar("streamlit:componentReady", { apiVersion: 1 });
})();
