import { createContext, useContext, useEffect, useState } from "react";
import { createMenuItem, deleteMenuItem, deleteMenuItemPhoto, getMyMenu, updateMenuItem, uploadMenuItemPhoto } from "../api/vendor";

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

  async function uploadPhoto(id, file) {
    const result = await uploadMenuItemPhoto(id, file);
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, photo_path: result.photo_path, _photo_v: Date.now() } : item,
      ),
    );
    return result;
  }

  async function removePhoto(id) {
    await deleteMenuItemPhoto(id);
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, photo_path: null } : item)),
    );
  }

  return (
    <VendorMenuContext.Provider value={{ items, loading, error, addItem, updateItem, removeItem, getItem, uploadPhoto, removePhoto }}>
      {children}
    </VendorMenuContext.Provider>
  );
}

export function useVendorMenu() {
  return useContext(VendorMenuContext);
}
