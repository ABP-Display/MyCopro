import React from "react";
import { createRoot } from "react-dom/client";
import { AppExperience } from "./components/AppExperience";
import { App } from "./App";
import "./styles.css";
import "./components/app-experience.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
    <AppExperience />
  </React.StrictMode>,
);
