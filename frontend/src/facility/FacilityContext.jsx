import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getMyFacilities as getEmployeeFacilities } from "../api/employee";
import { getMyFacilities as getVendorFacilities } from "../api/vendor";
import { useAuth } from "../auth/AuthContext";
import { chooseFacilityId } from "./facilitySelection";

const FacilityContext = createContext(null);

function shouldLoadFacilities(user) {
  if (!user) return false;
  if (user.role === "employee") return true;
  if (user.role === "vendor_manager") return user.vendorId != null;
  return false;
}

function fetchFacilitiesFor(user) {
  if (user.role === "employee") return getEmployeeFacilities();
  if (user.role === "vendor_manager") return getVendorFacilities();
  return Promise.resolve([]);
}

export function FacilityProvider({ children }) {
  const { user } = useAuth();
  const [facilities, setFacilities] = useState([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    setFacilities([]);
    setSelectedFacilityId(null);
    setError(null);

    if (!shouldLoadFacilities(user)) {
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    fetchFacilitiesFor(user)
      .then((data) => {
        if (cancelled) return;
        const nextFacilities = Array.isArray(data) ? data : [];
        setFacilities(nextFacilities);
        setSelectedFacilityId((current) => chooseFacilityId(nextFacilities, current));
      })
      .catch((err) => {
        if (cancelled) return;
        setFacilities([]);
        setSelectedFacilityId(null);
        setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user?.id, user?.role, user?.vendorId]);

  const selectedFacility = useMemo(
    () => facilities.find((facility) => facility.id === selectedFacilityId) ?? null,
    [facilities, selectedFacilityId],
  );

  const value = useMemo(
    () => ({
      facilities,
      selectedFacility,
      selectedFacilityId,
      loading,
      error,
      canSelectFacility: facilities.length > 1,
      setSelectedFacilityId: (facilityId) => {
        setSelectedFacilityId(chooseFacilityId(facilities, facilityId));
      },
    }),
    [error, facilities, loading, selectedFacility, selectedFacilityId],
  );

  return <FacilityContext.Provider value={value}>{children}</FacilityContext.Provider>;
}

export function useFacility() {
  const context = useContext(FacilityContext);
  if (!context) throw new Error("useFacility must be used within FacilityProvider");
  return context;
}
