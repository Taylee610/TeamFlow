export default function TaskCard({ task }) {
  return (
    <div style={card}>
      <h4>{task.title}</h4>
      <p>{task.description}</p>
      <small>
        {task.priority} | {task.status}
      </small>
    </div>
  );
}

const card = {
  border: "1px solid #ddd",
  padding: 10,
  borderRadius: 6,
  marginBottom: 10,
  background: "#fff",
};