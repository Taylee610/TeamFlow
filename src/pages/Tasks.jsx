import { useEffect, useState } from "react";
import api from "../api/axios";
import TaskCard from "../components/TaskCard";
import { toast } from "react-toastify";

import {
  DndContext,
  useDraggable,
  useDroppable,
} from "@dnd-kit/core";

export default function Tasks() {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    const res = await api.get("/tasks/");
    setTasks(res.data);
  };

  const updateTaskStatus = async (id, status) => {
    await api.patch(`/tasks/${id}/`, { status });
    loadTasks();
    toast.success("Task updated");
  };

  const onDragEnd = (event) => {
    const { active, over } = event;

    if (!over) return;

    const taskId = active.id;
    const newStatus = over.id;

    updateTaskStatus(taskId, newStatus);
  };

  const columns = {
    TODO: tasks.filter((t) => t.status === "TODO"),
    IN_PROGRESS: tasks.filter((t) => t.status === "IN_PROGRESS"),
    DONE: tasks.filter((t) => t.status === "DONE"),
  };

  return (
    <div style={{ padding: 40 }}>
      <h2>Task Board</h2>

      <DndContext onDragEnd={onDragEnd}>
        <div style={{ display: "flex", gap: 20 }}>
          <Column id="TODO" title="Todo" tasks={columns.TODO} />
          <Column id="IN_PROGRESS" title="In Progress" tasks={columns.IN_PROGRESS} />
          <Column id="DONE" title="Done" tasks={columns.DONE} />
        </div>
      </DndContext>
    </div>
  );
}

function Column({ id, title, tasks }) {
  const { setNodeRef } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      style={{
        flex: 1,
        padding: 10,
        border: "1px solid #ddd",
        minHeight: 400,
      }}
    >
      <h3>{title}</h3>

      {tasks.map((task) => (
        <DraggableTask key={task.id} task={task} />
      ))}
    </div>
  );
}

function DraggableTask({ task }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: task.id,
  });

  const style = {
    transform: transform
      ? `translate(${transform.x}px, ${transform.y}px)`
      : undefined,
    padding: 10,
    marginBottom: 10,
    border: "1px solid #ccc",
    background: "#fff",
    cursor: "grab",
  };

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <TaskCard task={task} />
    </div>
  );
}

const [search, setSearch] = useState("");

const filteredTasks = tasks.filter((t) =>
  t.title.toLowerCase().includes(search.toLowerCase())
);

