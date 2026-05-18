import { NavLink } from "react-router-dom";

export default function Sidebar({ items }) {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">Corporate Meal</p>
        <h1 className="sidebar-title">Operations Console</h1>
      </div>
      <nav className="nav-list" aria-label="Primary">
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              `nav-link${isActive ? " nav-link-active" : ""}`
            }
            to={item.to}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
