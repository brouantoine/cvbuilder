import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/Button";
import { Input } from "../components/Input";

export function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { login, loading, error } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      // L'erreur est déjà exposée dans le store.
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Bon retour 👋</h1>
        <p className="auth-intro">Connecte-toi pour retrouver tes CV.</p>
        {error && <p className="form-error global">{error}</p>}
        <Input
          label="Nom d'utilisateur"
          name="username"
          value={username}
          onChange={setUsername}
          required
          autoComplete="username"
        />
        <Input
          label="Mot de passe"
          type="password"
          name="password"
          value={password}
          onChange={setPassword}
          required
          autoComplete="current-password"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Connexion…" : "Se connecter"}
        </Button>
        <p className="auth-link">
          Pas de compte ? <Link to="/register">S'inscrire</Link>
        </p>
      </form>
    </div>
  );
}
