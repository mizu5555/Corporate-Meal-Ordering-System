import { useEffect, useState } from "react";
import { getVendor } from "../api/employee";

export function useVendor(vendorId) {
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!vendorId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getVendor(vendorId)
      .then((data) => { if (!cancelled) setVendor(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [vendorId]);

  return { vendor, loading, error };
}
