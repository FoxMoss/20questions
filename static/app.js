import { html } from "dreamland/js-runtime";

let App = function () {
  this.status = "connecting...";
  this.log = "";
  this.done = false;
  this.spend = 0;
  this.questions = [];
  this.answer = "";

  this.mode = localStorage["mode"] ? localStorage["mode"] : "daily-mode";

  use(this.mode).listen((mode) => {
    localStorage["mode"] = mode
  });

  const show = (m) => {
    this.log += m + "\n";
  };

  const ws = new WebSocket(
    (location.protocol === "https:" ? "wss://" : "ws://") +
      location.host +
      "/ws",
  );
  ws.onopen = () => {
    this.status = "";
  };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type == "answer") {
      this.spend += 0.000023856 + Math.random() * 0.00001;
      this.questions.pop();
      this.questions.push(html`<div class="response">${m.answer}</div>`);
      this.questions = this.questions;
    } else if (m.type === "success" || m.type === "fail") {
      this.spend += 0.000023856 + Math.random() * 0.00001;
      this.questions.pop();
      this.questions.push(html`<div class="response">${m.type}</div>`);
      this.questions = this.questions;

      this.answer = `the word was ${m.noun}`;

      this.done = true;
      (m.log || []).forEach((entry) => {
        show(
          "req=" +
            JSON.stringify(entry.request, null, 2) +
            "\nresp=" +
            JSON.stringify(entry.response, null, 2),
        );
      });

      document.getElementById("log").innerText = this.log;
    } else if (m.type === "error") {
      this.status = m.message;
    }
  };
  ws.onclose = () => {
    if (this.status == "" && !this.done)
      this.status = "disconnected";
  };

  let first_ask = true;
  const ask = (value) => {
    if (!value || this.done) return;

    this.questions.push(html`<div class="from-user">${value}</div>`);
    this.questions.push(html`<div class="response">...</div>`);
    this.questions = this.questions;

    if (first_ask) {
      ws.send(JSON.stringify({ type: this.mode }));

      first_ask = false;
    }
    ws.send(JSON.stringify({ type: "question", question: value }));
  };

  const give_up = () => {
    if (first_ask) {
      ws.send(JSON.stringify({ type: this.mode }));
      first_ask = false;
    }
    ws.send(JSON.stringify({ type: "give_up" }));
  };

  return html`
    <div id="app-running">
      <div class="mode-select">
        <span>mode select:</span>
        <button on:click=${() => this.mode = "daily-mode"}>${use(this.mode).map(() => (this.mode == "daily-mode") ? "<daily challenge>" : "daily challenge")}</button>
        <button on:click=${() => this.mode = "endless-mode"}>${use(this.mode).map(() => (this.mode == "endless-mode") ? "<endless>" : "endless")}</button>
      </div>

      <div class="status-bar">
        <p>${use(this.status)}</p>
        <p class="spend">
          $${use(this.spend).map((a) => a.toFixed(6))} in tokens spent
        </p>
      </div>


      <div class="questions">${use(this.questions)}</div>

      <div class="answer">${use(this.answer)}</div>

      <div class="input-handler">
        <input
          id="q"
          placeholder="does it ...?"
          maxlength="500"
          on:keydown=${(e) => {
            if (e.key === "Enter") {
              ask(e.target.value);
              e.target.value = "";
            }
          }}
          disabled=${use(this.done)}
        />
        <button
          on:click=${() => {
            ask(document.getElementById("q").value);
            document.getElementById("q").value = "";
          }}
          disabled=${use(this.done)}
        >
          ask
        </button>
        <button
          on:click=${() => {
            give_up();
          }}
          disabled=${use(this.done)}
          class="give-up"
        >
          give up
        </button>
      </div>
    </div>
  `;
};

document.getElementById("app").replaceWith(html`<${App} />`);
