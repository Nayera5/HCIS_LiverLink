import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, matchPath, useLocation, useNavigate } from 'react-router-dom'
import { getMyNotifications } from '../../api/notifications'
import { useAuth } from '../../auth/authContext'
import { displayName, initials, roleLine } from '../../auth/roles'
import { useApi } from '../../hooks/useApi'
import Button from '../ui/Button'
import { BellIcon, CloseIcon, LogOutIcon, MenuIcon, PlusIcon, SearchIcon } from '../ui/icons'
import { navigationFor, primaryActionFor } from './navigation'
import './AppShell.css'
import '../../pages/Notifications/Notifications.css'

/** Unread-count bell in the top bar. Refetches when the user leaves the notifications page. */
function NotificationBell() {
  const location = useLocation()
  const { data, reload } = useApi(getMyNotifications)
  const wasOnNotifications = useRef(false)

  useEffect(() => {
    const onNotifications = location.pathname === '/notifications'
    if (wasOnNotifications.current && !onNotifications) reload()
    wasOnNotifications.current = onNotifications
  }, [location.pathname, reload])

  const unread = data?.unread_count || 0
  return (
    <Link to="/notifications" className="topbar__bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
      <BellIcon size={18} />
      {unread > 0 && <span className="topbar__bell-badge">{unread > 99 ? '99+' : unread}</span>}
    </Link>
  )
}

/** Design reference: "Search patient by name, MRN or national ID" (users who may view patients). */
function PatientSearch() {
  const navigate = useNavigate()
  const [text, setText] = useState('')
  return (
    <form
      className="topbar__search"
      role="search"
      onSubmit={(event) => {
        event.preventDefault()
        const query = text.trim()
        navigate(query ? `/patients?search=${encodeURIComponent(query)}` : '/patients')
        setText('')
      }}
    >
      <SearchIcon size={17} className="topbar__search-icon" />
      <input
        type="search"
        aria-label="Search patients by name, MRN or national ID"
        placeholder="Search patient by name, MRN or national ID"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
    </form>
  )
}

function Logo() {
  return (
    <Link to="/" className="shell-logo" aria-label="LiverLink home">
      <span className="shell-logo__mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.4"
          strokeLinecap="round">
          <rect x="3.5" y="7.5" width="17" height="9" rx="4.5" transform="rotate(-35 12 12)" />
          <path d="M9.5 14.5 14.5 9.5" />
        </svg>
      </span>
      <span className="shell-logo__name">LiverLink</span>
    </Link>
  )
}

export default function AppShell() {
  const { user, can, signOut } = useAuth()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)

  const sections = navigationFor(can)
  const primary = primaryActionFor(can)
  const current = sections
    .flatMap((section) => section.items)
    .find((item) => matchPath({ path: item.to, end: Boolean(item.end) }, location.pathname))

  const handleSignOut = async () => {
    setSigningOut(true)
    await signOut('signed_out')
  }

  return (
    <div className={`shell ${menuOpen ? 'shell--menu-open' : ''}`}>
      <aside className="sidebar" aria-label="Main navigation">
        <div className="sidebar__top">
          <Logo />
          <button type="button" className="sidebar__close" onClick={() => setMenuOpen(false)} aria-label="Close menu">
            <CloseIcon size={20} />
          </button>
        </div>

        <nav className="sidebar__nav">
          {sections.map((section) => (
            <div key={section.label} className="sidebar__section">
              <p className="sidebar__label">{section.label}</p>
              <ul>
                {section.items.map(({ to, label, icon: Icon, end }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      end={end}
                      className={({ isActive }) => `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`}
                      onClick={() => setMenuOpen(false)}
                    >
                      <Icon size={18} />
                      <span>{label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="sidebar__user">
          <span className="sidebar__avatar" aria-hidden="true">
            {initials(user)}
          </span>
          <span className="sidebar__who">
            <span className="sidebar__name">{displayName(user)}</span>
            <span className="sidebar__role">{roleLine(user)}</span>
          </span>
          <button
            type="button"
            className="sidebar__logout"
            onClick={handleSignOut}
            disabled={signingOut}
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOutIcon size={18} />
          </button>
        </div>
      </aside>

      <button
        type="button"
        className="shell__scrim"
        tabIndex={-1}
        aria-hidden="true"
        onClick={() => setMenuOpen(false)}
      />

      <div className="shell__main">
        <header className="topbar">
          <button type="button" className="topbar__menu" onClick={() => setMenuOpen(true)} aria-label="Open menu">
            <MenuIcon size={22} />
          </button>
          {can('patients.view') ? (
            <PatientSearch />
          ) : (
            <p className="topbar__context">{current?.label || 'LiverLink'}</p>
          )}
          <div className="topbar__actions">
            <NotificationBell />
            {primary && (
              <Button as={Link} to={primary.to} icon={PlusIcon} size="sm" className="topbar__primary"
                aria-label={primary.label}>
                {primary.label}
              </Button>
            )}
          </div>
        </header>

        <main className="shell__content" id="main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
