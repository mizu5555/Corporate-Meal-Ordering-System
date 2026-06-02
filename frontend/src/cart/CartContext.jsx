import { createContext, useContext, useState } from "react";

import { addCartItem, removeCartItem, updateCartItemQuantity } from "./cartItems";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);

  function addItem(item, vendorId, quantity = 1, mealDate = null) {
    setItems((prev) => addCartItem(prev, { item, vendorId, quantity, mealDate }));
  }

  function removeItem(itemId, mealDate = null) {
    setItems((prev) => removeCartItem(prev, { itemId, mealDate }));
  }

  function updateQuantity(itemId, mealDateOrQuantity = null, maybeQuantity = undefined) {
    const hasMealDateArg = maybeQuantity !== undefined;
    const mealDate = hasMealDateArg ? mealDateOrQuantity : null;
    const quantity = hasMealDateArg ? maybeQuantity : mealDateOrQuantity;
    if (quantity <= 0) {
      removeItem(itemId, mealDate);
    } else {
      setItems((prev) => updateCartItemQuantity(prev, { itemId, mealDate, quantity }));
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
