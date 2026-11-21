import './ui.css'

/**
 * @param {'primary'|'outline'|'secondary'|'danger'|'link'} variant
 *   primary: teal filled · outline: teal border · secondary: white with grey border (toolbar
 *   actions in the dashboard design) · danger: red filled · link: teal text action.
 * @param {'md'|'sm'} size
 * @param {boolean} loading  Shows a spinner, disables the button and announces busy state.
 * @param {string|Component} as  Render as 'button' (default), 'a', or a router <Link>.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  block = false,
  icon: Icon,
  as: Component = 'button',
  className = '',
  children,
  disabled,
  ...rest
}) {
  const classes = [
    'btn',
    `btn--${variant}`,
    size === 'sm' && 'btn--sm',
    block && 'btn--block',
    loading && 'btn--loading',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const isButton = Component === 'button'

  return (
    <Component
      className={classes}
      {...(isButton && { disabled: disabled || loading, type: rest.type || 'button' })}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <span className="btn__spinner" aria-hidden="true" />}
      {!loading && Icon && <Icon size={16} className="btn__icon" />}
      <span className="btn__label">{children}</span>
    </Component>
  )
}
