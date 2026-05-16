export const mockUsers = [
  {
    id: "employee-demo",
    role: "employee",
    name: "Ting Lin",
    title: "Employee",
    email: "employee@corpmeal.local",
  },
  {
    id: "vendor-demo",
    role: "vendor",
    name: "Sunny Kitchen",
    title: "Vendor",
    email: "vendor@corpmeal.local",
  },
  {
    id: "admin-demo",
    role: "admin",
    name: "Committee Admin",
    title: "Admin",
    email: "admin@corpmeal.local",
  },
];

export function findMockUserByRole(role) {
  return mockUsers.find((user) => user.role === role) ?? null;
}
