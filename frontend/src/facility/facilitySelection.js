const HOME_FACILITY_KEY = (userId) => `corpmeal:home_facility:${userId}`;

export function loadHomeFacilityId(userId) {
  if (!userId) return null;
  const raw = window.localStorage.getItem(HOME_FACILITY_KEY(userId));
  return raw != null ? Number(raw) : null;
}

export function saveHomeFacilityId(userId, facilityId) {
  if (!userId) return;
  if (facilityId == null) {
    window.localStorage.removeItem(HOME_FACILITY_KEY(userId));
  } else {
    window.localStorage.setItem(HOME_FACILITY_KEY(userId), String(facilityId));
  }
}

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
