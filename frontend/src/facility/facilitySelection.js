export function chooseFacilityId(facilities, currentId) {
  if (!Array.isArray(facilities) || facilities.length === 0) return null;

  const normalizedCurrent = currentId == null ? null : Number(currentId);
  if (normalizedCurrent != null && facilities.some((facility) => facility.id === normalizedCurrent)) {
    return normalizedCurrent;
  }

  return facilities[0].id;
}

export function facilityDisplayName(facility) {
  if (!facility) return "No facility";
  if (facility.code && facility.name) return `${facility.code} - ${facility.name}`;
  return facility.name ?? facility.code ?? `Facility #${facility.id}`;
}
