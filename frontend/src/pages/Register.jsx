import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/Button";
import { Input } from "../components/Input";

export function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password_confirm, setPasswordConfirm] = useState("");
  const { register, loading, error } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(username, email, password, password_confirm);
      navigate("/dashboard");
    } catch {
      // L'erreur est déjà exposée dans le store.
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Crée ton compte</h1>
        <p className="auth-intro">Gratuit. Ton premier CV en quelques minutes.</p>
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
          label="Email"
          type="email"
          name="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
        />
        <Input
          label="Mot de passe"
          type="password"
          name="password"
          value={password}
          onChange={setPassword}
          required
          autoComplete="new-password"
        />
        <Input
          label="Confirmer le mot de passe"
          type="password"
          name="password_confirm"
          value={password_confirm}
          onChange={setPasswordConfirm}
          required
          autoComplete="new-password"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Inscription…" : "S'inscrire"}
        </Button>
        <p className="auth-link">
          Déjà un compte ? <Link to="/login">Se connecter</Link>
        </p>
      </form>
    </div>
  );
}
