import { useState } from "react";
import api from "../api/api";

function Login() {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");

  const login = async () => {
    try {
      const formData = new FormData();

      formData.append("username", email);
      formData.append("password", password);

      const response = await api.post(
        "/login/access-token",
        formData
      );

      localStorage.setItem(
        "token",
        response.data.access_token
      );

      alert("Login Successful ✅");

    } catch (err) {
      console.error(err);
      alert("Login Failed");
    }
  };

  return (
    <div className="card">

      <h2>Login</h2>

      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <br /><br />

      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <br /><br />

      <button onClick={login}>
        Login
      </button>

    </div>
  );
}

export default Login;