import { createContext, useContext, useState } from "react";

import { addCartItem } from "./cartItems";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);

  function addItem(item, vendorId, quantity = 1, mealDate = null) {
    setItems((prev) => addCartItem(prev, { item, vendorId, quantity, mealDate }));
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

  function replaceCart(nextItems) {
    setItems(nextItems);
  }

  const totalCount = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <CartContext.Provider value={{ items, addItem, removeItem, updateQuantity, clearCart, replaceCart, totalCount }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
