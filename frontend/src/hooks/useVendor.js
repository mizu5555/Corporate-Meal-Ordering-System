import { useEffect, useState } from "react";
import { getVendor } from "../api/employee";

export function useVendor(vendorId, filters = {}) {
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { facilityId } = filters;

  useEffect(() => {
    if (!vendorId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getVendor(vendorId, { facilityId })
      .then((data) => { if (!cancelled) setVendor(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [vendorId, facilityId]);

  return { vendor, loading, error };
}
