import UploadBox from "../components/UploadBox";
import ChatBox from "../components/ChatBox";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  return (
    <div className="app">

      <header className="header">

        <h1>KnowledgeFlow AI</h1>

        <button
          className="logout-btn"
          onClick={handleLogout}
        >
          Logout
        </button>

      </header>

      <div className="main-layout">

        <aside className="sidebar">
          <UploadBox />
        </aside>

        <section className="chat-section">
          <ChatBox />
        </section>

      </div>

    </div>
  );
}

export default Dashboard;