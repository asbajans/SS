import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../api.js";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    try {
      await login(email, password);
      nav("/projects");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="container small">
      <h1>Giriş</h1>
      <form onSubmit={submit}>
        <label>
          E-posta
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Şifre
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Giriş yap</button>
      </form>
    </main>
  );
}
