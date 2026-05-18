import { createContext, useContext, useState } from "react";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);

  function addItem(item, vendorId, quantity = 1) {
    setItems((prev) => {
      const existing = prev.find((i) => i.item.id === item.id);
      if (existing) {
        return prev.map((i) =>
          i.item.id === item.id ? { ...i, quantity: i.quantity + quantity } : i
        );
      }
      return [...prev, { item, vendorId, quantity }];
    });
  }

  function removeItem(itemId) {
    setItems((prev) => prev.filter((i) => i.item.id !== itemId));
  }

  function updateQuantity(itemId, quantity) {
    if (quantity <= 0) {
      removeItem(itemId);
    } else {
      setItems((prev) =>
        prev.map((i) => (i.item.id === itemId ? { ...i, quantity } : i))
      );
    }
  }

  function clearCart() {
    setItems([]);
  }

  const totalCount = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <CartContext.Provider value={{ items, addItem, removeItem, updateQuantity, clearCart, totalCount }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
