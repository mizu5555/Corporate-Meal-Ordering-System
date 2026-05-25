import { createContext, useContext, useEffect, useState } from "react";
import { createMenuItem, deleteMenuItem, getMyMenu, updateMenuItem } from "../api/vendor";

const VendorMenuContext = createContext(null);

export function VendorMenuProvider({ children }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMyMenu()
      .then((data) => { if (!cancelled) setItems(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function addItem(data) {
    const newItem = await createMenuItem(data);
    setItems((prev) => [...prev, newItem]);
    return newItem;
  }

  async function updateItem(id, data) {
    const updated = await updateMenuItem(id, data);
    setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
    return updated;
  }

  async function removeItem(id) {
    await deleteMenuItem(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
  }

  function getItem(id) {
    return items.find((item) => item.id === id) ?? null;
  }

  return (
    <VendorMenuContext.Provider value={{ items, loading, error, addItem, updateItem, removeItem, getItem }}>
      {children}
    </VendorMenuContext.Provider>
  );
}

export function useVendorMenu() {
  return useContext(VendorMenuContext);
}
