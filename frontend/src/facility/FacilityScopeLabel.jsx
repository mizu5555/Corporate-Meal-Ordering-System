import { useFacility } from "./FacilityContext";
import { facilityDisplayName } from "./facilitySelection";

export default function FacilityScopeLabel({ label = "Current facility" }) {
  const { selectedFacility, loading } = useFacility();

  if (loading || !selectedFacility) return null;

  return (
    <p className="facility-scope">
      {label}: <span>{facilityDisplayName(selectedFacility)}</span>
    </p>
  );
}
