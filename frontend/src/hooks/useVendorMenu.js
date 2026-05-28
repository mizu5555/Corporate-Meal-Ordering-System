import { useEffect, useState } from "react";
import { getVendorMenu } from "../api/employee";

export function useVendorMenu(vendorId, filters = {}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { available, facilityId } = filters;

  useEffect(() => {
    if (!vendorId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getVendorMenu(vendorId, { available, facilityId })
      .then((data) => { if (!cancelled) setItems(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [vendorId, available, facilityId]);

  return { items, loading, error };
}
