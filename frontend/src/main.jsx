import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { CartProvider } from "./cart/CartContext";
import { FacilityProvider } from "./facility/FacilityContext";
import "./styles/theme.css";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter
      basename={import.meta.env.BASE_URL}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AuthProvider>
        <FacilityProvider>
          <CartProvider>
            <App />
          </CartProvider>
        </FacilityProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
