import { useState } from "react";
import api from "../api/api";

function UploadBox() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a PDF.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setStatus("Uploading document...");

      const response = await api.post(
        "/documents/upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setStatus(response.data.message);
    } catch (error) {
      console.error(error);
      setStatus("❌ Upload failed.");
    }
  };

  return (
  <div className="upload-card">

    <h2>📄 Upload Document</h2>

    <p className="upload-text">
      Upload a PDF and start chatting with it.
    </p>

    <label className="upload-label">
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />
    </label>

    {file && (
      <div className="file-card">

        <div className="file-icon">
          📄
        </div>

        <div className="file-info">
          <strong>{file.name}</strong>
          <p>
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>

      </div>
    )}

    <button
      className="upload-btn"
      onClick={handleUpload}
    >
      Upload PDF
    </button>

    {status && (
      <div className="upload-status">
        {status}
      </div>
    )}

  </div>
);
}

export default UploadBox;