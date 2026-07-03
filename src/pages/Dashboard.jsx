import { useEffect, useState } from "react";
import api from "../api/axios";

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/").then((res) => setData(res.data));
  }, []);

  if (!data) return <p>Loading...</p>;

  return (
    <div style={{ padding: 50 }}>
      <h2>Dashboard</h2>

      <p>Total Tasks: {data.total_tasks}</p>
      <p>Todo: {data.todo}</p>
      <p>In Progress: {data.in_progress}</p>
      <p>Done: {data.done}</p>
    </div>
  );
}