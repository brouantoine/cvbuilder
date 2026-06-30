import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { Button } from "./Button";

export function Layout({ children }) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="layout">
      <header className="header">
        <div className="header-inner">
          <Link to="/" className="logo">CVBuilder</Link>
          <div className="header-account">
            {user ? (
              <>
                <Link to="/dashboard" className="account-link">Mes CV</Link>
                <span className="user">{user.username}</span>
                <Button variant="outline" onClick={handleLogout}>Déconnexion</Button>
              </>
            ) : (
              <>
                <Link to="/login" className="account-link">Connexion</Link>
                <Link to="/register" className="account-cta">Inscription</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
