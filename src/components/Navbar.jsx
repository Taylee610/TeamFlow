import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <div style={{ padding: 10, borderBottom: "1px solid #ddd" }}>
      <Link to="/dashboard">Dashboard</Link> |{" "}
      <Link to="/tasks">Tasks</Link>
    </div>
  );
}