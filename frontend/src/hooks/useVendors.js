import { useEffect, useState } from "react";
import { getVendors } from "../api/employee";

export function useVendors(filters = {}) {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { facilityId } = filters;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getVendors({ facilityId })
      .then((data) => { if (!cancelled) setVendors(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [facilityId]);

  return { vendors, loading, error };
}
