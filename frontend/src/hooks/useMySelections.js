import { useEffect, useState } from "react";
import { getMySelections } from "../api/employee";

export function useMySelections() {
  const [selections, setSelections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMySelections()
      .then((data) => { if (!cancelled) setSelections(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return { selections, loading, error };
}
