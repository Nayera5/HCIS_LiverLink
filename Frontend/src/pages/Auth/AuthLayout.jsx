import BrandPanel from '../Login/BrandPanel'
import '../Login/LoginPage.css'

/** Same split layout as the Login page, for the other public auth pages. */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="login-page">
      <BrandPanel />
      <main className="login-main">
        <div className="login-main__inner">
          <header className="login-header">
            <h1 className="login-header__title">{title}</h1>
            {subtitle && <p className="login-header__subtitle">{subtitle}</p>}
          </header>
          <section className="login-card">{children}</section>
          {footer}
        </div>
      </main>
    </div>
  )
}
