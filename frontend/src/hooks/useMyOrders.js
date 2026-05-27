import { useEffect, useState } from "react";
import { getMyOrders } from "../api/employee";

export function useMyOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMyOrders()
      .then((data) => { if (!cancelled) setOrders(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return { orders, setOrders, loading, error };
}
