import { NavLink } from "react-router-dom";

export default function Sidebar({ items }) {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">企業訂餐</p>
        <h1 className="sidebar-title">訂餐管理平台</h1>
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
