export function appendFacilityParam(path, facilityId) {
  if (facilityId == null || facilityId === "") return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}facility_id=${encodeURIComponent(String(facilityId))}`;
}

export function facilityPayload(facilityId) {
  return facilityId == null || facilityId === "" ? {} : { facility_id: Number(facilityId) };
}
