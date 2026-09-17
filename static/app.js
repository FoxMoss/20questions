import { html } from "dreamland/js-runtime";

let App = function () {
  this.status = "connecting...";
  this.log = "";
  this.done = false;
  this.spend = 0;
  this.questions = [];
  this.answer = ""

  const show = (m) => { this.log += m + "\n"; };

  const ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
  ws.onopen = () => { this.status = ""; };
  ws.onmessage = (e) => {
    this.spend += 0.000023856 + Math.random() * 0.00001
    const m = JSON.parse(e.data);
    show(JSON.stringify(m));
    if (m.type == "answer") {
      this.questions.pop()
      this.questions.push(html`<div class="response">${m.answer}</div>`)
      this.questions = this.questions;
    } else if (m.type === "success" || m.type === "fail") {
      document.getElementById("explainer").style.display ="block";
      this.questions.pop()
      this.questions.push(html`<div class="response">${m.type}</div>`)
      this.questions = this.questions;

      this.answer = `the word was ${m.noun}`

      this.done = true;
      (m.log || []).forEach((entry) => {
        show("#log " + entry.kind + " req=" + JSON.stringify(entry.request) + " resp=" + JSON.stringify(entry.response));
      });
    } else if (m.type === "error") {
      this.status = m.message;
    }
  };
  ws.onclose = () => { if (!this.done) this.status = "disconnected, maybe reload"; };

  const ask = (value) => {
    if (!value || this.done) return;

    this.questions.push(html`<div class="from-user">${value}</div>`)
    this.questions.push(html`<div class="response">...</div>`)
    this.questions = this.questions;
    
    ws.send(JSON.stringify({ type: "question", question: value }));
  };

  const give_up = () => {
    ws.send(JSON.stringify({ type: "give_up"}));
  };



  return html`
    <div>
      <p>${use(this.status)}</p>
      <p>$${use(this.spend).map((a) => a.toFixed(6))} in tokens spent</p>

      <div class="questions">
        ${use(this.questions)}
      </div>

      <div class="answer">${use(this.answer)}</div>

        <div class="input-handler">
          <input id="q" placeholder="does it ...?" maxlength="500"
            on:keydown=${(e) => { if (e.key === "Enter") { ask(e.target.value); e.target.value = ""; } }} disabled=${use(this.done)}/>
          <button on:click=${() => { ask(document.getElementById("q").value); document.getElementById("q").value = ""; }} disabled=${use(this.done)}>
            ask
          </button>
          <button on:click=${() => { give_up() }} disabled=${use(this.done)} class="give-up">
            give up
          </button>
        </div>

    </div>
  `;
};

document.getElementById("app").replaceWith(html`<${App} />`);
