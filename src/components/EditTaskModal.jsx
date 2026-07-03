import { useState } from "react";
import api from "../api/axios";
import { toast } from "react-toastify";

export default function EditTaskModal({ task, onClose, onUpdated }) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);

  const updateTask = async () => {
    try {
      const res = await api.patch(`/tasks/${task.id}/`, {
        title,
        description,
      });

      toast.success("Task updated");
      onUpdated(res.data);
      onClose();
    } catch {
      toast.error("Update failed");
    }
  };

  return (
    <div style={overlay}>
      <div style={modal}>
        <h3>Edit Task</h3>

        <input value={title} onChange={(e) => setTitle(e.target.value)} />
        <br />

        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <br />

        <button onClick={updateTask}>Save</button>
        <button onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}

const overlay = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
};

const modal = {
  background: "#fff",
  padding: 20,
  borderRadius: 8,
};