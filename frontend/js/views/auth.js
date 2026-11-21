// Login / register form (one view, two modes).
import { api } from "../api.js";
import { setAuth } from "../store.js";
import { toast } from "../components.js";
import { esc } from "../utils.js";

export function authView(root, { mode, params }) {
  const isRegister = mode === "register";
  const next = params.get("next") || "#/";

  root.innerHTML = `
    <section class="card auth-card">
      <h1 class="page-title">${isRegister ? "Create your account" : "Welcome back"}</h1>
      <p class="page-sub">${isRegister ? "Sign up to start ordering." : "Log in to place and track orders."}</p>
      <form id="auth-form" novalidate data-testid="${isRegister ? "register-form" : "login-form"}">
        ${isRegister ? `<div class="field"><label for="name">Full name</label>
          <input class="input" id="name" name="name" autocomplete="name" data-testid="name"></div>` : ""}
        <div class="field"><label for="email">Email</label>
          <input class="input" id="email" name="email" type="email" autocomplete="email" data-testid="email"></div>
        <div class="field"><label for="password">Password</label>
          <input class="input" id="password" name="password" type="password"
                 autocomplete="${isRegister ? "new-password" : "current-password"}" data-testid="password"></div>
        <div class="form-error" id="form-error" data-testid="auth-error"></div>
        <button class="btn block" type="submit" data-testid="auth-submit">${isRegister ? "Sign up" : "Log in"}</button>
      </form>
      <p class="switch-auth">${isRegister
        ? `Already have an account? <a href="#/login?next=${encodeURIComponent(next)}">Log in</a>`
        : `New here? <a href="#/register?next=${encodeURIComponent(next)}" data-testid="to-register">Create an account</a>`}</p>
      ${isRegister ? "" : `<p class="muted" style="text-align:center;font-size:13px">Demo account: demo@fooddash.dev / demo12345</p>`}
    </section>`;

  const form = root.querySelector("#auth-form");
  const errorEl = root.querySelector("#form-error");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.textContent = "";
    const data = Object.fromEntries(new FormData(form));
    if (!data.email || !data.password) { errorEl.textContent = "Email and password are required."; return; }
    if (isRegister && (!data.name || data.name.trim().length < 2)) { errorEl.textContent = "Please enter your name."; return; }
    if (isRegister && data.password.length < 8) { errorEl.textContent = "Password must be at least 8 characters."; return; }

    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const result = isRegister
        ? await api.register({ name: data.name, email: data.email, password: data.password })
        : await api.login({ email: data.email, password: data.password });
      setAuth({ token: result.access_token, user: result.user });
      toast(`Welcome, ${result.user.name.split(" ")[0]}!`, "success");
      location.hash = next;
    } catch (err) {
      errorEl.textContent = err.message;
      button.disabled = false;
    }
  });

  void esc;
}
