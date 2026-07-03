import { useState } from "react";
import api from "../api/axios";
import { toast } from "react-toastify";

export default function CreateTaskModal({ onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = async () => {
    try {
      const res = await api.post("/tasks/", {
        title,
        description,
        status: "TODO",
        priority: "MEDIUM",
      });

      toast.success("Task created!");
      onCreated(res.data);
      onClose();
    } catch (err) {
      toast.error("Failed to create task");
    }
  };

  return (
    <div style={overlay}>
      <div style={modal}>
        <h3>Create Task</h3>

        <input
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <br />

        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <br />

        <button onClick={handleSubmit}>Create</button>
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
  background: "white",
  padding: 20,
  borderRadius: 8,
  width: 300,
};